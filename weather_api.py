import requests
from datetime import date, datetime

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"

# Mormalizes strings for case-insensitive comparisons.
def _norm(string):
    return (string or "").strip().lower()

# Queries the geocoding API and returns candidate locations, optionally filtered by region.
def search_locations(city: str, country: str, count: int = 6, admin1: str | None = None):
    """
    return up to `count` geocoding candidates for the given city + country.
    Optionally filter by admin1 (state/province/region), case-insensitive substring match.
    Items include name, admin1, country, latitude, longitude, timezone.
    """
    query_string = f"{city}, {country}".strip()
    params = {"name": city, "count": count, "language": "en", "format": "json"}
    try:
        response = requests.get(GEO_URL, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        raise RuntimeError(f"Geocoding request failed: {e}")
    results = data.get("results") or []

    if not results:
        try:
            response = requests.get(GEO_URL, params={"name": query_string, "count": count, "language": "en", "format": "json"}, timeout=20)
            response.raise_for_status()
            data = response.json()
            results = data.get("results") or []
        except Exception as e:
            raise RuntimeError(f"Geocoding (fallback) failed: {e}")

    # Filter by admin1 if provided
    if admin1:
        want = _norm(admin1)
        filtered = []
        for result in results:
            admin1_normalized = _norm(result.get("admin1"))
            if want and (want == admin1_normalized or want in admin1_normalized):
                filtered.append(result)
        if filtered:
            results = filtered

    simplified = []
    for result in results:
        simplified.append({
            "name": result.get("name"),
            "admin1": result.get("admin1"),
            "country": result.get("country"),
            "latitude": result["latitude"],
            "longitude": result["longitude"],
            "timezone": result.get("timezone", "UTC"),
        })
    return simplified

# Selects the appropriate API based on date and returns a normalized daily weather dict.
def fetch_weather_for_date(city: str, country: str, target_date, latitude: float | None = None, longitude: float | None = None, timezone: str | None = None):
    """
    For recent past (≤7 days), use Forecast API with past_days to bridge ERA5 delay.
    Older past uses Archive API. Today/future uses Forecast.
    """
    if isinstance(target_date, str):
        target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
    if not isinstance(target_date, date):
        raise ValueError("target_date must be a datetime.date")

    # Geocode unless latitude/longitude provided
    if latitude is None or longitude is None:
        candidates = search_locations(city, country, count=1)
        if not candidates:
            raise ValueError(f"No geocoding results for '{city}, {country}'.")
        geo = candidates[0]
        latitude = geo.get("latitude")
        longitude = geo.get("longitude")
        timezone = geo.get("timezone", "UTC")
    else:
        latitude, longitude = latitude, longitude
        timezone = timezone or "UTC"

    today = date.today()
    daily_params = ["temperature_2m_max", "temperature_2m_min", "precipitation_sum", "wind_speed_10m_max"]

    if target_date < today:
        days_back = (today - target_date).days
        if days_back <= 7:
            params = {
                "latitude": latitude, "longitude": longitude,
                "daily": ",".join(daily_params),
                "timezone": timezone,
                "past_days": days_back
            }
            response = requests.get(FORECAST_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            source = "forecast"
        else:
            params = {
                "latitude": latitude, "longitude": longitude,
                "start_date": target_date.isoformat(), "end_date": target_date.isoformat(),
                "daily": ",".join(daily_params), "timezone": timezone,
            }
            response = requests.get(HISTORICAL_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            source = "historical"
    else:
        params = {
            "latitude": latitude, "longitude": longitude,
            "daily": ",".join(daily_params), "timezone": timezone,
        }
        response = requests.get(FORECAST_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        source = "forecast"

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    if target_date.isoformat() in dates:
        index = dates.index(target_date.isoformat())
    else:
        if not dates:
            raise ValueError("No daily data returned from weather API.")
        index = 0

    return {
        "temp_max_c": _safe_idx(daily.get("temperature_2m_max"), index),
        "temp_min_c": _safe_idx(daily.get("temperature_2m_min"), index),
        "precip_mm": _safe_idx(daily.get("precipitation_sum"), index),
        "wind_max_kmh": _safe_idx(daily.get("wind_speed_10m_max"), index),
        "source": source,
        "geo": {"latitude": latitude, "longitude": longitude, "timezone": timezone},
    }

# Safely returns list[index] or None if out of range.
def _safe_idx(values, index):
    if values is None:
        return None
    try:
        return values[index]
    except Exception:
        return None
