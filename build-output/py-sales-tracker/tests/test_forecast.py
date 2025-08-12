from app.ai.forecast import ForecastResult

def test_forecast_result_shape():
    fr = ForecastResult(dates=[1,2,3], values=[1.0,2.0,3.0])
    assert len(fr.dates) == len(fr.values) 