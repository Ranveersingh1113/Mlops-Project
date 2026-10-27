import csv
from datetime import datetime, timedelta, timezone
import json
from zoneinfo import ZoneInfo

import pytest

import scripts.capture_forecast as capture


def test_capture_records_pending_forecast_without_inventing_error(tmp_path, monkeypatch):
    issued = datetime(2026, 10, 27, 20, tzinfo=timezone.utc)
    today = issued.astimezone(ZoneInfo('Asia/Kolkata')).date()
    forecast = {'target_date': str(today + timedelta(days=1)), 'aqi': 120, 'last_aqi': 110,
                'model_version': 'a' * 32, 'issued_at': issued.isoformat(),
                'historical_replay': False}
    def call(base, path, data=None):
        if path == '/model':
            return {'run_id': 'a' * 32}
        if path == '/observations/latest':
            return {'history': [{'date': str(today - timedelta(days=i)), 'aqi': 110} for i in range(6, -1, -1)], 'sources': []}
        return forecast
    monkeypatch.setattr(capture, 'call', call)
    result = capture.capture('http://test', tmp_path / 'capture')
    assert result['state'] == 'awaiting_actuals'
    assert result['operational_mae'] is None
    rows = list(csv.DictReader((tmp_path / 'capture/predictions.csv').open()))
    assert rows[0]['issued_at'] == forecast['issued_at']
    assert json.loads((tmp_path / 'capture/status.json').read_text()) == result
    forecast['historical_replay'] = True
    with pytest.raises(ValueError, match='historical'):
        capture.capture('http://test', tmp_path / 'replay')
