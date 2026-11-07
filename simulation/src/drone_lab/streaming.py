"""Incremental collection, append-only CSV, and snapshots shared by live API and tests."""

import csv
import heapq
import json
import math
from dataclasses import asdict
from pathlib import Path
from typing import TextIO

import numpy as np

from drone_lab.aggregation import decode
from drone_lab.analytics import predict_many
from drone_lab.environment import PRESETS, Environment
from drone_lab.simulation import FEATURES, LINKS, SensorTour

CSV_FIELDS = [
    "run_id",
    "sensor_id",
    "drone_id",
    "environment",
    "sequence",
    "time_s",
    "received_s",
    "elapsed_s",
    "arrival_elapsed_s",
    "scenario",
    "protocol",
    "distance_m",
    "link_range_m",
    "delivery_delay_ms",
    "status",
    *FEATURES,
    "fire_present",
    "drone_x_m",
    "drone_y_m",
    "probability",
    "decision",
    "reason",
]


class StreamSession:
    """Advance explicitly in simulation time. The service owns wall-clock pacing."""

    def __init__(
        self,
        output: Path,
        model: dict,
        seed: int = 42,
        runs: int = 1,
        steps: int = 120,
        scenario: str = "fire",
        drones: int = 1,
        environment: Environment | None = None,
    ):
        if not 1 <= runs <= 300 or not 30 <= steps <= 600:
            raise ValueError("runs must be 1..300; steps must be 30..600")
        if scenario not in ("normal", "fire", "nuisance", "mixed"):
            raise ValueError("Unsupported scenario")
        if not 1 <= drones <= 8:
            raise ValueError("Use 1..8 drones")
        self.environment = environment or Environment()
        self.drone_count = drones
        output.mkdir(parents=True, exist_ok=False)
        self.output, self.model = output, model
        self.seed, self.runs, self.steps, self.scenario = seed, runs, steps, scenario
        self.paths = self.environment.paths(steps, drones)
        self.path = self.paths[0]
        self.positions = self.environment.positions()
        self.drone_counts = [0] * drones
        self.tour_duration = steps * 2
        self.total_duration = runs * self.tour_duration
        self.now = 0.0
        self.next_sample = 0
        self.tour: SensorTour | None = None
        self.pending: list = []
        self.latest: dict[int, dict] = {}
        self.scheduled_keys: set = set()
        self.counts = {"received": 0, "lost": 0, "out_of_range": 0, "duplicates": 0}
        self.link_counts = {name: {"received": 0, "lost": 0, "out_of_range": 0} for name in LINKS}
        self.status = "running"
        self.raw = (output / "raw.jsonl").open("w", encoding="utf-8")
        self.csv_file = (output / "readings.csv").open("w", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(self.csv_file, fieldnames=CSV_FIELDS)
        self.batch_dir = output / "batches"
        self.batch_dir.mkdir()
        self.batch_run = -1
        self.batch_handle: TextIO | None = None
        self.batch_writer: csv.DictWriter | None = None
        self.writer.writeheader()
        self.csv_file.flush()
        self.write_manifest()

    def advance(self, now: float) -> dict:
        if not math.isfinite(now) or now < self.now:
            raise ValueError("Simulation clock must be finite and monotonic")
        if self.status != "running":
            return self.snapshot()
        self.now = min(now, float(self.total_duration))
        while self.next_sample < self.runs * self.steps and self.next_sample * 2 <= self.now:
            run, step = divmod(self.next_sample, self.steps)
            if self.tour is None or self.tour.run != run:
                self.tour = SensorTour(
                    run,
                    self.steps,
                    self.seed,
                    None if self.scenario == "mixed" else self.scenario,
                    self.positions,
                    PRESETS[self.environment.preset]["temperature_offset_c"],
                    PRESETS[self.environment.preset]["humidity_offset_pct"],
                )
            self.scheduled_keys.clear()
            for packet in self.tour.sample(step, np.array([path[step] for path in self.paths])):
                packet["environment"] = self.environment.preset
                self.raw.write(json.dumps(packet) + "\n")
                key = (run, packet["sensor_id"], step)
                if key in self.scheduled_keys:
                    self.counts["duplicates"] += 1
                    continue
                self.scheduled_keys.add(key)
                if packet["status"] == "received":
                    heapq.heappush(
                        self.pending, (run * self.tour_duration + packet["received_s"], key, packet)
                    )
                else:
                    self.counts[packet["status"]] += 1
                    self.link_counts[packet["protocol"]][packet["status"]] += 1
            self.next_sample += 1
        arrivals = []
        while self.pending and self.pending[0][0] <= self.now:
            arrival, key, packet = heapq.heappop(self.pending)
            values = decode(packet["protocol"], packet["payload"])
            reading = {
                name: None if np.isnan(value) else float(value)
                for name, value in zip(FEATURES, values)
            }
            row = {k: v for k, v in packet.items() if k != "payload"}
            row.update(reading)
            row["elapsed_s"] = packet["run_id"] * self.tour_duration + packet["time_s"]
            row["arrival_elapsed_s"] = arrival
            arrivals.append(row)
        for row, decision in zip(arrivals, predict_many(arrivals, self.model)):
            row.update(decision)
            row["probability"] = decision.get("probability")
            if row["run_id"] != self.batch_run:
                if self.batch_handle:
                    self.batch_handle.close()
                self.batch_run = row["run_id"]
                self.batch_handle = (self.batch_dir / f"tour-{self.batch_run:04d}.csv").open(
                    "x", newline="", encoding="utf-8"
                )
                self.batch_writer = csv.DictWriter(self.batch_handle, fieldnames=CSV_FIELDS)
                self.batch_writer.writeheader()
            assert self.batch_writer is not None
            csv_row = row.copy()
            for feature in FEATURES:
                if csv_row[feature] is None:
                    csv_row[feature] = "NaN"
            self.batch_writer.writerow(csv_row)
            self.writer.writerow(csv_row)
            self.latest[row["sensor_id"]] = row
            self.counts["received"] += 1
            self.drone_counts[row["drone_id"]] += 1
            self.link_counts[row["protocol"]]["received"] += 1
        # Readers see complete lines while this process is still running.
        self.csv_file.flush()
        self.raw.flush()
        if self.batch_handle:
            self.batch_handle.flush()
        if self.now >= self.total_duration:
            self.close("completed")
        return self.snapshot()

    def snapshot(self) -> dict:
        current_run = min(int(self.now // self.tour_duration), self.runs - 1)
        local_time = min(self.now - current_run * self.tour_duration, (self.steps - 1) * 2)
        sample = local_time / 2
        axis = np.arange(self.steps)
        next_index = min(int(sample) + 1, self.steps - 1)
        prior_index = max(0, next_index - 1)
        fleet = []
        for drone_id, path in enumerate(self.paths):
            position = [float(np.interp(sample, axis, path[:, i])) for i in (0, 1)]
            delta = path[next_index] - path[prior_index]
            fleet.append(
                {
                    "id": drone_id,
                    "position": position,
                    "heading": float(np.arctan2(delta[1], delta[0])),
                    "collected": self.drone_counts[drone_id],
                    "altitude_m": 14 + drone_id * 2,
                }
            )
        stations = []
        for sensor, point in enumerate(self.positions):
            reading = self.latest.get(sensor)
            if reading is not None and reading["run_id"] != current_run:
                reading = None
            age = self.now - reading["elapsed_s"] if reading else None
            decision = (
                reading["decision"] if reading and age is not None and age <= 30 else "WARNING"
            )
            protocol = list(LINKS)[sensor % 3]
            stations.append(
                {
                    "id": sensor,
                    "x": float(point[0]),
                    "y": float(point[1]),
                    "protocol": protocol,
                    "decision": decision,
                    "age_s": age,
                    "in_range": any(
                        np.linalg.norm(np.array(drone["position"]) - point)
                        <= LINKS[protocol].range_m
                        for drone in fleet
                    ),
                    "reading": reading,
                }
            )
        visible_events = []
        if (
            self.tour
            and self.tour.run == current_run
            and sample >= self.tour.onset
            and self.tour.scenario in ("fire", "nuisance")
        ):
            strength = min(1.0, (sample - self.tour.onset + 1) / (self.steps * 0.3))
            for sensor in sorted(self.tour.affected):
                x, y = self.positions[sensor]
                visible_events.append(
                    {"x": float(x), "y": float(y), "kind": self.tour.scenario, "strength": strength}
                )
        return {
            "visible_events": visible_events,
            "status": self.status,
            "session": self.output.name,
            "seed": self.seed,
            "scenario_mode": self.scenario,
            "scenario": ("normal", "fire", "nuisance")[current_run % 3]
            if self.scenario == "mixed"
            else self.scenario,
            "run_id": current_run,
            "runs": self.runs,
            "time_s": round(local_time, 2),
            "elapsed_s": round(self.now, 2),
            "total_s": self.total_duration,
            "position": fleet[0]["position"],
            "heading": fleet[0]["heading"],
            "drones": fleet,
            "drone_count": self.drone_count,
            "environment": self.environment.to_dict(),
            "steps": self.steps,
            "stations": stations,
            "counts": self.counts.copy(),
            "links": self.link_counts,
            "route": self.path.tolist(),
            "csv_url": "/api/download/readings.csv",
            "pending": len(self.pending),
        }

    def write_manifest(self) -> None:
        manifest = {
            "synthetic": True,
            "mode": "live",
            "generator_version": 1,
            "schema_version": 3,
            "environment": self.environment.to_dict(),
            "drone_count": self.drone_count,
            "collector_policy": "nearest drone; one attempt per sensor sample",
            "seed": self.seed,
            "runs": self.runs,
            "steps": self.steps,
            "scenario": self.scenario,
            "status": self.status,
            "counts": self.counts,
            "elapsed_s": self.now,
            "sample_interval_s": 2,
            "pending_not_delivered": len(self.pending),
            "links": {k: asdict(v) for k, v in LINKS.items()},
        }
        (self.output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    def close(self, status: str = "stopped") -> None:
        if self.status == "running":
            self.status = status
            self.csv_file.close()
            self.raw.close()
            if self.batch_handle:
                self.batch_handle.close()
            self.write_manifest()
