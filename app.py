from flask import Flask, render_template, request
import pandas as pd
import os

app = Flask(__name__)

BASE_DIR = os.path.dirname(__file__)

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
    # 👉 mets ici ton autre fichier OU une autre logique de calcul
    df = load_df("predictions_films_alt.csv")  # par ex
    # si ta proba s'appelle autrement, renomme pour réutiliser le template :
    # df["proba_must_watch"] = df["proba_autre_modele"]

    ctx = apply_filters(df)
    ctx["active_tab"] = "alt"
    return render_template("index.html", **ctx)  # ou "alt.html" si tu veux une page différente

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
