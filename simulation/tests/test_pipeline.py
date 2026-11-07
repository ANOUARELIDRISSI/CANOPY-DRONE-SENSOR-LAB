import json

import joblib
import numpy as np
import pandas as pd
import pytest

from drone_lab.aggregation import aggregate, decode
from drone_lab.analytics import predict, split_runs, train
from drone_lab.simulation import FEATURES, LINKS, encode, generate, layout, route


@pytest.mark.parametrize("protocol", LINKS)
def test_payload_units_roundtrip(protocol):
    values = [28.12, 55.23, 20.0, 2.0]
    assert decode(protocol, encode(protocol, values)) == pytest.approx(values)
    missing = decode(protocol, encode(protocol, [None, 50, 2, 1]))
    assert np.isnan(missing[0])


def test_unknown_payload_rejected():
    with pytest.raises(ValueError):
        decode("unknown", {})
    with pytest.raises(ValueError):
        decode("proprietary", {"v": 99})


def test_route_visits_every_station():
    distances = np.linalg.norm(route(120)[:, None, :] - layout()[None, :, :], axis=2)
    assert (distances.min(axis=0) < LINKS["bluetooth"].range_m).all()
    assert np.allclose(route(120)[0], route(120)[-1])


@pytest.fixture(scope="module")
def experiment(tmp_path_factory):
    folder = tmp_path_factory.mktemp("experiment")
    manifest = generate(folder, runs=15, steps=60, seed=7)
    frame = aggregate(folder / "raw.jsonl", folder)
    return folder, manifest, frame


def test_transmission_and_aggregation(experiment):
    folder, manifest, frame = experiment
    raw = pd.read_json(folder / "raw.jsonl", lines=True)
    unique = raw.drop_duplicates(["run_id", "sensor_id", "sequence"])
    assert len(unique) == 15 * 60 * 12
    for protocol, link in LINKS.items():
        packets = unique[unique.protocol == protocol]
        assert (packets[packets.status == "received"].distance_m <= link.range_m + 0.0001).all()
        in_range = packets[packets.status != "out_of_range"]
        assert abs((in_range.status == "lost").mean() - link.loss) < 0.04
    assert set(frame.protocol) == set(LINKS)
    assert not frame.duplicated(["run_id", "sensor_id", "sequence"]).any()
    assert len(frame) == manifest["counts"]["received"]
    assert frame[FEATURES].isna().any().any()
    assert (frame.received_s > frame.time_s).all()
    assert (
        frame.groupby(["run_id", "sensor_id"])
        .time_s.apply(lambda s: s.is_monotonic_increasing)
        .all()
    )


def test_reproducibility(experiment, tmp_path):
    folder, _, _ = experiment
    generate(tmp_path, runs=15, steps=60, seed=7)
    assert (folder / "raw.jsonl").read_bytes() == (tmp_path / "raw.jsonl").read_bytes()


def test_group_splits_and_model(experiment):
    folder, _, frame = experiment
    splits = split_runs(frame, 7)
    assert not set(splits["train"]) & set(splits["test"])
    assert not set(splits["train"]) & set(splits["validation"])
    assert not set(splits["test"]) & set(splits["validation"])
    assert sum(map(len, splits.values())) == frame.run_id.nunique()
    report = train(frame, folder, seed=7)
    assert len(report["models"]) == 2
    bundle = joblib.load(folder / "model.joblib")
    assert bundle["features"] == FEATURES
    assert predict(dict(zip(FEATURES, [25, 60, 3, 0.5])), bundle)["decision"] == "NO_ALARM"
    assert predict(dict(zip(FEATURES, [70, 20, 90, 25])), bundle)["decision"] == "ALARM"
    assert predict({"temperature_c": 25}, bundle)["decision"] == "WARNING"
    assert json.loads((folder / "metrics.json").read_text())["synthetic_only"]


def test_invalid_configuration(tmp_path):
    with pytest.raises(ValueError):
        generate(tmp_path, runs=2)
