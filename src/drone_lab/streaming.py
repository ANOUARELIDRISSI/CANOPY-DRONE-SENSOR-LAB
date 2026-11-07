"""Incremental collection, append-only CSV, and snapshots shared by live API and tests."""

import csv
import heapq
import json
import math
from dataclasses import asdict
from pathlib import Path

import numpy as np

from drone_lab.aggregation import decode
from drone_lab.analytics import predict_many
from drone_lab.simulation import FEATURES, LINKS, SensorTour, layout, route

CSV_FIELDS = [
    "run_id",
    "sensor_id",
    "sequence",
    "time_s",
    "received_s",
    "elapsed_s",
    "arrival_elapsed_s",
    "scenario",
    "protocol",
    "distance_m",
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
    ):
        if not 1 <= runs <= 300 or not 30 <= steps <= 600:
            raise ValueError("runs must be 1..300; steps must be 30..600")
        if scenario not in ("normal", "fire", "nuisance", "mixed"):
            raise ValueError("Unsupported scenario")
        output.mkdir(parents=True, exist_ok=False)
        self.output, self.model = output, model
        self.seed, self.runs, self.steps, self.scenario = seed, runs, steps, scenario
        self.path = route(steps)
        self.tour_duration = steps * 2
        self.total_duration = runs * self.tour_duration
        self.now = 0.0
        self.next_sample = 0
        self.tour: SensorTour | None = None
        self.pending: list = []
        self.latest: dict[int, dict] = {}
        self.received_keys: set = set()
        self.scheduled_keys: set = set()
        self.counts = {"received": 0, "lost": 0, "out_of_range": 0, "duplicates": 0}
        self.link_counts = {name: {"received": 0, "lost": 0, "out_of_range": 0} for name in LINKS}
        self.status = "running"
        self.raw = (output / "raw.jsonl").open("w", encoding="utf-8")
        self.csv_file = (output / "readings.csv").open("w", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(self.csv_file, fieldnames=CSV_FIELDS)
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
                    run, self.steps, self.seed, None if self.scenario == "mixed" else self.scenario
                )
            for packet in self.tour.sample(step, self.path[step]):
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
            if key in self.received_keys:
                continue
            self.received_keys.add(key)
            values = decode(packet["protocol"], packet["payload"])
            reading = {
                name: None if np.isnan(value) else float(value)
                for name, value in zip(FEATURES, values)
            }
            row = {k: v for k, v in packet.items() if k != "payload"}
            row.update(reading)
            row["elapsed_s"] = packet["run_id"] * self.tour_duration + packet["time_s"]
            row["arrival_elapsed_s"] = arrival
            row["drone_x_m"], row["drone_y_m"] = self.path[packet["sequence"]].tolist()
            arrivals.append(row)
        for row, decision in zip(arrivals, predict_many(arrivals, self.model)):
            row.update(decision)
            row["probability"] = decision.get("probability")
            self.writer.writerow(row)
            self.latest[row["sensor_id"]] = row
            self.counts["received"] += 1
            self.link_counts[row["protocol"]]["received"] += 1
        # Readers see complete lines while this process is still running.
        self.csv_file.flush()
        self.raw.flush()
        if self.now >= self.total_duration:
            self.close("completed")
        return self.snapshot()

    def snapshot(self) -> dict:
        current_run = min(int(self.now // self.tour_duration), self.runs - 1)
        local_time = min(self.now - current_run * self.tour_duration, (self.steps - 1) * 2)
        sample = local_time / 2
        axis = np.arange(self.steps)
        position = [float(np.interp(sample, axis, self.path[:, i])) for i in (0, 1)]
        next_index = min(int(sample) + 1, self.steps - 1)
        prior_index = max(0, next_index - 1)
        delta = self.path[next_index] - self.path[prior_index]
        stations = []
        for sensor, point in enumerate(layout()):
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
                    "x": int(point[0]),
                    "y": int(point[1]),
                    "protocol": protocol,
                    "decision": decision,
                    "age_s": age,
                    "in_range": float(np.linalg.norm(np.array(position) - point))
                    <= LINKS[protocol].range_m,
                    "reading": reading,
                }
            )
        return {
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
            "position": position,
            "heading": float(np.arctan2(delta[1], delta[0])),
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
            self.write_manifest()
