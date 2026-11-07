import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from drone_lab.aggregation import aggregate
from drone_lab.server import Runtime, create_app
from drone_lab.simulation import FEATURES, generate
from drone_lab.streaming import CSV_FIELDS, StreamSession


class TestEstimator:
    """Deterministic test double; model training is covered by test_pipeline."""

    def predict_proba(self, frame):
        risk = np.where(frame.co_ppm > 3, 0.9, 0.1)
        return np.column_stack([1 - risk, risk])


@pytest.fixture
def bundle():
    return {"model": TestEstimator(), "threshold": 0.5, "features": FEATURES}


def test_csv_grows_only_on_arrival_and_closes(tmp_path, bundle):
    session = StreamSession(tmp_path / "live", bundle, steps=30)
    state = session.advance(0)
    assert state["counts"]["received"] == 0
    assert pd.read_csv(session.output / "readings.csv").empty
    session.advance(0.5)
    first = pd.read_csv(session.output / "readings.csv")
    assert len(first) > 0
    assert first.arrival_elapsed_s.max() <= 0.5
    session.advance(30)
    second = pd.read_csv(session.output / "readings.csv")
    assert len(second) > len(first)
    assert second.arrival_elapsed_s.max() <= 30
    assert not second.duplicated(["run_id", "sensor_id", "sequence"]).any()
    assert list(second.columns) == CSV_FIELDS
    assert session.status == "running"
    session.close()
    assert session.csv_file.closed
    assert json.loads((session.output / "manifest.json").read_text())["status"] == "stopped"


def test_live_matches_batch_and_has_training_labels(tmp_path, bundle):
    live = StreamSession(tmp_path / "live", bundle, runs=15, steps=30, scenario="mixed", seed=7)
    live.advance(live.total_duration)
    generated = generate(tmp_path / "batch", runs=15, steps=30, seed=7)
    batch = aggregate(tmp_path / "batch" / "raw.jsonl", tmp_path / "batch")
    streamed = pd.read_csv(live.output / "readings.csv")
    keys = ["run_id", "sensor_id", "sequence"]
    columns = keys + FEATURES + ["fire_present", "protocol", "scenario"]
    pd.testing.assert_frame_equal(
        batch[columns].sort_values(keys).reset_index(drop=True),
        streamed[columns].sort_values(keys).reset_index(drop=True),
    )
    assert live.status == "completed"
    assert live.counts == generated["counts"]
    assert len(live.pending) == 0
    assert streamed.groupby("scenario").run_id.nunique().to_dict() == {
        "fire": 5,
        "normal": 5,
        "nuisance": 5,
    }


def test_backward_clock_and_invalid_input(tmp_path, bundle):
    session = StreamSession(tmp_path / "live", bundle, steps=30)
    session.advance(3)
    with pytest.raises(ValueError):
        session.advance(2)
    with pytest.raises(ValueError):
        session.advance(float("nan"))
    session.close()
    with pytest.raises(ValueError):
        StreamSession(tmp_path / "bad", bundle, scenario="typo")


def test_api_controls_download_and_assets(tmp_path, bundle):
    runtime = Runtime(bundle, tmp_path / "sessions")
    with TestClient(create_app(runtime)) as client:
        assert client.get("/api/state").json()["status"] == "idle"
        assert client.get("/api/download/readings.csv").status_code == 404
        for asset in (
            "/",
            "/app.js",
            "/assets/cf2.dae",
            "/vendor/three.module.js",
            "/vendor/loaders/ColladaLoader.js",
            "/vendor/loaders/TGALoader.js",
        ):
            assert client.get(asset).status_code == 200
        assert client.post("/api/start", json={"runs": 0}).status_code == 422
        assert client.post("/api/start", json={"scenario": "typo"}).status_code == 409
        assert client.post("/api/start", json={"steps": 30}).status_code == 200
        assert client.post("/api/start", json={"steps": 30}).status_code == 409
        assert client.get("/api/download/readings.csv").text.startswith("run_id,")
        assert client.get("/api/download/secret").status_code == 404
        assert client.post("/api/stop").json()["status"] == "stopped"
    assert runtime.worker is not None and not runtime.worker.is_alive()


def test_snapshot_does_not_carry_previous_tour_as_fresh(tmp_path, bundle):
    session = StreamSession(tmp_path / "live", bundle, runs=3, steps=30, scenario="mixed")
    session.advance(59)
    state = session.advance(60)
    assert state["run_id"] == 1
    assert all(station["reading"] is None for station in state["stations"])
    session.close()
