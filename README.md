# Flight Price Analysis and Prediction Dashboard

This project is a Flask-based dashboard for analyzing airline ticket data and predicting flight prices. It combines interactive Plotly visualizations with a scikit-learn regression model so users can explore price trends and estimate fares from flight details.

## Dashboard Sections

- **Predict:** a focused fare form, airline shortcuts, and a sample-flight button.
- **Analytics:** route/class filters, dataset counts, and interactive charts.
- **History:** browser-local predictions with CSV export.
Model evaluation tables are available under **Model performance** in Analytics. Interview and resume material stays in the documentation.

Tabs support keyboard navigation and direct links such as `/?view=analytics`. Filter submissions return to Analytics. `GET /health` reports readiness once the models are loaded.

For placement preparation, see [the interview guide](docs/INTERVIEW_GUIDE.md). It includes a demo script, technical questions, an honest resume bullet, and remaining deployment work. Screenshots below show an earlier layout.

## Screenshots

### Dashboard Overview

![Flight price dashboard overview](screenshots/dashboard-overview.png)

The overview section shows the airline logo selector, model evaluation metrics, total flight records, and unique flight counts for Business and Economy classes. It gives a quick summary of the dataset and the current prediction model performance.

### Analytics Charts

| Flights by Airline | Airline Share |
| --- | --- |
| ![Flights by airline chart](screenshots/flights-by-airline.png) | ![Airline share pie chart](screenshots/airline-share.png) |

**Flights by Airline:** Shows how many flight records are available for each airline. This helps identify which airlines dominate the dataset.

**Airline Share:** Displays the same airline distribution as percentages. It makes it easier to compare each airline's overall share in the dataset.

| Price Distribution | Duration vs Price |
| --- | --- |
| ![Price distribution histogram](screenshots/price-distribution.png) | ![Duration vs price scatter plot](screenshots/duration-vs-price.png) |

**Price Distribution:** Shows how ticket prices are spread across the dataset. Most tickets fall into lower price ranges, while higher-priced tickets appear less frequently.

**Duration vs Price:** Compares flight duration with ticket price. It helps reveal how price changes across short, medium, and long-duration flights.

| Airline vs Price | Correlation Heatmap |
| --- | --- |
| ![Airline vs price box plot](screenshots/airline-vs-price.png) | ![Correlation heatmap](screenshots/correlation-heatmap.png) |

**Airline vs Price:** Compares price ranges for each airline using box plots. This highlights median prices, spread, and possible outliers for different airlines.

**Correlation Heatmap:** Shows relationships between numeric columns such as duration, days left, and price. Stronger values indicate features that move more closely together.

| Regression: Actual vs Predicted | Average Price by Class |
| --- | --- |
| ![Regression actual vs predicted chart](screenshots/regression-actual-vs-predicted.png) | ![Average price by class chart](screenshots/average-price-by-class.png) |

**Regression: Actual vs Predicted:** Compares actual ticket prices with model-predicted prices. Points closer to the red diagonal line indicate better predictions.

**Average Price by Class:** Compares average ticket prices for Business and Economy classes. It clearly shows the price gap between the two travel classes.

### Price Prediction

![Predict flight price form](screenshots/predict-flight-price.png)

The prediction form lets users choose airline, source, destination, timing, stops, class, duration, and days left before travel. After submission, it returns the predicted flight price along with model metrics.

## Key Features

- Flight count analysis by airline.
- Airline market-share visualization.
- Price distribution and duration-vs-price analysis.
- Airline-wise price comparison using box plots.
- Correlation heatmap for numeric features.
- Actual-vs-predicted regression performance chart.
- Average price comparison between Business and Economy classes.
- Five selectable prediction models with held-out metrics.
- Calibrated fare ranges targeting 90% coverage, with observed test coverage.
- Airline, source, destination, and class analytics filters.
- Browser-local prediction history (latest 100) with CSV export and clear controls.
- Dataset- and code-aware model caching.
- Unseen-route and held-out booking lead-time evaluations.

## Model Summary

The application trains regression pipelines with preprocessing for numeric and categorical flight features. It uses:

