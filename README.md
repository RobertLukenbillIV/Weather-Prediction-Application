# Weather Database (Flask + SQLite + Open-Meteo)

A tiny full-stack Python project: enter a **date, country, city** (optionally **state/province**), fetch weather (historical / forecast) via **Open-Meteo**, and store in local **SQLite**. Web UI shows sortable rows, add/delete, and disambiguation for duplicate city names.

## Quickstart
```bash
python -m venv .venv
# Linux/Mac:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000/

## Disambiguation with State/Province
Fill the optional **State/Province** field to narrow geocoding results. If multiple results remain, you’ll choose from a table.

## Testing
- Install dev deps: `pip install -r requirements-dev.txt`
- Run tests: `pytest -q`


### Coverage reports
Pytest is configured to generate coverage:
- terminal summary (missing lines)
- HTML at **htmlcov/index.html**
- XML at **coverage.xml**

## CI (GitHub Actions)
A workflow at `.github/workflows/ci.yml` runs tests with coverage on pushes/PRs to `main` and uploads HTML/XML coverage artifacts.