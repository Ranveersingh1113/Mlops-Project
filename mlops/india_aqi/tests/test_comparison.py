from datetime import date, timedelta

import pytest

from compare_models import compare


def write_series(path, start, offset=0):
    rows = ['date,City,Index Value']
    rows += [f'{start + timedelta(days=i)},Delhi,{100 + (i % 7) * 10 + offset}' for i in range(80)]
    path.write_text('\n'.join(rows))


def test_new_holdout_cannot_overlap_training_source(tmp_path):
    source, holdout = tmp_path / 'source.csv', tmp_path / 'holdout.csv'
    write_series(source, date(2023, 1, 1))
    write_series(holdout, date(2023, 2, 1))
    with pytest.raises(ValueError, match='after'):
        compare(source, holdout)


def test_model_selection_does_not_depend_on_new_holdout_labels(tmp_path):
    source, holdout = tmp_path / 'source.csv', tmp_path / 'holdout.csv'
    write_series(source, date(2023, 1, 1))
    write_series(holdout, date(2025, 1, 1))
    first = compare(source, holdout)
    write_series(holdout, date(2025, 1, 1), offset=200)
    changed = compare(source, holdout)
    assert first['selected_by_validation'] == changed['selected_by_validation']
    for name in first['validation']:
        assert first['validation'][name] == pytest.approx(changed['validation'][name], abs=1e-12)
    assert first['new_holdout']['model']['mae'] != changed['new_holdout']['model']['mae']
