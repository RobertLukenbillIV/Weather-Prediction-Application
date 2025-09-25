from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class WeatherRecord(db.Model):
    __tablename__ = "weather_records"

    id = db.Column(db.Integer, primary_key=True)
    requested_date = db.Column(db.Date, nullable=False, index=True)
    city = db.Column(db.String(120), nullable=False, index=True)
    country = db.Column(db.String(120), nullable=False, index=True)

    temp_max_c = db.Column(db.Float, nullable=True)
    temp_min_c = db.Column(db.Float, nullable=True)
    precip_mm = db.Column(db.Float, nullable=True)
    wind_max_kmh = db.Column(db.Float, nullable=True)

    source = db.Column(db.String(32), nullable=False)  # "historical" or "forecast"

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<WeatherRecord {self.id} {self.city}, {self.country} {self.requested_date}>"
