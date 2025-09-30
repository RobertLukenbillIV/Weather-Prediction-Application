from models import WeatherRecord

# Section: test_model_repr — ensures model __repr__ returns a meaningful string without errors.
def test_model_repr():
    r = WeatherRecord(id=1, city="Testville", country="Nowhere", requested_date=None, source="forecast")
    assert "Testville" in repr(r)
