from flask import Flask, jsonify, render_template, request
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from pathlib import Path
from modeling import DEFAULT_MODEL, FEATURE_COLUMNS, TARGET_COLUMN, COVERAGE, load_or_train

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)
DATASET_PATH = Path(os.environ.get("FLIGHT_DATA_PATH", BASE_DIR / "flight_price_prediction.csv"))
df = pd.read_csv(DATASET_PATH, dtype={column: "category" for column in FEATURE_COLUMNS if column not in ("duration", "days_left")})
df.columns = df.columns.str.strip().str.lower()
PRICE_FLOOR = 0.0
PRICE_CEILING = float(df[TARGET_COLUMN].max()) * 1.25
bundle, cache_hit = load_or_train(
    df, DATASET_PATH, os.environ.get("FLIGHT_MODEL_CACHE", BASE_DIR / ("model_artifacts" if (BASE_DIR / "model_artifacts").exists() else ".model_cache")),
    require_cached=os.environ.get("VERCEL") == "1" or os.environ.get("FLIGHT_REQUIRE_CACHE") == "1",
)
models, model_metrics = bundle["models"], bundle["metrics"]
model_r2 = model_metrics[DEFAULT_MODEL]["r2"]
model_mae = model_metrics[DEFAULT_MODEL]["mae"]
regression_df = bundle["regression"]
airline_options = sorted(df["airline"].dropna().astype(str).unique().tolist())
source_options = sorted(df["source_city"].dropna().astype(str).unique().tolist())
destination_options = sorted(df["destination_city"].dropna().astype(str).unique().tolist())
departure_options = sorted(df["departure_time"].dropna().astype(str).unique().tolist())
arrival_options = sorted(df["arrival_time"].dropna().astype(str).unique().tolist())
stops_options = sorted(df["stops"].dropna().astype(str).unique().tolist())
class_options = sorted(df["class"].dropna().astype(str).unique().tolist())
airline_set = set(airline_options)
source_set = set(source_options)
destination_set = set(destination_options)
departure_set = set(departure_options)
arrival_set = set(arrival_options)
stops_set = set(stops_options)
class_set = set(class_options)
duration_min = float(df["duration"].min())
duration_max = float(df["duration"].max())
days_left_min = int(df["days_left"].min())
days_left_max = int(df["days_left"].max())
total_flights = int(len(df))
flight_numbers = df["flight"].dropna().astype(str).str.strip() if "flight" in df.columns else pd.Series(dtype=str)
normalized_classes = df["class"].fillna("").astype(str).str.strip().str.lower()
business_unique_flights = int(
    flight_numbers[normalized_classes.eq("business")].nunique()
) if "flight" in df.columns else 0
economy_unique_flights = int(
    flight_numbers[normalized_classes.eq("economy")].nunique()
) if "flight" in df.columns else 0
gallery_images = [
    {"filename": "AirAsia.png", "label": "AirAsia", "airline": "AirAsia"},
    {"filename": "airindia.png", "label": "Air India", "airline": "Air_India"},
    {"filename": "Go first.png", "label": "GO FIRST", "airline": "GO_FIRST"},
    {"filename": "indigo.png", "label": "Indigo", "airline": "Indigo"},
    {"filename": "spicejet.png", "label": "SpiceJet", "airline": "SpiceJet"},
    {"filename": "vistara.png", "label": "Vistara", "airline": "Vistara"},
]
def read_text_value(payload, key):
    return str(payload.get(key, "")).strip()

def bound_price(value):
    return max(PRICE_FLOOR, min(PRICE_CEILING, float(value)))


def apply_transparent_theme(fig):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#103c3c"),
        autosize=True,
        height=360,
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=55, r=30, t=45, b=65),
    )
    fig.update_xaxes(automargin=True, showgrid=True, gridcolor="rgba(16,60,60,0.12)", zeroline=False)
    fig.update_yaxes(automargin=True, showgrid=True, gridcolor="rgba(16,60,60,0.12)", zeroline=False)
    return fig


