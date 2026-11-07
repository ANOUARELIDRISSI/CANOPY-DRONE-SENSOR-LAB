import argparse
import json
from pathlib import Path

import pandas as pd

from drone_lab.analytics import train
from drone_lab.simulation import FEATURES


def main() -> None:
    parser = argparse.ArgumentParser(description="Train from a completed live collection CSV")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    frame = pd.read_csv(args.input)
    required = set(FEATURES + ["run_id", "scenario", "fire_present"])
    if not required.issubset(frame.columns):
        parser.error(f"CSV is missing columns: {sorted(required - set(frame.columns))}")
    if frame.groupby("scenario").run_id.nunique().min() < 5 or frame.scenario.nunique() != 3:
        parser.error("Collect at least 15 mixed tours (five per scenario) for training")
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("Choose a new empty output directory")
    args.output.mkdir(parents=True, exist_ok=True)
    report = train(frame, args.output, args.seed)
    print(
        json.dumps(
            {
                "rows": len(frame),
                "model": report["selected_model"],
                "test": report["models"][report["selected_model"]]["test"],
            },
            indent=2,
        )
    )
