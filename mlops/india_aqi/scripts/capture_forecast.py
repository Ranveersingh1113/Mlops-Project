"""Capture a real issued forecast; pending labels are never scored as accuracy."""
import argparse
import csv
from datetime import date, datetime, timedelta
import json
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


def call(base, path, data=None):
    request = Request(base.rstrip('/') + path, data=json.dumps(data).encode() if data else None,
                      headers={'Content-Type': 'application/json'})
    with urlopen(request, timeout=90) as response:
        return json.load(response)


def capture(base, directory):
    report = call(base, '/model')
    observations = call(base, '/observations/latest')
    forecast = call(base, '/predict', {'history': observations['history']})
    issued = datetime.fromisoformat(forecast['issued_at'])
    if forecast['historical_replay'] or issued.tzinfo is None or issued.astimezone(ZoneInfo('Asia/Kolkata')).date() >= date.fromisoformat(forecast['target_date']):
        raise ValueError('Cannot use historical replay or late issuance as operational evidence')
    if forecast['model_version'] != report['run_id']:
        raise ValueError('Model changed while capturing; retry with a consistent deployed run')
    assert date.fromisoformat(forecast['target_date']) == date.fromisoformat(observations['history'][-1]['date']) + timedelta(days=1)
    status = {'state': 'awaiting_actuals', 'target_date': forecast['target_date'],
              'model_version': forecast['model_version'], 'issued_at': forecast['issued_at'],
              'operational_mae': None, 'sufficient_samples': False, 'action': 'collect_more_labels'}
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    for name, content in [('report', report), ('observations', observations), ('forecast', forecast), ('status', status)]:
        (directory / f'{name}.json').write_text(json.dumps(content, indent=2) + '\n', encoding='utf-8')
    with (directory / 'predictions.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(['date', 'prediction', 'last_aqi', 'model_version', 'issued_at', 'historical_replay'])
        writer.writerow([forecast['target_date'], forecast['aqi'], forecast['last_aqi'], forecast['model_version'], forecast['issued_at'], False])
    return status


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('url', help='Service URL; use an authenticated Cloud Run proxy for a private service')
    parser.add_argument('--output-dir', type=Path, default=Path('artifacts/operational') / datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    args = parser.parse_args()
    print(json.dumps({'directory': str(args.output_dir), **capture(args.url, args.output_dir)}, indent=2))
