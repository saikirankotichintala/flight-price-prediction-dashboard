import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import modeling


def payload(dashboard):
    row = dashboard.df.iloc[0][modeling.FEATURE_COLUMNS].to_dict()
    row["source"] = row.pop("source_city")
    row["destination"] = row.pop("destination_city")
    return row


def test_all_models_and_calibrated_bounds(dashboard):
    client = dashboard.app.test_client()
    for model_id in dashboard.models:
        response = client.post("/predict", json={**payload(dashboard), "model": model_id})
        assert response.status_code == 200
        result = response.get_json()
        assert result["model"] == model_id
        assert 0 <= result["range_low"] <= result["price"] <= result["range_high"] <= dashboard.PRICE_CEILING + .005
        assert result["nominal_coverage_pct"] == 90
        assert 0 <= result["test_coverage_pct"] <= 100
    assert client.post("/predict", json=payload(dashboard)).json["model"] == modeling.DEFAULT_MODEL
    assert sum(dashboard.bundle["split_counts"].values()) == len(dashboard.df)
    assert all(item["status"] == "ok" for item in dashboard.bundle["evaluations"])


@pytest.mark.parametrize("overrides", [
    {"model": "missing"}, {"airline": "unknown"}, {"duration": "nan"}, {"duration": "inf"},
    {"duration": -1}, {"duration": 500}, {"days_left": 1.5}, {"days_left": "inf"}, {"days_left": 1000},
])
def test_bad_prediction_inputs(dashboard, overrides):
    response = dashboard.app.test_client().post("/predict", json={**payload(dashboard), **overrides})
    assert response.status_code == 400
    assert "error" in response.json


def test_bad_json_and_same_city(dashboard):
    client = dashboard.app.test_client()
    for value in ([], [1], "hello", None):
        assert client.post("/predict", json=value).status_code == 400
    data = payload(dashboard)
    data["destination"] = data["source"]
    assert client.post("/predict", json=data).status_code == 400


def test_calibration_order_statistic():
    assert modeling.calibration_radius(np.arange(1, 100)) == 90
    with pytest.raises(ValueError):
        modeling.calibration_radius([1, 2])


def test_cache_reuse_invalidation_and_corruption(tmp_path, monkeypatch):
    data_path = tmp_path / "data.csv"
    data_path.write_text("dataset-one")
    calls = []
    def train(_df):
        calls.append(True)
        return {"generation": len(calls)}
    monkeypatch.setattr(modeling, "train_bundle", train)
    cache = tmp_path / "cache"
    assert modeling.load_or_train(None, data_path, cache) == ({"generation": 1}, False)
    assert modeling.load_or_train(None, data_path, cache) == ({"generation": 1}, True)
    next(cache.glob("*.joblib")).write_bytes(b"corrupted")
    assert modeling.load_or_train(None, data_path, cache) == ({"generation": 2}, False)
    data_path.write_text("dataset-two")
    assert modeling.load_or_train(None, data_path, cache) == ({"generation": 3}, False)
    monkeypatch.setattr(modeling.sklearn, "__version__", "changed")
    assert modeling.load_or_train(None, data_path, cache) == ({"generation": 4}, False)


def test_health_endpoint(dashboard):
    response = dashboard.app.test_client().get("/health")
    assert response.status_code == 200
    assert response.json == {"status": "ok", "models_ready": 5}


def test_deployment_requires_matching_prebuilt_artifact(tmp_path, monkeypatch):
    data = tmp_path / "data.csv"
    data.write_text("dataset")
    def unexpected_training(_df):
        pytest.fail("Deployment startup must not train a model")
    monkeypatch.setattr(modeling, "train_bundle", unexpected_training)
    with pytest.raises(RuntimeError, match="python build.py"):
        modeling.load_or_train(None, data, tmp_path / "missing", require_cached=True)


