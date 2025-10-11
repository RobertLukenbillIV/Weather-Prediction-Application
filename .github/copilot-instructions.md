# Weather Prediction Application - AI Agent Instructions

## Architecture Overview
This is a Flask web app that fetches weather data from Open-Meteo API and stores it in SQLite. The app uses the **Application Factory pattern** (`create_app()` in `app.py`) with three core modules:

- **`app.py`**: Routes, form handling, and Flask app creation
- **`models.py`**: SQLAlchemy model (`WeatherRecord`) with flexible column mapping
- **`weather_api.py`**: Open-Meteo API integration with geocoding and smart date-based API selection

## Critical Patterns & Conventions

### Dynamic Column Mapping
The app uses **flexible field mapping** for coordinates and dates via `_coord_kwargs()` and `_date_kwargs()` helper functions. These dynamically detect actual column names in the `WeatherRecord` model, allowing the app to work with different database schemas. Always use these helpers when creating records.

### Weather API Date Logic
`fetch_weather_for_date()` automatically selects the correct Open-Meteo endpoint:
- **Recent past (≤7 days)**: Forecast API with `past_days` parameter (bridges ERA5 archive delay)  
- **Older past**: Archive/Historical API
- **Today/Future**: Forecast API

### Location Disambiguation
When multiple geocoding results exist, the app shows a selection page. The `add` route handles both direct coordinate submission and city/country search with optional region filtering.

## Development Workflows

### Local Development
```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt requirements-dev.txt
flask --app app:create_app run --debug
```

### Testing
All tests use **pytest with coverage** configured in `pyproject.toml`:
```bash
pytest -q  # Runs with coverage, generates htmlcov/ and coverage.xml
```

Test fixtures in `conftest.py` create isolated Flask apps with temporary SQLite databases. Mock `weather_api` functions using `monkeypatch.setattr()`.

### Database Operations
SQLite database auto-created on first run at `sqlite:///weather.db`. The `WeatherRecord` model has indexed fields: `requested_date`, `city`, `country`, `created_at`.

## Integration Points

### Open-Meteo API Dependencies
- **Geocoding**: `https://geocoding-api.open-meteo.com/v1/search`
- **Forecast**: `https://api.open-meteo.com/v1/forecast` 
- **Historical**: `https://archive-api.open-meteo.com/v1/archive`

Always handle API failures gracefully and respect 20-30 second timeouts.

### Template Structure
Uses Jinja2 with `_layout.html` base template. Flash messages categorized as "success"/"error". The app gracefully falls back to simple HTML if templates are missing (see location selection handling).

## Key Files for Understanding
- `app.py` lines 15-45: Column mapping helpers that enable schema flexibility
- `weather_api.py` lines 60-90: Date-based API selection logic
- `tests/conftest.py`: Test isolation pattern with temporary databases
- `pyproject.toml`: Coverage configuration and test discovery