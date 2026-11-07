"""Train on entire runs, choose thresholds on validation, evaluate untouched test runs."""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from drone_lab.simulation import FEATURES


def split_runs(frame: pd.DataFrame, seed: int) -> dict[str, list[int]]:
    rng = np.random.default_rng(seed)
    splits: dict[str, list[int]] = {"train": [], "validation": [], "test": []}
    for _, group in frame[["run_id", "scenario"]].drop_duplicates().groupby("scenario"):
        ids = rng.permutation(group.run_id).tolist()
        n = len(ids)
        if n < 5:
            raise ValueError("At least five independent runs per scenario are required")
        a, b = int(n * 0.6), int(n * 0.8)
        for name, chunk in zip(splits, [ids[:a], ids[a:b], ids[b:]]):
            splits[name].extend(chunk)
    return splits


def metrics(y, predicted) -> dict:
    return {
        "accuracy": float(accuracy_score(y, predicted)),
        "precision": float(precision_score(y, predicted, zero_division=0)),
        "recall": float(recall_score(y, predicted, zero_division=0)),
        "f1": float(f1_score(y, predicted, zero_division=0)),
        "confusion_matrix": confusion_matrix(y, predicted, labels=[0, 1]).tolist(),
    }


def train(frame: pd.DataFrame, output: Path, seed: int = 42, classifier: str = "auto") -> dict:
    splits = split_runs(frame, seed)
    parts = {name: frame[frame.run_id.isin(ids)] for name, ids in splits.items()}
    for name, part in parts.items():
        if part.fire_present.nunique() != 2:
            raise ValueError(f"{name} requires both classes; generate more independent runs")
        part.to_csv(output / f"{name}.csv", index=False)
    train_data, val, test = (parts[k] for k in ("train", "validation", "test"))
    models = {
        "logistic_regression": make_pipeline(
            SimpleImputer(add_indicator=True),
            StandardScaler(),
            LogisticRegression(max_iter=1000, class_weight="balanced"),
        ),
        "random_forest": make_pipeline(
            SimpleImputer(add_indicator=True),
            RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_leaf=5,
                class_weight="balanced",
                random_state=seed,
                n_jobs=2,
            ),
        ),
    }
    if classifier != "auto":
        if classifier not in models:
            raise ValueError("Unknown classifier")
        models = {classifier: models[classifier]}
    report: dict = {
        "synthetic_only": True,
        "features": FEATURES,
        "split_runs": splits,
        "split_rows": {k: len(v) for k, v in parts.items()},
        "models": {},
    }
    costs = {}
    thresholds = {}
    for name, model in models.items():
        model.fit(train_data[FEATURES], train_data.fire_present)
        probabilities = model.predict_proba(val[FEATURES])[:, 1]
        candidates = []
        for threshold in np.arange(0.1, 0.91, 0.05):
            predicted = probabilities >= threshold
            tn, fp, fn, tp = confusion_matrix(val.fire_present, predicted, labels=[0, 1]).ravel()
            candidates.append((int(5 * fn + fp), float(threshold)))
        cost, threshold = min(candidates)
        costs[name], thresholds[name] = cost, threshold
        report["models"][name] = {
            "threshold": threshold,
            "validation_cost_5fn_plus_fp": cost,
            "validation": metrics(val.fire_present, probabilities >= threshold),
        }
    # Selection uses validation only; test results cannot change the winner.
    winner = min(costs, key=lambda name: costs[name])
    for name, model in models.items():
        report["models"][name]["test"] = metrics(
            test.fire_present, model.predict_proba(test[FEATURES])[:, 1] >= thresholds[name]
        )
    bundle = {"model": models[winner], "threshold": thresholds[winner], "features": FEATURES}
    joblib.dump(bundle, output / "model.joblib")
    report["selected_model"] = winner
    report["test_by_scenario"] = {
        scenario: metrics(
            group.fire_present,
            models[winner].predict_proba(group[FEATURES])[:, 1] >= thresholds[winner],
        )
        for scenario, group in test.groupby("scenario")
    }
    # A small learning curve measures validation performance, never the final test set.
    curve = []
    for fraction in (0.25, 0.5, 1.0):
        ids = []
        for _, group in train_data[["run_id", "scenario"]].drop_duplicates().groupby("scenario"):
            ids.extend(group.run_id.tolist()[: max(1, int(len(group) * fraction))])
        subset = train_data[train_data.run_id.isin(ids)]
        from sklearn.base import clone

        model = clone(models[winner]).fit(subset[FEATURES], subset.fire_present)
        curve.append(
            {
                "runs": len(ids),
                "rows": len(subset),
                **metrics(
                    val.fire_present, model.predict_proba(val[FEATURES])[:, 1] >= thresholds[winner]
                ),
            }
        )
    report["learning_curve_validation"] = curve
    (output / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    decisions = frame.copy()
    decisions["probability"] = models[winner].predict_proba(frame[FEATURES])[:, 1]
    decisions["decision"] = np.where(
        decisions.probability >= thresholds[winner], "ALARM", "NO_ALARM"
    )
    # Missing inputs make the decision uncertain even though the estimator can impute them.
    decisions.loc[decisions[FEATURES].isna().any(axis=1), "decision"] = "WARNING"
    decisions.to_csv(output / "decisions.csv", index=False)
    return report


def predict(reading: dict, bundle: dict) -> dict:
    return predict_many([reading], bundle)[0]


def predict_many(readings: list[dict], bundle: dict) -> list[dict]:
    """Batch available arrivals so fast streaming does not infer one forest per packet."""
    if not readings:
        return []
    values = pd.DataFrame(readings).reindex(columns=FEATURES)
    if np.isinf(values.to_numpy(dtype=float)).any():
        raise ValueError("Measurements must be finite")
    complete = ~values.isna().any(axis=1)
    results: list[dict] = [
        {"decision": "WARNING", "reason": "Missing measurement; recollect before deciding"}
        for _ in readings
    ]
    if complete.any():
        scores = bundle["model"].predict_proba(values[complete])[:, 1]
        for index, score in zip(values.index[complete], scores):
            probability = float(score)
            results[index] = {
                "decision": "ALARM" if probability >= bundle["threshold"] else "NO_ALARM",
                "probability": probability,
                "reason": (
                    f"Synthetic-model score {probability:.3f}; cutoff {bundle['threshold']:.2f}"
                ),
            }
    return results
