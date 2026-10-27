from datetime import date, timedelta

import numpy as np
import pytest

from pipeline import examples, features, read_series, split


def test_features_only_use_history_and_forecast_calendar():
    history = [10, 20, 30, 40, 50, 60, 70]
    x = features(history, date(2023, 1, 8))
    assert list(x[:7]) == [70, 60, 50, 40, 30, 20, 10]
    assert x[7] == 40
    assert len(x) == 11
    for bad in ([1] * 6, [float("nan")] * 7, [501] * 7):
        with pytest.raises(ValueError):
            features(bad, date(2023, 1, 8))


def test_missing_days_break_windows_and_target_is_next_day():
    start = date(2023, 1, 1)
    series = {start + timedelta(days=i): float(i) for i in range(18) if i != 8}
    x, y, dates = examples(series)
    assert dates == [start + timedelta(days=i) for i in [7, 16, 17]]
    assert y.tolist() == [7, 16, 17]
    assert x[0, 0] == 6


def test_chronological_split():
    parts = split(np.arange(100))
    assert [len(p) for p in parts] == [60, 20, 20]
    assert max(parts[0]) < min(parts[1]) < min(parts[2])


def test_duplicate_or_invalid_records_fail(tmp_path):
    source = tmp_path / "aqi.csv"
    source.write_text("date,City,Index Value\n2020-01-01,Delhi,20\n2020-01-01,Delhi,30\n")
    with pytest.raises(ValueError, match="Duplicate"):
        read_series(source)
    source.write_text("date,City,Index Value\n2020-01-01,Delhi,NaN\n")
    with pytest.raises(ValueError, match="Invalid"):
        read_series(source)
