import os
from datetime import datetime
from urllib.parse import urlencode

from flask import Flask, render_template, request, redirect, url_for, flash

from models import db, WeatherRecord
import weather_api as weather_api

from jinja2 import TemplateNotFound

# Helper: build keyword-args that match the actual column names
def _coord_kwargs(latitude, longitude, timezone):
    """Return coord fields keyed to whatever columns your model actually has."""
    from models import WeatherRecord
    cols = set(WeatherRecord.__table__.columns.keys())
    coord_fields = {}
    if 'lat' in cols:
        coord_fields['lat'] = latitude
    elif 'latitude' in cols:
        coord_fields['latitude'] = latitude
    if 'lon' in cols:
        coord_fields['lon'] = longitude
    elif 'longitude' in cols:
        coord_fields['longitude'] = longitude
    if 'timezone' in cols:
        coord_fields['timezone'] = timezone
    return coord_fields

def _date_kwargs(date_value):
    """Return a dict mapping the given date_value to the model's actual date column."""
    from models import WeatherRecord
    cols = set(WeatherRecord.__table__.columns.keys())

    for candidate in (
        'requested_date',  # <-- add this
        'date',
        'record_date',
        'day',
        'observation_date',
        'observed_date',
    ):
        if candidate in cols:
            return {candidate: date_value}

    # Any column that contains 'date'
    for col in cols:
        if 'date' in col:
            return {col: date_value}

    return {}

# App factory — sets configuration, initializes the database, and registers routes.
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
        sort_column = sortable.get(sort, WeatherRecord.requested_date)
        records = WeatherRecord.query.order_by(sort_column.asc() if direction == "asc" else sort_column.desc()).all()

        def sort_link(col_name):
            next_direction = "asc"
            if sort == col_name and direction == "asc":
                next_direction = "desc"
            params = {"sort": col_name, "dir": next_direction}
            return f"?{urlencode(params)}"

        return render_template("index.html", records=records, sort=sort, direction=direction, sort_link=sort_link)

    # Add route — parses form inputs, resolves location if needed, fetches weather for the selected date, and saves a new record.
    @app.route("/add", methods=["POST"])
    def add():
        from datetime import datetime
        from flask import request, redirect, url_for, flash, render_template

        requested_date_str = (request.form.get("requested_date") or "").strip()
        country = (request.form.get("country") or "").strip()
        city = (request.form.get("city") or "").strip()
        region_text = (request.form.get("region") or "").strip()

        # Accept BOTH legacy and new field names coming from the form/tests
        latitude_str  = (request.form.get("latitude")  or request.form.get("lat") or "").strip()
        longitude_str = (request.form.get("longitude") or request.form.get("lon") or "").strip()
        timezone_str  = (request.form.get("timezone") or "").strip()

        try:
            requested_date = datetime.strptime(requested_date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Date must be in YYYY-MM-DD format.", "error")
            return redirect(url_for("index"))

        # If coordinates + timezone already provided, fetch & save directly
        if latitude_str and longitude_str and timezone_str:
            try:
                latitude = float(latitude_str)
                longitude = float(longitude_str)
            except ValueError:
                flash("Latitude/Longitude must be numeric.", "error")
                return redirect(url_for("index"))

            daily = weather_api.fetch_weather_for_date(
                city=city,
                country=country,
                target_date=requested_date,
                latitude=latitude,          
                longitude=longitude,        
                timezone=timezone_str,      
            )

            record_fields = dict(
                city=city,
                country=country,
                temp_max_c=daily.get("temp_max_c"),
                temp_min_c=daily.get("temp_min_c"),
                precip_mm=daily.get("precip_mm"),
                wind_max_kmh=daily.get("wind_max_kmh"),
                source=daily.get("source"),
            )
            record_fields.update(_coord_kwargs(latitude, longitude, timezone_str))
            record_fields.update(_date_kwargs(requested_date))

            record = WeatherRecord(**record_fields)
            db.session.add(record)
            db.session.commit()

            flash("Record added.", "success")
            return redirect(url_for("index"))

        # Otherwise search for a location first
        candidates = weather_api.search_locations(
            city=city, country=country, admin1=(region_text or None)
        )

        # Show a selection page; if template is missing, return simple HTML fallback
        if len(candidates) > 1:
            try:
                return render_template(
                    "select_location.html",
                    candidates=candidates,
                    requested_date=requested_date_str,
                    city=city,
                    country=country,
                )
            except TemplateNotFound:
                options = "".join(
                    f"<li>{c['name']}, {c.get('admin1','')} ({c['country']})</li>"
                    for c in candidates
                )
                html = f"<h1>Choose a location</h1><ul>{options}</ul>"
                return html, 200

        # Single match
        if len(candidates) == 1:
            match = candidates[0]
            latitude = match["latitude"]
            longitude = match["longitude"]
            timezone_str = match["timezone"]
            daily = weather_api.fetch_weather_for_date(
                city=city,
                country=country,
                target_date=requested_date,
                latitude=latitude,          
                longitude=longitude,        
                timezone=timezone_str,      
            )

            record_fields = dict(
                city=city,
                country=country,
                temp_max_c=daily.get("temp_max_c"),
                temp_min_c=daily.get("temp_min_c"),
                precip_mm=daily.get("precip_mm"),
                wind_max_kmh=daily.get("wind_max_kmh"),
                source=daily.get("source"),
            )
            record_fields.update(_coord_kwargs(latitude, longitude, timezone_str))
            record_fields.update(_date_kwargs(requested_date))

            record = WeatherRecord(**record_fields)
            db.session.add(record)
            db.session.commit()

            flash("Record added.", "success")
            return redirect(url_for("index"))

        flash("No matching locations found.", "error")
        return redirect(url_for("index"))


    # Deletes the selected record.
    @app.route("/delete/<int:record_id>", methods=["POST"])
    def delete(record_id):
        record = db.session.get(WeatherRecord, record_id)
        if record is None:
            flash("Record not found.", "error")
            return redirect(request.referrer or url_for("index"))
        db.session.delete(record)
        db.session.commit()
        flash("Record deleted.", "success")
        return redirect(request.referrer or url_for("index"))

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
