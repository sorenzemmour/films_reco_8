from flask import Flask, render_template, request, jsonify
import pandas as pd
import os
import json
import joblib
import shap

app = Flask(__name__)

BASE_DIR = os.path.dirname(__file__)

# =============================
# 1) CHARGER MODÈLE + METADATA (AU DÉMARRAGE)
# =============================
MODEL_PATH = os.path.join(BASE_DIR, "best_model.pkl")
METADATA_PATH = os.path.join(BASE_DIR, "model_metadata.json")

best_model = joblib.load(MODEL_PATH)

with open(METADATA_PATH, "r", encoding="utf-8") as f:
    metadata = json.load(f)

features_to_use = metadata["features_to_use"]
categorical_cols = metadata["categorical_cols"]
categories_map = metadata["categories"]

explainer = shap.TreeExplainer(best_model)

# Cache simple mémoire
explain_cache = {}

# =============================
# 2) CHARGER DONNÉES (AU DÉMARRAGE)
# =============================
PRED_PATH = os.path.join(BASE_DIR, "predictions_films.csv")
FEAT_PATH = os.path.join(BASE_DIR, "features_films.parquet")

df_pred = pd.read_csv(PRED_PATH, encoding="utf-8")
df_feat = pd.read_parquet(FEAT_PATH)

# Indexation pour lookup rapide
df_pred = df_pred.set_index("original_index", drop=False)
df_feat = df_feat.set_index("original_index", drop=False)


def load_df(csv_filename: str) -> pd.DataFrame:
    csv_path = os.path.join(BASE_DIR, csv_filename)
    df = pd.read_csv(csv_path, encoding="utf-8")
    df["rk_sc"] = df.index + 1
    return df

def apply_filters(df: pd.DataFrame):
    year_min = request.args.get("year_min", default=df["year_rym"].min(), type=float)
    year_max = request.args.get("year_max", default=df["year_rym"].max(), type=float)
    proba_min = request.args.get("proba_min", default=0.0, type=float)
    proba_max = request.args.get("proba_max", default=1.0, type=float)
    seen = request.args.get("seen", default="0")
    country = request.args.getlist("country")
    sort = request.args.get("sort", default="rk_sc")
    order = request.args.get("order", default="asc")

    if seen == "0":
        df = df[df["user_rating_sc"].isna()]
    else:
        df = df[df["user_rating_sc"].notna()]

    df = df[(df["year_rym"] >= year_min) & (df["year_rym"] <= year_max)]
    df = df[(df["proba_must_watch"] >= proba_min) & (df["proba_must_watch"] <= proba_max)]

    if country:
        df = df[df["country_sc"].isin(country)]

    if sort == "rk_rym":
        df = df.sort_values(by="rk_rym", ascending=(order == "asc"), na_position="last")
    else:
        df = df.sort_values(by=sort, ascending=(order == "asc"))

    countries = sorted(df["country_sc"].dropna().unique())
    films = df.to_dict(orient="records")

    ctx = dict(
        films=films,
        year_min=int(year_min),
        year_max=int(year_max),
        country=country,
        countries=countries,
        proba_min=proba_min,
        proba_max=proba_max,
        seen=seen,
        sort=sort,
        order=order,
    )
    return ctx

@app.route("/")
def index():
    df = load_df("predictions_films.csv")
    ctx = apply_filters(df)
    ctx["active_tab"] = "base"
    return render_template("index.html", **ctx)

@app.route("/alt")
def alt():
    df = load_df("predictions_films_alt.csv")
    ctx = apply_filters(df)
    ctx["active_tab"] = "alt"
    return render_template("index.html", **ctx)

@app.route("/explain/<int:film_id>")
def explain_film(film_id):
    try:
        if film_id not in df_feat.index:
            return jsonify({"error": "Film not found", "film_id": film_id}), 404

        row_pred = df_pred.loc[[film_id]]
        row_feat = df_feat.loc[[film_id]]

        X_row = row_feat[features_to_use].copy()

        for col in categorical_cols:
            X_row[col] = pd.Categorical(X_row[col], categories=categories_map[col])

        shap_values = explainer(X_row)

        predicted_class = int(row_pred["prediction_classe"].values[0])

        if len(shap_values.values.shape) == 3:
            values = shap_values[0, :, predicted_class].values
            base_value = explainer.expected_value[predicted_class]
        else:
            values = shap_values[0].values
            base_value = explainer.expected_value

        contributions = []
        for feature, val, shap_val in zip(features_to_use, X_row.iloc[0], values):
            contributions.append({"feature": feature, "value": str(val), "shap": float(shap_val)})

        contributions = sorted(contributions, key=lambda x: abs(x["shap"]), reverse=True)[:10]

        result = {
            "base_value": float(base_value),
            "prediction_proba": float(row_pred["proba_must_watch"].values[0]),
            "prediction_label": row_pred["prediction_label"].values[0],
            "contributions": contributions
        }
        return jsonify(result)

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc().splitlines()[-30:]}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)