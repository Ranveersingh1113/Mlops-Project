"""One alternative, selected on validation; a newer holdout stays separate."""
import hashlib
import json
from pathlib import Path

from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from threadpoolctl import threadpool_limits

from pipeline import ROOT, examples, metrics, read_series, split


def compare(source, holdout):
    source, holdout = Path(source), Path(holdout)
    series, newer = read_series(source), read_series(holdout)
    if min(newer) <= max(series):
        raise ValueError('New holdout must be strictly after the original source')
    x, y, days = examples(series)
    xt, xv, _ = split(x)
    yt, yv, _ = split(y)
    models = {
        'RandomForestRegressor': RandomForestRegressor(n_estimators=120, max_depth=8,
                                                       min_samples_leaf=3, random_state=42, n_jobs=2),
        'HistGradientBoostingRegressor': HistGradientBoostingRegressor(max_iter=120, max_leaf_nodes=15,
            learning_rate=.05, l2_regularization=1, random_state=42, early_stopping=False),
    }
    with threadpool_limits(limits=2):
        validation = {}
        for name, model in models.items():
            model.fit(xt, yt)
            validation[name] = metrics(yv, model.predict(xv))
        selected = min(validation, key=lambda name: validation[name]['mae'])
        # No new holdout labels enter fitting, tuning or the selection above.
        xe, ye, de = examples(newer)
        score = metrics(ye, models[selected].predict(xe))
    baseline = metrics(ye, xe[:, 0])
    return {
        'selected_by_validation': selected, 'validation': validation,
        'training_end': str(split(days)[0][-1]), 'validation_end': str(split(days)[1][-1]),
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'holdout_sha256': hashlib.sha256(holdout.read_bytes()).hexdigest(),
        'new_holdout': {'n': len(ye), 'start': str(de[0]), 'end': str(de[-1]),
                        'model': score, 'persistence': baseline,
                        'beats_persistence': score['mae'] < baseline['mae']},
        'deployment_action': 'Retain deployed forest; comparison does not promote a model.',
        'note': 'Backtest, not production monitoring. Repeated tuning against the new holdout invalidates its independence.',
    }


if __name__ == '__main__':
    import mlflow
    result = compare(ROOT / 'data/delhi.csv', ROOT / 'data/delhi-holdout-2025.csv')
    out = ROOT / 'artifacts/model-comparison.json'
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    mlflow.set_tracking_uri(f"sqlite:///{(ROOT / 'mlflow.db').as_posix()}")
    mlflow.set_experiment('delhi-model-comparison')
    with mlflow.start_run(run_name='forest-vs-boosting'):
        mlflow.log_params({'selected': result['selected_by_validation'], 'holdout_sha256': result['holdout_sha256']})
        mlflow.log_metrics({'new_holdout_mae': result['new_holdout']['model']['mae'],
                            'new_baseline_mae': result['new_holdout']['persistence']['mae']})
        mlflow.log_artifact(str(out))
    print(json.dumps(result, indent=2))
