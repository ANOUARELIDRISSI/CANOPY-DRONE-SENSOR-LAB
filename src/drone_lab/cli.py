import argparse
import json
from pathlib import Path

from drone_lab.aggregation import aggregate
from drone_lab.analytics import train
from drone_lab.simulation import generate
from drone_lab.visuals import render


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate, normalize, train and plot synthetic tours"
    )
    parser.add_argument("--output", type=Path, default=Path("artifacts/demo"))
    parser.add_argument("--runs", type=int, default=90)
    parser.add_argument("--steps", type=int, default=120)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error(
            "Output directory is not empty. Choose a new --output to preserve prior results."
        )
    manifest = generate(args.output, args.runs, args.steps, args.seed)
    frame = aggregate(args.output / "raw.jsonl", args.output)
    report = train(frame, args.output, args.seed)
    render(args.output, manifest, report)
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "counts": manifest["counts"],
                "split_rows": report["split_rows"],
                "selected_model": report["selected_model"],
                "test": report["models"][report["selected_model"]]["test"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
