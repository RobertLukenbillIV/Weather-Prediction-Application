from datetime import date
from models import db, WeatherRecord

def test_index_loads(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"Weather Database" in r.data

def test_add_ambiguous_shows_selection(app, client, monkeypatch):
    import weather_api as wa
    def fake_search(city, country, admin1=None, count=6):
        return [
            {"name":"Springfield","admin1":"Illinois","country":"United States","latitude":39.78,"longitude":-89.64,"timezone":"America/Chicago"},
            {"name":"Springfield","admin1":"Missouri","country":"United States","latitude":37.20,"longitude":-93.29,"timezone":"America/Chicago"},
        ]
    monkeypatch.setattr(wa, "search_locations", fake_search)

    r = client.post("/add", data={
        "requested_date": date.today().isoformat(),
        "country": "United States",
        "city": "Springfield"
    }, follow_redirects=True)

    assert r.status_code == 200
    assert b"Choose a location" in r.data

def test_add_with_selected_coordinates_creates_record(app, client, monkeypatch):
    import weather_api as wa
    def fake_fetch(city, country, target_date, latitude=None, longitude=None, timezone=None):
        return {"temp_max_c": 20.0, "temp_min_c": 10.0, "precip_mm": 1.0, "wind_max_kmh": 15.0, "source":"forecast"}
    monkeypatch.setattr(wa, "fetch_weather_for_date", fake_fetch)

    r = client.post("/add", data={
        "requested_date": date.today().isoformat(),
        "country": "United States",
        "city": "Chicago",
        "lat": "41.8781",
        "lon": "-87.6298",
        "timezone": "America/Chicago"
    }, follow_redirects=True)

    assert r.status_code == 200
    with app.app_context():
        count = WeatherRecord.query.count()
        assert count == 1
        rec = WeatherRecord.query.first()
        assert rec.city == "Chicago"
        assert rec.temp_max_c == 20.0

def test_delete_record(app, client, monkeypatch):
    import weather_api as wa
    def fake_fetch(city, country, target_date, latitude=None, longitude=None, timezone=None):
        return {"temp_max_c": 21.0, "temp_min_c": 9.0, "precip_mm": 0.0, "wind_max_kmh": 10.0, "source":"forecast"}
    monkeypatch.setattr(wa, "fetch_weather_for_date", fake_fetch)

    r = client.post("/add", data={
        "requested_date": date.today().isoformat(),
        "country": "United States",
        "city": "Austin",
        "lat": "30.2672",
        "lon": "-97.7431",
        "timezone": "America/Chicago"
    }, follow_redirects=True)
    assert r.status_code == 200

    with app.app_context():
        rec = WeatherRecord.query.first()
        assert rec is not None
        rec_id = rec.id

    r = client.post(f"/delete/{rec_id}", follow_redirects=True)
    assert r.status_code == 200
    with app.app_context():
        assert WeatherRecord.query.count() == 0

def test_sorting_by_city(app, client, monkeypatch):
    import weather_api as wa
    def fake_fetch(city, country, target_date, latitude=None, longitude=None, timezone=None):
        return {"temp_max_c": 21.0, "temp_min_c": 9.0, "precip_mm": 0.0, "wind_max_kmh": 10.0, "source":"forecast"}
    monkeypatch.setattr(wa, "fetch_weather_for_date", fake_fetch)

    for c in ["Alpha", "Zulu"]:
        client.post("/add", data={
            "requested_date": date.today().isoformat(),
            "country": "X",
            "city": c,
            "lat": "0.0",
            "lon": "0.0",
            "timezone": "UTC"
        }, follow_redirects=True)

    r = client.get("/?sort=city&dir=asc")
    body = r.data.decode("utf-8")
    assert body.find("Alpha") < body.find("Zulu")
