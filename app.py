from flask import Flask, jsonify, render_template, request
import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

app = Flask(__name__)
df = pd.read_csv("flight_price_prediction.csv")
df.columns = df.columns.str.strip().str.lower()
FEATURE_COLUMNS = ["airline","source_city","destination_city","departure_time","arrival_time","stops","class","duration","days_left",]
TARGET_COLUMN = "price"
NUMERIC_FEATURES = ["duration", "days_left"]
CATEGORICAL_FEATURES = [c for c in FEATURE_COLUMNS if c not in NUMERIC_FEATURES]
X = df[FEATURE_COLUMNS].copy()
y = df[TARGET_COLUMN]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
preprocessor = ColumnTransformer(transformers=[("num",Pipeline(steps=[("imputer", SimpleImputer(strategy="median"))]),NUMERIC_FEATURES,),
("cat",Pipeline(steps=[("imputer", SimpleImputer(strategy="most_frequent")),("onehot", OneHotEncoder(handle_unknown="ignore")),]),
CATEGORICAL_FEATURES,),])
model = Pipeline(steps=[("preprocessor", preprocessor),("regressor", LinearRegression()),])
model.fit(X_train, y_train)
y_pred = model.predict(X_test)
model_r2 = r2_score(y_test, y_pred)
model_mae = mean_absolute_error(y_test, y_pred)
regression_df = pd.DataFrame({"actual_price": y_test.values,"predicted_price": y_pred,})
if len(regression_df) > 5000:
    regression_df = regression_df.sample(n=5000, random_state=42)
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
@app.route("/")
def home():
    counts = df["airline"].value_counts().reset_index()
    counts.columns = ["airline", "count"]

    fig1 = px.bar(counts, x="airline", y="count", color="count")
    graph1 = fig1.to_html(full_html=False)

    fig2 = px.histogram(df, x="price", nbins=30)
    graph2 = fig2.to_html(full_html=False)

    fig3 = px.scatter(df, x="duration", y="price", color="price")
    graph3 = fig3.to_html(full_html=False)

    fig4 = px.box(df, x="airline", y="price", color="airline")
    graph4 = fig4.to_html(full_html=False)

    corr = df.corr(numeric_only=True)
    corr_text = corr.apply(lambda col: col.map(lambda v: f"{v:.2f}"))
    fig5 = ff.create_annotated_heatmap(
        z=corr.values,
        x=list(corr.columns),
        y=list(corr.columns),
        annotation_text=corr_text.values,
        colorscale="Viridis",
        showscale=True,
    )
    graph5 = fig5.to_html(full_html=False)

    fig6 = px.pie(counts, names="airline", values="count")
    graph6 = fig6.to_html(full_html=False)

    fig7 = px.scatter(
        regression_df,
        x="actual_price",
        y="predicted_price",
        opacity=0.5,
        title="Regression Plot: Actual vs Predicted",
    )
    min_price = float(min(regression_df["actual_price"].min(), regression_df["predicted_price"].min()))
    max_price = float(max(regression_df["actual_price"].max(), regression_df["predicted_price"].max()))
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
    graph7 = fig7.to_html(full_html=False)

    class_avg_price = (
        df.groupby("class", as_index=False)["price"]
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
    graph8 = fig8.to_html(full_html=False)
    return render_template(
        "index.html",
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
        departure_times=departure_options,
        arrival_times=arrival_options,
        stops=stops_options,
        classes=class_options,
        duration_min=round(duration_min, 2),
        duration_max=round(duration_max, 2),
        days_left_min=days_left_min,
        days_left_max=days_left_max,
        accuracy_pct=round(model_r2 * 100, 2),
        model_r2=round(model_r2, 4),
        model_mae=round(model_mae, 2),
        gallery_images=gallery_images,
    )
@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json(silent=True) or {}
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
        days_left = int(float(data.get("days_left")))
    except (TypeError, ValueError):
        return jsonify({"error": "Duration and days_left must be numeric."}), 400
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
    prediction = model.predict(input_df)[0]
    return jsonify(
        {
            "price": round(float(prediction), 2),
            "accuracy_pct": round(model_r2 * 100, 2),
            "r2": round(model_r2, 4),
            "mae": round(model_mae, 2),
        }
    )
if __name__ == "__main__":
    app.run(debug=True)
