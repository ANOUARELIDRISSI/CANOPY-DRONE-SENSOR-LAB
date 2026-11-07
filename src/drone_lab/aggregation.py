"""Normalize received application payloads without inventing lost readings."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from drone_lab.simulation import FEATURES


def decode(protocol: str, payload: dict) -> list:
    def scale(value, factor=1, offset=0):
        return np.nan if value is None else (float(value) - offset) / factor

    if protocol == "bluetooth":
        return [
            scale(payload["t_centi_c"], 100),
            scale(payload["rh_centi_pct"], 100),
            scale(payload["smoke_ppm"]),
            scale(payload["co_ppm"]),
        ]
    if protocol == "wifi":
        return [
            scale(payload["temperature_f"], 1.8, 32),
            scale(payload["humidity_pct"]),
            scale(payload["smoke_ppm"]),
            scale(payload["co_ppm"]),
        ]
    if protocol == "proprietary" and payload.get("v") == 1:
        t, h, s, c = payload["channels"]
        return [scale(t, offset=273.15), scale(h, 0.01), scale(s), scale(c)]
    raise ValueError(f"Unsupported payload: {protocol}")


def aggregate(raw_path: Path, output: Path) -> pd.DataFrame:
    rows = []
    with raw_path.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            if record["status"] != "received":
                continue
            values = decode(record["protocol"], record.pop("payload"))
            for value, (low, high) in zip(values, [(-50, 150), (0, 100), (0, 1000), (0, 500)]):
                if not np.isnan(value) and (not np.isfinite(value) or not low <= value <= high):
                    raise ValueError("Measurement outside teaching schema bounds")
            rows.append(record | dict(zip(FEATURES, values)))
    if not rows:
        raise ValueError("No received packets to aggregate")
    frame = (
        pd.DataFrame(rows)
        .sort_values("received_s")
        .drop_duplicates(["run_id", "sensor_id", "sequence"])
        .sort_values(["run_id", "time_s", "sensor_id"])
        .reset_index(drop=True)
    )
    output.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output / "readings.csv", index=False)
    summary = frame.groupby(["run_id", "sensor_id", "protocol"])[FEATURES].agg(
        ["count", "mean", "min", "max"]
    )
    summary.columns = ["_".join(col) for col in summary.columns]
    summary.to_csv(output / "tour_summary.csv")
    return frame
