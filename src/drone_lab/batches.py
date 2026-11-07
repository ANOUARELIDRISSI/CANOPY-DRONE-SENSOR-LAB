"""Collect independent batches and fit a sensor classifier across completed tours."""

import argparse
import json
import secrets
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import pandas as pd

from drone_lab.aggregation import aggregate
from drone_lab.analytics import train
from drone_lab.simulation import generate


def collect(root: Path, runs: int, steps: int, seed: int | None) -> Path:
    seed = secrets.randbits(32) if seed is None else seed
    parent = root / "batches"
    parent.mkdir(parents=True, exist_ok=True)
    destination = parent / f"batch-{seed}-{uuid4().hex[:8]}"
    with TemporaryDirectory(dir=parent, prefix=".collect-") as temp:
        staging = Path(temp) / "dataset"
        manifest = generate(staging, runs, steps, seed)
        rows = aggregate(staging / "raw.jsonl", staging)
        manifest.update(status="completed", batch_id=destination.name, rows=len(rows))
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        staging.rename(destination)
    return destination


def fit_batches(root: Path, classifier: str, seed: int, include_live: bool) -> Path:
    manifests = sorted((root / "batches").glob("batch-*/manifest.json"))
    if include_live:
        manifests.extend(sorted((root / "live").glob("*/manifest.json")))
    seen: set[tuple[int, int]] = set()
    frames = []
    provenance = []
    for source in manifests:
        manifest = json.loads(source.read_text(encoding="utf-8"))
        if manifest.get("status") != "completed":
            continue
        frame = pd.read_csv(source.parent / "readings.csv")
        mapping = {}
        for local_run in sorted(frame.run_id.unique()):
            key = (int(manifest["seed"]), int(local_run))
            if key not in seen:
                mapping[local_run] = len(seen)
                seen.add(key)
        included = frame[frame.run_id.isin(mapping)].copy()
        if not included.empty:
            included["source_run_id"] = included.run_id
            included["batch_id"] = source.parent.name
            included["run_id"] = included.run_id.map(mapping)
            frames.append(included)
        provenance.append(
            {
                "manifest": str(source.relative_to(root)),
                "seed": manifest["seed"],
                "included_rows": len(included),
                "repeated_runs_skipped": int(frame.run_id.nunique() - len(mapping)),
            }
        )
    if not frames:
        raise ValueError("No completed datasets. Run the batch service first.")
    data = pd.concat(frames, ignore_index=True)
    if set(data.scenario) != {"normal", "fire", "nuisance"}:
        raise ValueError("Training needs normal, fire and nuisance tours.")
    parent = root / "models"
    parent.mkdir(parents=True, exist_ok=True)
    destination = parent / f"fit-{uuid4().hex[:12]}"
    with TemporaryDirectory(dir=parent, prefix=".fit-") as temp:
        staging = Path(temp) / "model"
        staging.mkdir()
        report = train(data, staging, seed, classifier)
        record = {
            "classifier": report["selected_model"],
            "split_seed": seed,
            "rows": len(data),
            "sources": provenance,
        }
        (staging / "sources.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        staging.rename(destination)
        candidate = Path(temp) / "current.joblib"
        shutil.copyfile(destination / "model.joblib", candidate)
        candidate.replace(parent / "current.joblib")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["collect", "train", "bootstrap"])
    parser.add_argument("--root", type=Path, default=Path("artifacts"))
    parser.add_argument("--runs", type=int, default=30)
    parser.add_argument("--steps", type=int, default=120)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--include-live", action="store_true")
    parser.add_argument(
        "--classifier", choices=["auto", "logistic_regression", "random_forest"], default="auto"
    )
    args = parser.parse_args()
    if args.action == "bootstrap" and (args.root / "models/current.joblib").is_file():
        print("Using existing sensor model")
        return
    if args.action == "collect" or (
        args.action == "bootstrap"
        and not any((args.root / "batches").glob("batch-*/manifest.json"))
    ):
        print(collect(args.root, args.runs, args.steps, args.seed), flush=True)
    if args.action != "collect":
        print(
            fit_batches(
                args.root,
                args.classifier,
                args.seed if args.seed is not None else 42,
                args.include_live,
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
