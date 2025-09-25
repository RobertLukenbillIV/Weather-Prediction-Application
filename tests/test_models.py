from models import WeatherRecord

def test_model_repr():
    r = WeatherRecord(id=1, city="Testville", country="Nowhere", requested_date=None, source="forecast")
    assert "Testville" in repr(r)
