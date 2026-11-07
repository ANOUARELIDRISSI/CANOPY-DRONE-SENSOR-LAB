"""Seeded sensor physics approximation and deliberately simplified wireless links."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

FEATURES = ["temperature_c", "humidity_pct", "smoke_ppm", "co_ppm"]
SCENARIOS = ("normal", "fire", "nuisance")


@dataclass(frozen=True)
class Link:
    range_m: float
    bitrate_bps: float
    delay_ms: float
    loss: float


# Teaching assumptions, not Bluetooth/WiFi specifications or calibrated radio models.
LINKS = {
    "bluetooth": Link(35, 125_000, 25, 0.08),
    "wifi": Link(100, 6_000_000, 8, 0.03),
    "proprietary": Link(160, 9_600, 90, 0.12),
}


def layout(n: int = 12) -> np.ndarray:
    return np.array([(20 + (i % 4) * 60, 20 + (i // 4) * 60) for i in range(n)])


def route(steps: int) -> np.ndarray:
    """Constant-speed closed lawnmower tour, including all twelve fixed sensor sites."""
    nodes = layout()[[0, 1, 2, 3, 7, 6, 5, 4, 8, 9, 10, 11, 0]]
    lengths = np.linalg.norm(np.diff(nodes, axis=0), axis=1)
    cumulative = np.r_[0, np.cumsum(lengths)]
    distance = np.linspace(0, cumulative[-1], steps)
    return np.column_stack([np.interp(distance, cumulative, nodes[:, axis]) for axis in (0, 1)])


def encode(protocol: str, values: list) -> dict:
    """Three heterogeneous application payloads; no real radio frames are emitted."""
    t, h, s, c = values
    if protocol == "bluetooth":
        return dict(
            zip(
                ("t_centi_c", "rh_centi_pct", "smoke_ppm", "co_ppm"),
                [
                    None if t is None else round(t * 100),
                    None if h is None else round(h * 100),
                    s,
                    c,
                ],
            )
        )
    if protocol == "wifi":
        return {
            "temperature_f": None if t is None else t * 1.8 + 32,
            "humidity_pct": h,
            "smoke_ppm": s,
            "co_ppm": c,
        }
    if protocol == "proprietary":
        return {
            "v": 1,
            "channels": [None if t is None else t + 273.15, None if h is None else h / 100, s, c],
        }
    raise ValueError(f"Unknown protocol: {protocol}")


class SensorTour:
    """Incremental scenario model shared by batch generation and the live 3D service."""

    def __init__(self, run: int, steps: int, seed: int, scenario: str | None = None):
        self.run = run
        self.steps = steps
        self.scenario = scenario or SCENARIOS[run % 3]
        if self.scenario not in SCENARIOS:
            raise ValueError("Unknown scenario")
        self.rng = np.random.default_rng(np.random.SeedSequence([seed, run]))
        self.onset = int(self.rng.integers(steps // 5, steps // 2))
        self.affected = set(self.rng.choice(12, size=6, replace=False).tolist())
        self.ambient = self.rng.normal(25, 5)
        self.humidity = self.rng.uniform(40, 75)
        self.bias = self.rng.normal(0, 1.5, size=12)

    def sample(self, step: int, drone: np.ndarray) -> list[dict]:
        rng, run, steps = self.rng, self.run, self.steps
        scenario, onset, affected = self.scenario, self.onset, self.affected
        ambient, humidity, bias = self.ambient, self.humidity, self.bias
        positions = layout()
        records: list[dict] = []
        for sensor, position in enumerate(positions):
            protocol = list(LINKS)[sensor % 3]
            link = LINKS[protocol]
            distance = float(np.linalg.norm(drone - position))
            active = sensor in affected and step >= onset
            label = int(scenario == "fire" and active)
            severity = min(1.0, max(0, (step - onset) / (steps * 0.3)))
            values = [
                ambient + bias[sensor] + rng.normal(0, 2),
                humidity + rng.normal(0, 4),
                max(0, rng.normal(4, 2)),
                max(0, rng.normal(0.7, 0.4)),
            ]
            if label:
                values[0] += 8 + severity * rng.uniform(20, 45)
                values[1] -= 5 + severity * 25
                values[2] += 8 + severity * rng.uniform(25, 90)
                values[3] += 2 + severity * rng.uniform(8, 25)
            elif scenario == "nuisance" and active:
                # Dust/steam: high apparent smoke without combustion-level CO.
                values[2] += rng.uniform(15, 80)
                values[0] += rng.uniform(0, 7)
            values[1] = float(np.clip(values[1], 0, 100))
            packet_values: list[float | None] = [round(float(v), 3) for v in values]
            if rng.random() < 0.02:
                packet_values[int(rng.integers(4))] = None
            payload = encode(protocol, packet_values)
            duration = (
                link.delay_ms / 1000 + len(json.dumps(payload).encode()) * 8 / link.bitrate_bps
            )
            status = (
                "out_of_range"
                if distance > link.range_m
                else "lost"
                if rng.random() < link.loss
                else "received"
            )
            record = {
                "run_id": run,
                "sensor_id": sensor,
                "sequence": step,
                "time_s": step * 2,
                "protocol": protocol,
                "scenario": scenario,
                "fire_present": label,
                "distance_m": round(distance, 4),
                "status": status,
                "received_s": step * 2 + duration,
                "payload": payload if status == "received" else None,
            }
            records.append(record)
            if status == "received" and rng.random() < 0.01:
                records.append(record.copy())
        return records


def generate(output: Path, runs: int = 90, steps: int = 120, seed: int = 42) -> dict:
    if runs < 15 or runs % 3 or steps < 30:
        raise ValueError("Use a multiple of 3 runs >= 15 and steps >= 30")
    output.mkdir(parents=True, exist_ok=True)
    path = route(steps)
    counters: dict[str, int] = {}
    with (output / "raw.jsonl").open("w", encoding="utf-8") as raw:
        for run in range(runs):
            tour = SensorTour(run, steps, seed)
            records = [
                record for step, drone in enumerate(path) for record in tour.sample(step, drone)
            ]
            seen = set()
            for record in records:
                key = (record["sensor_id"], record["sequence"])
                status = "duplicates" if key in seen else record["status"]
                seen.add(key)
                counters[status] = counters.get(status, 0) + 1
            tour.rng.shuffle(records)
            for record in records:
                raw.write(json.dumps(record) + "\n")
    manifest = {
        "generator_version": 1,
        "seed": seed,
        "runs": runs,
        "steps": steps,
        "sensors": 12,
        "sample_interval_s": 2,
        "synthetic": True,
        "counts": counters,
        "links": {k: asdict(v) for k, v in LINKS.items()},
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
