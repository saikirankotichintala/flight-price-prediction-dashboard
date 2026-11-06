import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import modeling


@pytest.fixture(scope="module")
def dashboard(tmp_path_factory):
    folder = tmp_path_factory.mktemp("dashboard")
    rng = np.random.default_rng(19)
    rows = []
    cities = ["Delhi", "Mumbai", "Chennai", "Bangalore"]
    for i in range(900):
        source = cities[i % 4]
        destination = cities[(i % 4 + 1 + (i // 4) % 3) % 4]
        days = int(rng.integers(1, 50))
        duration = float(rng.uniform(1, 12))
        business = i % 3 == 0
        rows.append({"airline": "Air_India" if i % 2 else "Indigo", "flight": f"F-{i % 30}",
                     "source_city": source, "destination_city": destination,
                     "departure_time": "Morning", "arrival_time": "Evening", "stops": "one",
                     "class": "Business" if business else "Economy", "duration": duration,
                     "days_left": days, "price": 3000 + 15000 * business + duration * 500 + (50 - days) * 100 + rng.normal(0, 200)})
    path = folder / "data.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    import os
    old = {key: os.environ.get(key) for key in ("FLIGHT_DATA_PATH", "FLIGHT_MODEL_CACHE")}
    os.environ["FLIGHT_DATA_PATH"] = str(path)
    os.environ["FLIGHT_MODEL_CACHE"] = str(folder / "cache")
    module = importlib.import_module("app")
    module.app.config.update(TESTING=True)
    yield module
    for key, value in old.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


