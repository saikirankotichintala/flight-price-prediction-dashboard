"""Reproducible model training, calibration, evaluation, and local caching."""
import hashlib
import logging
import math
import os
from pathlib import Path
import tempfile
import time

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeRegressor

FEATURE_COLUMNS = ["airline", "source_city", "destination_city", "departure_time", "arrival_time", "stops", "class", "duration", "days_left"]
NUMERIC_FEATURES = ["duration", "days_left"]
TARGET_COLUMN = "price"
DEFAULT_MODEL = "extra_trees"
COVERAGE = 0.90
MODEL_ESTIMATORS = {
    "linear": ("Linear Regression", LinearRegression()),
    "ridge": ("Ridge Regression", Ridge(alpha=10.0, solver="lsqr")),
    "decision_tree": ("Decision Tree", DecisionTreeRegressor(max_depth=18, min_samples_leaf=5, random_state=42)),
    "random_forest": ("Random Forest", RandomForestRegressor(n_estimators=40, max_depth=18, min_samples_leaf=3, max_samples=0.7, n_jobs=-1, random_state=42)),
    "extra_trees": ("Extra Trees", ExtraTreesRegressor(n_estimators=40, max_depth=18, min_samples_leaf=3, n_jobs=-1, random_state=42)),
}


def pipeline_for(model_id):
    preprocessor = ColumnTransformer([
        ("num", SimpleImputer(strategy="median"), NUMERIC_FEATURES),
        ("cat", Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]), [c for c in FEATURE_COLUMNS if c not in NUMERIC_FEATURES]),
    ])
    return Pipeline([("preprocessor", preprocessor), ("regressor", clone(MODEL_ESTIMATORS[model_id][1]))])


def metrics_for(actual, predicted):
    return {"r2": round(float(r2_score(actual, predicted)), 4),
            "mae": round(float(mean_absolute_error(actual, predicted)), 2)}


def calibration_radius(residuals, coverage=COVERAGE):
    """Finite-sample split-conformal order statistic, calibrated without test rows."""
    residuals = np.sort(np.asarray(residuals))
    rank = math.ceil((len(residuals) + 1) * coverage)
    if rank > len(residuals):
        raise ValueError("Not enough calibration rows for the requested coverage")
    return float(residuals[rank - 1])


def train_bundle(df):
    started = time.monotonic()
    X, y = df[FEATURE_COLUMNS], df[TARGET_COLUMN]
    # Keep test data untouched by fitting, calibration, and default-model choice.
    development, test = train_test_split(np.arange(len(df)), test_size=0.20, random_state=42)
    train, calibration = train_test_split(development, test_size=0.20, random_state=43)
    ceiling = float(y.max()) * 1.25
    models, metrics, predictions, radii = {}, {}, {}, {}
    for model_id, (label, _) in MODEL_ESTIMATORS.items():
        model = pipeline_for(model_id)
        model.fit(X.iloc[train], y.iloc[train])
        calibrated = np.clip(model.predict(X.iloc[calibration]), 0, ceiling)
        radius = calibration_radius(np.abs(y.iloc[calibration].to_numpy() - calibrated))
        predicted = np.clip(model.predict(X.iloc[test]), 0, ceiling)
        models[model_id], radii[model_id], predictions[model_id] = model, radius, predicted
        covered = (y.iloc[test].to_numpy() >= np.maximum(0, predicted - radius)) & (y.iloc[test].to_numpy() <= np.minimum(ceiling, predicted + radius))
        metrics[model_id] = {"id": model_id, "name": label, **metrics_for(y.iloc[test], predicted),
                             "coverage_pct": round(float(covered.mean()) * 100, 2), "radius": round(radius, 2)}
    evaluations = [{"name": "Random holdout", "status": "ok", "train_rows": len(train), "test_rows": len(test),
                    "detail": "64% fit / 16% calibration / 20% test", **metrics_for(y.iloc[test], predictions[DEFAULT_MODEL])}]
    # Separate diagnostic models; never replace the model used for predictions.
    routes = X["source_city"].astype(str) + " → " + X["destination_city"].astype(str)
    splits = []
    if routes.nunique() >= 2:
        route_train, route_test = next(GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42).split(X, y, routes))
        splits.append(("Unseen routes", route_train, route_test, "Entire directional routes held out; no matching route in training."))
    else:
        evaluations.append({"name": "Unseen routes", "status": "unavailable", "detail": "Requires at least two routes."})
    lead_train = np.flatnonzero(X["days_left"].to_numpy() > 7)
    lead_test = np.flatnonzero(X["days_left"].to_numpy() <= 7)
    splits.append(("Unseen lead times", lead_train, lead_test, "Train on >7 days before departure; test on ≤7 days. Not a chronological backtest."))
    for name, fit_rows, test_rows, detail in splits:
        if len(fit_rows) < 2 or len(test_rows) < 2:
            evaluations.append({"name": name, "status": "unavailable", "detail": "Insufficient rows for this split."})
            continue
        diagnostic = pipeline_for(DEFAULT_MODEL)
        diagnostic.fit(X.iloc[fit_rows], y.iloc[fit_rows])
        predicted = np.clip(diagnostic.predict(X.iloc[test_rows]), 0, float(y.iloc[fit_rows].max()) * 1.25)
        evaluations.append({"name": name, "status": "ok", "train_rows": len(fit_rows), "test_rows": len(test_rows),
                            "detail": detail, **metrics_for(y.iloc[test_rows], predicted)})
    regression = df.iloc[test][FEATURE_COLUMNS].copy()
    regression["actual_price"] = y.iloc[test].to_numpy()
    regression["predicted_price"] = predictions[DEFAULT_MODEL]
    return {"models": models, "metrics": metrics, "radii": radii, "regression": regression,
            "evaluations": evaluations, "split_counts": {"train": len(train), "calibration": len(calibration), "test": len(test)},
            "training_seconds": round(time.monotonic() - started, 2)}


def cache_artifact_path(dataset_path, cache_dir):
    digest = hashlib.sha256()
    for path in (Path(dataset_path), Path(__file__)):
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
    digest.update(f"{sklearn.__version__}:{np.__version__}:{pd.__version__}".encode())
    return Path(cache_dir) / f"models-{digest.hexdigest()}.joblib"


def load_or_train(df, dataset_path, cache_dir, require_cached=False):
    cache_dir = Path(cache_dir)
    artifact = cache_artifact_path(dataset_path, cache_dir)
    if artifact.exists():
        try:
            return joblib.load(artifact), True
        except Exception:
            logging.warning("Model cache unreadable; retraining", exc_info=True)
    if require_cached:
        raise RuntimeError("A matching model artifact is required. Run python build.py before starting the server.")
    bundle = train_bundle(df)
    # A failed cache write must not prevent serving newly trained models.
    temporary = None
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=cache_dir, suffix=".tmp", delete=False) as target:
            temporary = target.name
        joblib.dump(bundle, temporary, compress=3)
        os.replace(temporary, artifact)
    except OSError:
        logging.warning("Could not save model cache", exc_info=True)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
    return bundle, False
