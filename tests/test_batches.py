import json

import pandas as pd

from drone_lab.batches import collect, fit_batches


def test_repeated_seed_does_not_cross_training_splits(tmp_path):
    first = collect(tmp_path, runs=15, steps=30, seed=901)
    repeat = collect(tmp_path, runs=15, steps=30, seed=901)
    different = collect(tmp_path, runs=15, steps=30, seed=902)
    assert first != repeat
    expected = sum(len(pd.read_csv(path / "readings.csv")) for path in (first, different))
    fitted = fit_batches(tmp_path, "logistic_regression", 42, False)
    sources = json.loads((fitted / "sources.json").read_text())
    assert sources["rows"] == expected
    assert sum(s["repeated_runs_skipped"] for s in sources["sources"]) == 15
    assert sources["classifier"] == "logistic_regression"
    assert (tmp_path / "models/current.joblib").read_bytes() == (
        fitted / "model.joblib"
    ).read_bytes()
    parts = [pd.read_csv(fitted / f"{name}.csv") for name in ("train", "validation", "test")]
    assert sum(p.run_id.nunique() for p in parts) == 30
    assert len(set.union(*(set(p.run_id) for p in parts))) == 30
