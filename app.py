import os
from datetime import datetime
from urllib.parse import urlencode

from flask import Flask, render_template, request, redirect, url_for, flash

from models import db, WeatherRecord
import weather_api as wa

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///weather.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()

    @app.route("/", methods=["GET"])
    def index():
        sort = request.args.get("sort", "requested_date")
        direction = request.args.get("dir", "desc")

        sortable = {
            "id": WeatherRecord.id,
            "requested_date": WeatherRecord.requested_date,
            "city": WeatherRecord.city,
            "country": WeatherRecord.country,
            "temp_max_c": WeatherRecord.temp_max_c,
            "temp_min_c": WeatherRecord.temp_min_c,
            "precip_mm": WeatherRecord.precip_mm,
            "wind_max_kmh": WeatherRecord.wind_max_kmh,
            "source": WeatherRecord.source,
            "created_at": WeatherRecord.created_at,
        }
        sort_col = sortable.get(sort, WeatherRecord.requested_date)
        records = WeatherRecord.query.order_by(sort_col.asc() if direction == "asc" else sort_col.desc()).all()

        def sort_link(col_name):
            dir_next = "asc"
            if sort == col_name and direction == "asc":
                dir_next = "desc"
            params = {"sort": col_name, "dir": dir_next}
            return f"?{urlencode(params)}"

        return render_template("index.html", records=records, sort=sort, direction=direction, sort_link=sort_link)

    @app.route("/add", methods=["POST"])
    def add():
        requested_date_str = request.form.get("requested_date", "").strip()
        country = request.form.get("country", "").strip()
        city = request.form.get("city", "").strip()
        region = request.form.get("region", "").strip()  # optional

        if not requested_date_str or not country or not city:
            flash("Please fill in date, country, and city.", "error")
            return redirect(url_for("index"))

        try:
            requested_date = datetime.strptime(requested_date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Date must be in YYYY-MM-DD format.", "error")
            return redirect(url_for("index"))

        lat = request.form.get("lat")
        lon = request.form.get("lon")
        tz = request.form.get("timezone")

        if not lat or not lon:
            try:
                candidates = wa.search_locations(city=city, country=country, admin1=region, count=6)
            except Exception as e:
                flash(f"Geocoding failed: {e}", "error")
                return redirect(url_for("index"))

            if not candidates:
                rtxt = f" ({region})" if region else ""
                flash(f"No matching locations found for {city}, {country}{rtxt}.", "error")
                return redirect(url_for("index"))

            if len(candidates) > 1:
                return render_template(
                    "choose_location.html",
                    candidates=candidates,
                    requested_date=requested_date_str,
                    city=city,
                    country=country
                )
            else:
                selected = candidates[0]
                lat = selected["latitude"]
                lon = selected["longitude"]
                tz = selected.get("timezone", "UTC")

        try:
            weather = wa.fetch_weather_for_date(
                city=city, country=country, target_date=requested_date,
                latitude=float(lat), longitude=float(lon), timezone=tz
            )
        except Exception as e:
            flash(f"Weather fetch failed: {e}", "error")
            return redirect(url_for("index"))

        record = WeatherRecord(
            requested_date=requested_date,
            city=city,
            country=country,
            temp_max_c=weather.get("temp_max_c"),
            temp_min_c=weather.get("temp_min_c"),
            precip_mm=weather.get("precip_mm"),
            wind_max_kmh=weather.get("wind_max_kmh"),
            source=weather.get("source"),
        )
        db.session.add(record)
        db.session.commit()
        flash("Weather record added.", "success")
        return redirect(url_for("index"))

    @app.route("/delete/<int:record_id>", methods=["POST"])
    def delete(record_id):
        rec = WeatherRecord.query.get_or_404(record_id)
        db.session.delete(rec)
        db.session.commit()
        flash("Record deleted.", "success")
        return redirect(request.referrer or url_for("index"))

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
