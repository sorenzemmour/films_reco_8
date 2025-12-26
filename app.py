import os
from flask import Flask, render_template, request
import pandas as pd

app = Flask(__name__)

@app.route("/")
def index():
    csv_path = os.path.join(os.path.dirname(__file__), "predictions_films.csv")
    df = pd.read_csv(csv_path, encoding="utf-8")

    df["rk_sc"] = df.index + 1

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

    return render_template(
        "index.html",
        films=films,
        year_min=int(year_min),
        year_max=int(year_max),
        country=country,
        countries=countries,
        proba_min=proba_min,
        proba_max=proba_max,
        seen=seen,
        sort=sort,
        order=order
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