- Numeric inputs: `duration`, `days_left`
- Categorical inputs: `airline`, `source_city`, `destination_city`, `departure_time`, `arrival_time`, `stops`, `class`
- Target output: `price`

Five selectable models are available: Linear Regression, Ridge Regression, Decision Tree, Random Forest, and Extra Trees (default). Each trains on actual prices using the same reproducible 64% fit / 16% calibration / 20% test split and independent preprocessing. The comparison table reports held-out R2 and MAE in rupees for each model; the regression chart shows Extra Trees predictions. R2 is a regression score, not classification accuracy.

Models train on the first startup and load from `.model_cache/` on subsequent starts. The cache key includes dataset content, `modeling.py`, and scikit-learn, NumPy, and pandas versions. Writes are atomic; a corrupt cache triggers retraining. Only use locally generated cache files. Delete `.model_cache/` and `model_artifacts/`, then rerun `python3 build.py` to force retraining. Set `FLIGHT_DATA_PATH` or `FLIGHT_MODEL_CACHE` to override the default paths.

Fare ranges use a split-conformal absolute-error radius for each model, calibrated on rows excluded from fitting and testing. The comparison table shows measured test coverage; nominal 90% coverage assumes exchangeable observations and may not hold for unfamiliar routes or shifted data. Prices and range bounds are clipped to the supported price interval.

Generalization checks fit separate Extra Trees models on entire held-out directional routes and on held-out lead times (train with `days_left > 7`, test with `days_left <= 7`). These checks never replace the serving model. This CSV has no travel-date field, so chronological backtesting requires a new dataset with dates. The diagnostic splits overlap with the main split and serve as separate evaluations, not additional independent evidence.

Analytics filters affect dataset counts and charts, including matching regression test points; model metrics stay global. Aggregate charts use all matches (box plots send quartiles/whiskers without individual outliers); scatter plots sample at most 5,000 rows. History is stored only in browser local storage on the same origin and device. CSV export includes inputs, model, fare range, metrics, and timestamp.

Tree ensembles increase initial startup time and memory usage. The prediction form selects the model, and API clients can pass `model` as `linear`, `ridge`, `decision_tree`, `random_forest`, or `extra_trees`. Omitting it uses Extra Trees. Responses include `model` and `model_name` alongside price and that model’s metrics.

## Tech Stack

- Python
- Flask
- Pandas
- NumPy
- Plotly
- scikit-learn

## Project Structure

```text
Fight-price-analysis-prediction-dashboard/
|-- app.py
|-- modeling.py
|-- tests/
|-- flight_price_prediction.csv
|-- README.md
|-- screenshots/
|-- static/
`-- templates/
```

## Run Locally

Install the required Python packages:

```bash
python3 -m pip install -r requirements.txt
```

Start the Flask app:

```bash
python3 build.py
python3 app.py
```

Open the dashboard in your browser:

```text
http://127.0.0.1:5000/
```

## Prediction Endpoint

The app exposes a `POST /predict` endpoint. It accepts flight details as JSON and returns:

- Predicted flight price
- Estimated fare bounds (`range_low`, `range_high`)
- Nominal and observed test range coverage
- R2 percentage (`accuracy_pct`, retained for compatibility; not classification accuracy)
- R2 score
- Mean absolute error


Example request:

```bash
curl http://127.0.0.1:5000/predict \
  -H 'Content-Type: application/json' \
  -d '{"model":"extra_trees","airline":"SpiceJet","source":"Delhi","destination":"Mumbai","departure_time":"Evening","arrival_time":"Night","stops":"zero","class":"Economy","duration":2.17,"days_left":1}'
```

The API rejects identical source/destination cities, unknown categories or models, non-finite numeric inputs, fractional lead times, and values outside the dataset duration/lead-time bounds.

## Verification

```bash
python3 -m pip install pytest
python3 -m pytest -q
node --test tests/*.test.cjs
```

The Python tests use a small synthetic dataset and isolated cache. Browser behavior tests run with Node's built-in test runner.


## Deployment

Render and Vercel configuration is included. Both run `python build.py` before serving the app so model fitting stays out of cold starts. See [deployment instructions and verification limits](docs/DEPLOYMENT.md).
