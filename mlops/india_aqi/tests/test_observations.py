from datetime import date, timedelta

import pytest

from observations import parse_bulletin_text, latest_history


TEXT = '''Air Quality Index on Oct 27, 2026 @ 4 PM
(Average of past 24 hours)
80 Dehradun Satisfactory 70 PM10 1/1
81 Delhi Moderate 197 PM2.5 55/59
82 Dhanbad Moderate 129 PM10 2/2
'''


def test_delhi_bulletin_date_and_city_are_verified():
    row = parse_bulletin_text(TEXT, date(2026, 10, 27))
    assert row == {'date': '2026-10-27', 'aqi': 197, 'stations': 55, 'total_stations': 59}
    with pytest.raises(ValueError, match='date'):
        parse_bulletin_text(TEXT, date(2026, 10, 26))
    for invalid in (TEXT.replace('197', '597'), TEXT + '81 Delhi Moderate 197 PM2.5 55/59\n',
                    TEXT.replace('Delhi', 'New Delhi'), TEXT.replace('55/59', '0/59')):
        with pytest.raises(ValueError):
            parse_bulletin_text(invalid, date(2026, 10, 27))


def test_history_requires_seven_days_and_discloses_publication_lag():
    today = date(2026, 10, 27)
    def fetch(day):
        if day == today:
            raise FileNotFoundError('not published')
        return {'date': str(day), 'aqi': 100, 'source_url': 'https://cpcb.nic.in/test.pdf', 'sha256': 'test'}
    result = latest_history(today=today, fetch=fetch)
    assert len(result['history']) == 7
    assert result['history'][0]['date'] == '2026-10-20'
    assert result['history'][-1]['date'] == '2026-10-26'
    assert result['input_age_days'] == 1
    def missing_middle(day):
        if day == today - timedelta(days=3):
            raise FileNotFoundError('gap')
        return fetch(day)
    with pytest.raises(FileNotFoundError):
        latest_history(today=today, fetch=missing_middle)


def test_latest_route_reports_source_failure(monkeypatch):
    import app as service
    from fastapi.testclient import TestClient
    expected = {'history': [{'date': '2026-10-27', 'aqi': 197}], 'sources': []}
    monkeypatch.setattr(service, 'latest_history', lambda: expected)
    client = TestClient(service.app)
    assert client.get('/observations/latest').json() == expected
    def fail():
        raise ValueError('bulletin changed')
    monkeypatch.setattr(service, 'latest_history', fail)
    response = client.get('/observations/latest')
    assert response.status_code == 503
    assert 'CPCB' in response.json()['detail']
