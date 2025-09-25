import types
from datetime import date, timedelta

import weather_api as wa

class FakeResponse:
    def __init__(self, json_data, status_code=200, captured=None):
        self._json = json_data
        self.status_code = status_code
        self.captured = captured or {}

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

def make_requests_get_stub(store):
    def _get(url, params=None, timeout=30, **kwargs):
        params = params or {}
        store.append({"url": url, "params": dict(params)})
        if "geocoding-api" in url:
            data = {
                "results": [
                    {"name":"Springfield","admin1":"Illinois","country":"United States","latitude":39.78,"longitude":-89.64,"timezone":"America/Chicago"},
                    {"name":"Springfield","admin1":"Missouri","country":"United States","latitude":37.20,"longitude":-93.29,"timezone":"America/Chicago"},
                ]
            }
            return FakeResponse(data, captured={"url": url, "params": params})
        elif "forecast" in url:
            past_days = int(params.get("past_days", 0) or 0)
            days = 7 + past_days
            start = date.today() - timedelta(days=past_days)
            times = [(start + timedelta(d)).isoformat() for d in range(days)]
            daily = {
                "time": times,
                "temperature_2m_max": [25.0 for _ in times],
                "temperature_2m_min": [15.0 for _ in times],
                "precipitation_sum": [2.0 for _ in times],
                "wind_speed_10m_max": [30.0 for _ in times],
            }
            return FakeResponse({"daily": daily}, captured={"url": url, "params": params})
        elif "archive-api" in url:
            day = params.get("start_date")
            daily = {
                "time": [day],
                "temperature_2m_max": [10.0],
                "temperature_2m_min": [0.0],
                "precipitation_sum": [5.0],
                "wind_speed_10m_max": [20.0],
            }
            return FakeResponse({"daily": daily}, captured={"url": url, "params": params})
        else:
            return FakeResponse({}, status_code=404)
    return _get

def test_search_locations_filters_by_region(monkeypatch):
    calls = []
    monkeypatch.setattr(wa, "requests", types.SimpleNamespace(get=make_requests_get_stub(calls)))
    results = wa.search_locations("Springfield", "United States", admin1="Illinois")
    assert any(r["admin1"] == "Illinois" for r in results)
    assert all("Springfield" in r["name"] for r in results)

def test_fetch_future_uses_forecast(monkeypatch):
    calls = []
    monkeypatch.setattr(wa, "requests", types.SimpleNamespace(get=make_requests_get_stub(calls)))
    future = date.today() + timedelta(days=2)
    out = wa.fetch_weather_for_date("X", "Y", future, latitude=1.0, longitude=2.0, timezone="UTC")
    assert any("forecast" in c["url"] for c in calls)
    assert out["source"] == "forecast"
    assert out["temp_max_c"] == 25.0

def test_fetch_recent_past_uses_forecast_with_past_days(monkeypatch):
    calls = []
    monkeypatch.setattr(wa, "requests", types.SimpleNamespace(get=make_requests_get_stub(calls)))
    recent = date.today() - timedelta(days=2)
    out = wa.fetch_weather_for_date("X", "Y", recent, latitude=1.0, longitude=2.0, timezone="UTC")
    matched = [c for c in calls if "forecast" in c["url"]]
    assert matched, "expected a forecast call"
    assert int(matched[-1]["params"].get("past_days", 0)) >= 2
    assert out["source"] == "forecast"

def test_fetch_old_past_uses_archive(monkeypatch):
    calls = []
    monkeypatch.setattr(wa, "requests", types.SimpleNamespace(get=make_requests_get_stub(calls)))
    old = date(2000, 1, 1)
    out = wa.fetch_weather_for_date("X", "Y", old, latitude=1.0, longitude=2.0, timezone="UTC")
    assert any("archive-api" in c["url"] for c in calls)
    assert out["source"] == "historical"
    assert out["precip_mm"] == 5.0
