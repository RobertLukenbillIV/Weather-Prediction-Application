import requests
from datetime import date, datetime

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"

def _norm(s):
    return (s or "").strip().lower()

def search_locations(city: str, country: str, count: int = 6, admin1: str | None = None):
    """
    Return up to `count` geocoding candidates for the given city + country.
    Optionally filter by admin1 (state/province/region), case-insensitive substring match.
    Items include name, admin1, country, latitude, longitude, timezone.
    """
    q = f"{city}, {country}".strip()
    params = {"name": city, "count": count, "language": "en", "format": "json"}
    try:
        resp = requests.get(GEO_URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        raise RuntimeError(f"Geocoding request failed: {e}")
    results = data.get("results") or []

    if not results:
        try:
            resp = requests.get(GEO_URL, params={"name": q, "count": count, "language": "en", "format": "json"}, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results") or []
        except Exception as e:
            raise RuntimeError(f"Geocoding (fallback) failed: {e}")

    # Filter by admin1 if provided
    if admin1:
        want = _norm(admin1)
        filtered = []
        for r in results:
            a1 = _norm(r.get("admin1"))
            if want and (want == a1 or want in a1):
                filtered.append(r)
        if filtered:
            results = filtered

    simplified = []
    for r in results:
        simplified.append({
            "name": r.get("name"),
            "admin1": r.get("admin1"),
            "country": r.get("country"),
            "latitude": r["latitude"],
            "longitude": r["longitude"],
            "timezone": r.get("timezone", "UTC"),
        })
    return simplified

def fetch_weather_for_date(city: str, country: str, target_date, *, latitude: float=None, longitude: float=None, timezone: str=None):
    """
    For recent past (≤7 days), use Forecast API with past_days to bridge ERA5 delay.
    Older past uses Archive API. Today/future uses Forecast.
    """
    if isinstance(target_date, str):
        target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
    if not isinstance(target_date, date):
        raise ValueError("target_date must be a datetime.date")

    # Geocode unless lat/lon provided
    if latitude is None or longitude is None:
        candidates = search_locations(city, country, count=1)
        if not candidates:
            raise ValueError(f"No geocoding results for '{city}, {country}'.")
        geo = candidates[0]
        lat = geo.get("latitude")
        lon = geo.get("longitude")
        tz = geo.get("timezone", "UTC")
    else:
        lat, lon = latitude, longitude
        tz = timezone or "UTC"

    today = date.today()
    daily_params = ["temperature_2m_max", "temperature_2m_min", "precipitation_sum", "wind_speed_10m_max"]

    if target_date < today:
        days_back = (today - target_date).days
        if days_back <= 7:
            params = {
                "latitude": lat, "longitude": lon,
                "daily": ",".join(daily_params),
                "timezone": tz,
                "past_days": days_back
            }
            resp = requests.get(FORECAST_URL, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            source = "forecast"
        else:
            params = {
                "latitude": lat, "longitude": lon,
                "start_date": target_date.isoformat(), "end_date": target_date.isoformat(),
                "daily": ",".join(daily_params), "timezone": tz,
            }
            resp = requests.get(HISTORICAL_URL, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            source = "historical"
    else:
        params = {
            "latitude": lat, "longitude": lon,
            "daily": ",".join(daily_params), "timezone": tz,
        }
        resp = requests.get(FORECAST_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        source = "forecast"

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    if target_date.isoformat() in dates:
        idx = dates.index(target_date.isoformat())
    else:
        if not dates:
            raise ValueError("No daily data returned from weather API.")
        idx = 0

    return {
        "temp_max_c": _safe_idx(daily.get("temperature_2m_max"), idx),
        "temp_min_c": _safe_idx(daily.get("temperature_2m_min"), idx),
        "precip_mm": _safe_idx(daily.get("precipitation_sum"), idx),
        "wind_max_kmh": _safe_idx(daily.get("wind_speed_10m_max"), idx),
        "source": source,
        "geo": {"lat": lat, "lon": lon, "timezone": tz},
    }

def _safe_idx(lst, idx):
    if lst is None:
        return None
    try:
        return lst[idx]
    except Exception:
        return None
