"""Exercise the real service, not a model test seam."""
import argparse
import json
from urllib.request import Request, urlopen

parser = argparse.ArgumentParser()
parser.add_argument("url")
args = parser.parse_args()
base = args.url.rstrip("/")


def call(path, data=None):
    payload = json.dumps(data).encode() if data is not None else None
    request = Request(base + path, data=payload, headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=20) as response:
        return json.load(response)


health = call("/health")
assert health["status"] == "ok"
report = call("/model")
forecast = call("/predict", {"history": report["latest_history"]})
assert forecast["model_version"] == report["run_id"]
assert forecast["target_date"] == report["latest_target"]
assert 0 <= forecast["aqi"] <= 500
assert forecast["historical_replay"]
assert forecast["issued_at"]
with urlopen(base + "/", timeout=20) as response:
    assert b"Delhi AQI Forecasting" in response.read()
print(json.dumps({"status": "smoke_passed", **forecast}, indent=2))
