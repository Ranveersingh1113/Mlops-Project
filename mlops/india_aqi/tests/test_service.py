from datetime import date, timedelta
import json

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import ForecastInput, app, predict
from monitor import distribution_shift, monitor


def payload():
    return {"history": [{"date": str(date(2023, 12, 25) + timedelta(days=i)), "aqi": 100 + i}
                        for i in range(7)]}


class Model:
    def predict(self, x):
        return np.array([x[0][0]])


def test_next_calendar_day_and_replay():
    result = predict(ForecastInput(**payload()), Model(), {"run_id": "test"}, today=date(2026, 10, 6))
    assert result["target_date"] == "2024-01-01"
    assert result["aqi"] == 106
    assert result["historical_replay"] is True
    assert result["model_version"] == "test"
    assert "issued_at" in result


def test_api_rejects_gaps_nonfinite_future_and_wrong_lengths():
    client = TestClient(app)
    for history in (payload()["history"][:6], payload()["history"] * 2):
        assert client.post("/predict", json={"history": history}).status_code == 422
    data = payload()
    data["history"][2]["date"] = "2023-12-29"
    assert client.post("/predict", json=data).status_code == 422
    data = payload()
    data["history"][0]["aqi"] = 501
    assert client.post("/predict", json=data).status_code == 422
    future = {"history": [{"date": str(date(2099, 1, 1) + timedelta(days=i)), "aqi": 100}
                           for i in range(7)]}
    assert client.post("/predict", json=future).status_code == 422


def test_untrained_service_returns_explicit_failure():
    client = TestClient(app)
    app.state.model = None
    assert client.get("/health").status_code == 503
    assert client.post("/predict", json=payload()).status_code == 503


def test_nonfinite_json_input_returns_validation_error_not_server_error():
    client = TestClient(app, raise_server_exceptions=False)
    for value in (float("nan"), float("inf")):
        data = payload()
        data["history"][0]["aqi"] = value
        response = client.post("/predict", content=json.dumps(data), headers={"Content-Type": "application/json"})
        assert response.status_code == 422


def test_monitor_detects_shift_and_rejects_empty_join(tmp_path):
    reference = [30, 30, 30, 30, 30, 30, 30]
    assert distribution_shift(reference, [10, 60, 120, 170, 250, 350, 450] * 4) < .01
    assert distribution_shift(reference, [450] * 30) > .2
    predictions = tmp_path / "predictions.csv"
    predictions.write_text("date,prediction,last_aqi,model_version\n2099-01-01,100,100,test\n")
    with pytest.raises(ValueError, match="No matched"):
        monitor(predictions, {date(2023, 1, 1): 10}, {"run_id": "test", "training_histogram": reference, "model_test": {"mae": 10}})


def test_operational_monitor_excludes_late_replays_and_selects_first_forecast(tmp_path):
    predictions = tmp_path / "predictions.csv"
    predictions.write_text("date,prediction,last_aqi,model_version,issued_at,historical_replay\n"
                           "2023-01-02,100,100,test,2023-01-01T10:00:00+00:00,false\n"
                           "2023-01-02,200,100,test,2023-01-01T11:00:00+00:00,false\n"
                           "2023-01-03,450,100,test,2023-01-04T10:00:00+00:00,false\n"
                           "2023-01-04,450,100,test,2023-01-03T10:00:00+00:00,true\n")
    actual = {date(2023, 1, day): 100 for day in (2, 3, 4)}
    report = {"run_id": "test", "training_histogram": [10] * 7, "model_test": {"mae": 10}}
    result = monitor(predictions, actual, report, mode="operational")
    assert result["matched"] == 1
    assert result["mae"] == 0
    assert result["excluded_replays_or_late"] == 2
    assert result["evaluation_mode"] == "operational"


def test_operational_monitor_requires_issuance_metadata(tmp_path):
    predictions = tmp_path / "p.csv"
    predictions.write_text("date,prediction,last_aqi,model_version\n2023-01-01,100,100,test\n")
    with pytest.raises(ValueError, match="issued_at"):
        monitor(predictions, {date(2023, 1, 1): 100}, {"run_id": "test"}, mode="operational")
