"""Prepare model artifacts and static assets before starting a deployment."""
import os
from pathlib import Path
import shutil

import pandas as pd
from plotly.offline import get_plotlyjs

from modeling import FEATURE_COLUMNS, cache_artifact_path, load_or_train

BASE_DIR = Path(__file__).resolve().parent


def main():
    dataset = Path(os.environ.get("FLIGHT_DATA_PATH", BASE_DIR / "flight_price_prediction.csv"))
    cache = Path(os.environ.get("FLIGHT_MODEL_CACHE", BASE_DIR / ".model_cache"))
    df = pd.read_csv(dataset, dtype={column: "category" for column in FEATURE_COLUMNS if column not in ("duration", "days_left")})
    df.columns = df.columns.str.strip().str.lower()
    bundle, hit = load_or_train(df, dataset, cache)
    artifact = cache_artifact_path(dataset, cache)
    if not artifact.exists():
        raise RuntimeError("Build did not persist a model artifact")
    packaged = BASE_DIR / "model_artifacts"
    packaged.mkdir(exist_ok=True)
    for previous in packaged.glob("models-*.joblib"):
        if previous.name != artifact.name:
            previous.unlink()
    if artifact.resolve() != (packaged / artifact.name).resolve():
        shutil.copy2(artifact, packaged / artifact.name)
    static = BASE_DIR / "static"
    (static / "plotly.min.js").write_text(get_plotlyjs(), encoding="utf-8")
    # Keep the committed CDN assets synchronized with the editable source files.
    destination = BASE_DIR / "public" / "static"
    destination.mkdir(parents=True, exist_ok=True)
    for asset in static.iterdir():
        if asset.is_file() and asset.name != "Plane photo.png":
            shutil.copy2(asset, destination / asset.name)
    print(f"Prepared {len(bundle['models'])} models ({'cached' if hit else 'trained'}) and static assets", flush=True)


if __name__ == "__main__":
    main()