@app.route("/")
def home():
    active_tab = request.args.get("view", "dashboard")
    if active_tab not in {"dashboard", "analytics", "history"}:
        active_tab = "dashboard"
    filters = {key: request.args.get(key, "").strip() for key in ("airline", "source_city", "destination_city", "class")}
    analytics_df = df
    regression = regression_df
    for key, value in filters.items():
        if value:
            analytics_df = analytics_df[analytics_df[key].eq(value)]
            regression = regression[regression[key].eq(value)]
    analytics_count = len(analytics_df)
    # Scatter plots are sampled for responsive rendering; aggregate plots use all matches.
    scatter_df = analytics_df.sample(n=min(len(analytics_df), 5000), random_state=42)
    regression = regression.sample(n=min(len(regression), 5000), random_state=42)
    counts = analytics_df["airline"].value_counts().reset_index()
    counts.columns = ["airline", "count"]

    fig1 = px.bar(counts, x="airline", y="count", color="count")
    apply_transparent_theme(fig1)
    graph1 = fig1.to_html(full_html=False, include_plotlyjs=False)

    price_counts, price_edges = np.histogram(analytics_df["price"], bins=30)
    fig2 = go.Figure(go.Bar(x=(price_edges[:-1] + price_edges[1:]) / 2, y=price_counts,
                           width=np.diff(price_edges), marker_color="#168e96"))
    fig2.update_layout(xaxis_title="Price", yaxis_title="Count", bargap=0.04)
    apply_transparent_theme(fig2)
    graph2 = fig2.to_html(full_html=False, include_plotlyjs=False)

    fig3 = px.scatter(scatter_df, x="duration", y="price", color="price")
    apply_transparent_theme(fig3)
    graph3 = fig3.to_html(full_html=False, include_plotlyjs=False)

    # Send exact quartiles/whiskers rather than 300k raw prices to the browser.
    fig4 = go.Figure()
    palette = px.colors.qualitative.Plotly
    for index, (airline, group) in enumerate(analytics_df.groupby("airline")):
        prices = group["price"]
        q1, median, q3 = prices.quantile([0.25, 0.5, 0.75])
        iqr = q3 - q1
        inside = prices[prices.between(q1 - 1.5 * iqr, q3 + 1.5 * iqr)]
        fig4.add_trace(go.Box(name=str(airline), q1=[q1], median=[median], q3=[q3],
                             lowerfence=[float(inside.min())], upperfence=[float(inside.max())],
                             boxpoints=False, marker_color=palette[index % len(palette)]))
    fig4.update_layout(xaxis_title="Airline", yaxis_title="Price", showlegend=False)
    apply_transparent_theme(fig4)
    graph4 = fig4.to_html(full_html=False, include_plotlyjs=False)

    corr = analytics_df[["duration", "days_left", "price"]].corr().fillna(0)
    fig5 = px.imshow(corr, text_auto=".2f", color_continuous_scale="Viridis", zmin=-1, zmax=1)
    apply_transparent_theme(fig5)
    graph5 = fig5.to_html(full_html=False, include_plotlyjs=False)

    fig6 = px.pie(counts, names="airline", values="count")
    apply_transparent_theme(fig6)
    graph6 = fig6.to_html(full_html=False, include_plotlyjs=False)

    fig7 = px.scatter(
        regression,
        x="actual_price",
        y="predicted_price",
        opacity=0.5,
        title="Regression Plot: Actual vs Predicted",
    )
    min_price = float(min(regression["actual_price"].min(), regression["predicted_price"].min()))
    max_price = float(max(regression["actual_price"].max(), regression["predicted_price"].max()))
    if regression.empty:
        min_price, max_price = 0, PRICE_CEILING
    fig7.add_shape(
        type="line",
        x0=min_price,
        y0=min_price,
        x1=max_price,
        y1=max_price,
        line=dict(color="red", width=2, dash="dash"),
    )
    fig7.update_layout(
        xaxis_title="Actual Price",
        yaxis_title="Predicted Price",
    )
    apply_transparent_theme(fig7)
    graph7 = fig7.to_html(full_html=False, include_plotlyjs=False)

    class_avg_price = (
        analytics_df.groupby("class", as_index=False)["price"]
        .mean()
        .sort_values("price", ascending=False)
    )
    fig8 = px.bar(
        class_avg_price,
        x="class",
        y="price",
        color="price",
        title="Average Price by Class",
    )
    fig8.update_layout(
        xaxis_title="Class",
        yaxis_title="Average Price",
    )
    apply_transparent_theme(fig8)
    graph8 = fig8.to_html(full_html=False, include_plotlyjs=False)
    return render_template(
        "index.html",
        active_tab=active_tab,
        sample_flight={"model": DEFAULT_MODEL, "airline": str(df.iloc[0]["airline"]),
                       "source": str(df.iloc[0]["source_city"]), "destination": str(df.iloc[0]["destination_city"]),
                       **{key: str(df.iloc[0][key]) for key in ("departure_time", "arrival_time", "stops", "class", "duration", "days_left")}},
        graph1=graph1,
        graph2=graph2,
        graph3=graph3,
        graph4=graph4,
        graph5=graph5,
        graph6=graph6,
        graph7=graph7,
        graph8=graph8,
        airlines=airline_options,
        sources=source_options,
        destinations=destination_options,
        default_destination=next(value for value in destination_options if value != source_options[0]),
        departure_times=departure_options,
        arrival_times=arrival_options,
        stops=stops_options,
        classes=class_options,
        duration_min=round(duration_min, 2),
        duration_max=round(duration_max, 2),
        days_left_min=days_left_min,
        days_left_max=days_left_max,
        total_flights=analytics_count,
        dataset_total=total_flights,
        filters=filters,
        evaluations=bundle["evaluations"],
        split_counts=bundle["split_counts"],
        cache_hit=cache_hit,
        business_unique_flights=int(analytics_df.loc[analytics_df["class"].str.lower().eq("business"), "flight"].nunique()) if "flight" in analytics_df else 0,
        economy_unique_flights=int(analytics_df.loc[analytics_df["class"].str.lower().eq("economy"), "flight"].nunique()) if "flight" in analytics_df else 0,
        accuracy_pct=round(model_r2 * 100, 2),
        model_r2=round(model_r2, 4),
        model_mae=round(model_mae, 2),
        gallery_images=gallery_images,
        model_options=list(model_metrics.values()),
        default_model=DEFAULT_MODEL,
        default_model_name=model_metrics[DEFAULT_MODEL]["name"],
    )
