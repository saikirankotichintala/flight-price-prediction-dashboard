# Flight fare estimator: interview guide

## A 60-second explanation

I built a Flask application that estimates flight fares from nine flight features and lets users explore a historical dataset. It compares five scikit-learn regression pipelines, handles missing values and unknown categories, and separates training, range calibration, and testing. Users can switch models, estimate a fare range, explore filtered charts, and export their prediction history. Trained models are cached using dataset, training-code, and library fingerprints.

## A three-minute demonstration

1. Open Predict and choose **Try sample flight**, then **Predict Price**.
2. Change the model and compare the estimates. A single estimate is not evidence that one model is better.
3. Open Analytics and filter a route or cabin class.
4. Open History, export CSV, and explain that history stays in browser storage.
5. Open Analytics → Model performance. Compare R2, rupee MAE, observed interval coverage, and the unseen-route/lead-time checks.

## Technical questions to prepare for

- **Why a pipeline?** Preprocessing fits only on the fitting partition and is reused consistently for inference. Each model has its own fitted preprocessing.
- **Why MAE and R2?** MAE expresses error in rupees; R2 compares explained variation to the mean-price baseline. R2 is not a percentage of correct fare predictions.
- **Why separate calibration data?** Residuals used for the split-conformal interval radius come from data outside fitting and testing. Nominal coverage depends on exchangeability and can degrade under distribution shift.
- **Is the model overfitting?** Training/test gaps were small in the prior assessment, but random splits can share similar flight records. Grouped route evaluation is a harder generalization check. Use learning curves and cross-validation before claiming a model is optimally tuned.
- **Why do route and lead-time scores drop?** Their test distributions differ from fitting data. Trees also struggle with numeric extrapolation.
- **What prevents stale models?** Cache keys incorporate the CSV content, training source, and relevant dependency versions. Corrupt artifacts trigger retraining; files are replaced atomically.
- **What is deployment-ready today?** A Gunicorn Procfile and `/health` readiness endpoint exist. A public deployment, CI pipeline, dependency lock, persistent cache policy, and load testing remain work to complete.

## Honest resume bullet

Built a flight fare estimation dashboard with five scikit-learn pipelines, a validated Flask API, calibrated fare ranges, route-level evaluation, cached model artifacts, and browser-local prediction history with CSV export.

Only add a performance number after reading the current Model performance table. Name the split and metric, for example “test R2 on a random holdout,” and do not call R2 classification accuracy. Do not claim live airline pricing, production traffic, or deployment unless actually implemented and verified.

## Next improvements

- Collect dated observations and evaluate chronologically.
- Add grouped cross-validation and learning curves using development data; reserve the final test set.
- Pin dependencies and automate tests in CI.
- Measure latency and memory with multiple Gunicorn workers.
- Monitor drift and set a retraining policy before production use.
