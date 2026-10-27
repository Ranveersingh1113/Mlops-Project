"""Verified Delhi city AQI from official dated CPCB daily bulletins."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from functools import lru_cache
from hashlib import sha256
from io import BytesIO
import re
import time
from urllib.error import HTTPError
from urllib.request import urlopen
from zoneinfo import ZoneInfo

from pypdf import PdfReader


def parse_bulletin_text(text, expected):
    dates = re.findall(r'Air\s+Quality\s+Index\s+on\s+([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})', text)
    months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    found = {date(int(y), months.index(m[:3].lower()) + 1, int(d)) for m, d, y in dates}
    if found != {expected}:
        raise ValueError('Bulletin date does not match requested date')
    rows = re.findall(r'^\s*\d+\s+Delhi\s+(Good|Satisfactory|Moderate|Poor|Very\s+Poor|Severe)\s+'
                      r'(\d{1,3})\s+([^\n]+?)\s+(\d+)\s*/\s*(\d+)\s*$', text, re.MULTILINE)
    if len(rows) != 1:
        raise ValueError('Expected exactly one Delhi city record')
    category, aqi, _, stations, total = rows[0]
    aqi, stations, total = int(aqi), int(stations), int(total)
    expected_category = ('Good' if aqi <= 50 else 'Satisfactory' if aqi <= 100 else 'Moderate' if aqi <= 200
                         else 'Poor' if aqi <= 300 else 'Very Poor' if aqi <= 400 else 'Severe')
    if not 0 <= aqi <= 500 or not 0 < stations <= total or ' '.join(category.split()) != expected_category:
        raise ValueError('Invalid Delhi AQI, category or station coverage')
    return {'date': str(expected), 'aqi': aqi, 'stations': stations, 'total_stations': total}


@lru_cache(maxsize=64)
def _fetch_bulletin(day, cache_hour):
    url = f'https://cpcb.nic.in/upload/Downloads/AQI_Bulletin_{day:%Y%m%d}.pdf'
    try:
        with urlopen(url, timeout=20) as response:
            content = response.read(2_000_001)
    except HTTPError as exc:
        if exc.code in (404, 410):
            raise FileNotFoundError(f'CPCB bulletin not published for {day}') from exc
        raise
    if len(content) > 2_000_000 or not content.startswith(b'%PDF-'):
        raise ValueError('CPCB returned an invalid or oversized bulletin')
    text = '\n'.join(page.extract_text() or '' for page in PdfReader(BytesIO(content)).pages)
    return {**parse_bulletin_text(text, day), 'source_url': url, 'sha256': sha256(content).hexdigest()}


def fetch_bulletin(day):
    # Refresh within an hour so official corrections are not cached indefinitely.
    return _fetch_bulletin(day, int(time.time() // 3600)).copy()


def latest_history(today=None, fetch=fetch_bulletin):
    today = today or datetime.now(ZoneInfo('Asia/Kolkata')).date()
    latest = today
    try:
        last = fetch(latest)
    except FileNotFoundError:
        latest -= timedelta(days=1)
        last = fetch(latest)
    days = [latest - timedelta(days=i) for i in range(6, 0, -1)]
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = [*pool.map(fetch, days), last]
    return {'history': [{'date': row['date'], 'aqi': row['aqi']} for row in rows],
            'sources': rows, 'input_age_days': (today - latest).days,
            'note': 'Official CPCB bulletin, daily 4 PM city AQI (past 24 hours). Missing days are never interpolated.'}


if __name__ == '__main__':
    import argparse
    import csv
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', type=Path, help='Export recent actuals for the monitoring CLI')
    args = parser.parse_args()
    result = latest_history()
    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open('w', newline='', encoding='utf-8') as stream:
            writer = csv.writer(stream)
            writer.writerow(['date', 'City', 'Index Value'])
            writer.writerows((row['date'], 'Delhi', row['aqi']) for row in result['history'])
    print(json.dumps(result, indent=2))
