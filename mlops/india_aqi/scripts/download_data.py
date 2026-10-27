"""Reproduce the exact checked-in dataset, with timeout and checksum validation."""
import argparse
import hashlib
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
URL = "https://urbanemissions.info/wp-content/uploads/ncap/aqibulletins/Delhi_AQIBulletins.csv"
EXPECTED = "3bb4435d91457dca820e1189357446849235bcce18e4092267a5c6fc1e9fd61d"
parser = argparse.ArgumentParser()
parser.add_argument("--verify", action="store_true")
args = parser.parse_args()
target = ROOT / "data/delhi.csv"
if args.verify:
    data = target.read_bytes()
else:
    with urlopen(URL, timeout=30) as response:
        data = response.read()
digest = hashlib.sha256(data).hexdigest()
if digest != EXPECTED:
    raise ValueError("Source checksum differs from pinned snapshot; review new data before replacing it")
if not args.verify:
    temporary = target.with_suffix(".download")
    temporary.write_bytes(data)
    temporary.replace(target)
print(f"Dataset verified: {len(data)} bytes; SHA-256 {digest}")