@app.get("/health")
def health():
    return jsonify({"status": "ok", "models_ready": len(models)})


@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400
    model_id = read_text_value(data, "model") or DEFAULT_MODEL
    if model_id not in models:
        return jsonify({"error": "Unknown prediction model."}), 400
    airline = read_text_value(data, "airline")
    source_city = read_text_value(data, "source")
    destination_city = read_text_value(data, "destination")
    departure_time = read_text_value(data, "departure_time")
    arrival_time = read_text_value(data, "arrival_time")
    stops = read_text_value(data, "stops")
    travel_class = read_text_value(data, "class")
    if not (
        airline in airline_set
        and source_city in source_set
        and destination_city in destination_set
        and departure_time in departure_set
        and arrival_time in arrival_set
        and stops in stops_set
        and travel_class in class_set
    ):
        return jsonify({"error": "Invalid categorical values provided."}), 400
    try:
        duration = float(data.get("duration"))
        raw_days_left = float(data.get("days_left"))
        if not np.isfinite(duration) or not np.isfinite(raw_days_left) or not raw_days_left.is_integer():
            raise ValueError
        days_left = int(raw_days_left)
    except (TypeError, ValueError):
        return jsonify({"error": "Duration and days_left must be numeric."}), 400
    if source_city == destination_city:
        return jsonify({"error": "Source and destination must be different."}), 400
    if not duration_min <= duration <= duration_max or not days_left_min <= days_left <= days_left_max:
        return jsonify({"error": f"Duration must be {duration_min}–{duration_max} hours and days_left must be a whole number from {days_left_min}–{days_left_max}."}), 400
    if duration <= 0 or days_left < 0:
        return jsonify({"error": "Duration must be > 0 and days_left must be >= 0."}), 400
    input_df = pd.DataFrame(
        [
            {
                "airline": airline,
                "source_city": source_city,
                "destination_city": destination_city,
                "departure_time": departure_time,
                "arrival_time": arrival_time,
                "stops": stops,
                "class": travel_class,
                "duration": duration,
                "days_left": days_left,
            }
        ],
        columns=FEATURE_COLUMNS,
    )
    prediction = bound_price(models[model_id].predict(input_df)[0])
    metrics = model_metrics[model_id]
    return jsonify({
        "price": round(prediction, 2),
        "range_low": round(bound_price(prediction - bundle["radii"][model_id]), 2),
        "range_high": round(bound_price(prediction + bundle["radii"][model_id]), 2),
        "nominal_coverage_pct": int(COVERAGE * 100),
        "test_coverage_pct": metrics["coverage_pct"],
        "model": model_id,
        "model_name": metrics["name"],
        "accuracy_pct": round(metrics["r2"] * 100, 2),
        "r2": metrics["r2"],
        "mae": metrics["mae"],
    })

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=False)
