"""Batch error and population shift monitoring; review only, never promotion."""
import argparse
import csv
import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

from pipeline import ROOT, metrics, read_series

BINS = [0, 50, 100, 150, 200, 300, 400, 501]


def distribution_shift(reference_counts, observed):
    counts = np.asarray(reference_counts, dtype=float)
    values = np.asarray(observed, dtype=float)
    if counts.shape != (7,) or (counts < 0).any() or not np.isfinite(counts).all() or counts.sum() <= 0:
        raise ValueError("Invalid reference histogram")
    if not len(values) or not np.isfinite(values).all() or (values < 0).any() or (values > 500).any():
        raise ValueError("Invalid observed AQI")
    recent = np.histogram(values, bins=BINS)[0]
    p, q = (counts + .5) / (counts.sum() + 3.5), (recent + .5) / (recent.sum() + 3.5)
    return float(np.sum((q - p) * np.log(q / p)))


def monitor(predictions, actual_series, report, inject_drift=False, mode="backtest"):
    if mode not in ("backtest", "operational"):
        raise ValueError("Unknown evaluation mode")
    with Path(predictions).open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if mode == "operational" and not {"issued_at", "historical_replay"}.issubset(reader.fieldnames or []):
            raise ValueError("Operational CSV requires issued_at and historical_replay")
        rows = list(reader)
    matched, selected, excluded = [], {}, 0
    for row in rows:
        day = date.fromisoformat(row["date"])
        if row["model_version"] != report["run_id"]:
            raise ValueError("Prediction model version differs from report")
        predicted, last = float(row["prediction"]), float(row["last_aqi"])
        if not all(np.isfinite(v) and 0 <= v <= 500 for v in (predicted, last)):
            raise ValueError("Invalid prediction or input AQI")
        issued = None
        if mode == "operational":
            issued = datetime.fromisoformat(row["issued_at"])
            if issued.tzinfo is None:
                raise ValueError("issued_at must include a timezone")
            replay = row["historical_replay"].strip().lower()
            if replay not in ("true", "false"):
                raise ValueError("historical_replay must be true or false")
            if replay == "true" or issued.astimezone(ZoneInfo("Asia/Kolkata")).date() >= day:
                excluded += 1
                continue
        if day in selected:
            prior = selected[day]
            if mode == "backtest" or (issued == prior[0] and (predicted, last) != prior[1:]):
                raise ValueError("Duplicate prediction date with ambiguous evidence")
            if issued >= prior[0]:
                continue  # Explicit policy: earliest eligible issuance per target day.
        selected[day] = (issued, predicted, last)
    for day, (_, predicted, last) in sorted(selected.items()):
        if day in actual_series:
            matched.append((actual_series[day], predicted, 450.0 if inject_drift else last))
    if not matched:
        raise ValueError("No matched predictions and actual observations")
    actual, predicted, latest = np.array(matched).T
    score = metrics(actual, predicted)
    psi = distribution_shift(report["training_histogram"], latest)
    enough = len(matched) >= 30
    flags = []
    if enough and psi > .2:
        flags.append("input_distribution_shift")
    if enough and score["mae"] > max(1.0, report["model_test"]["mae"] * 1.25):
        flags.append("prediction_error_increase")
    return {"model_version": report["run_id"], "matched": len(matched), **score,
            "evaluation_mode": mode, "excluded_replays_or_late": excluded,
            "psi": psi, "flags": flags, "sufficient_samples": enough, "simulated_drift": inject_drift,
            "action": "review_retraining" if flags else "observe" if enough else "collect_more_labels",
            "note": "PSI is a heuristic; seasonal shifts can trigger review without model degradation."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--actuals", type=Path, default=ROOT / "data/delhi.csv")
    parser.add_argument("--inject-drift", action="store_true")
    parser.add_argument("--mode", choices=["backtest", "operational"])
    args = parser.parse_args()
    directory = args.run_dir or ROOT / "artifacts" / json.loads((ROOT / "artifacts/latest.json").read_text())["run_id"]
    result = monitor(args.predictions or directory / "test_predictions.csv", read_series(args.actuals),
                     json.loads((directory / "report.json").read_text()), args.inject_drift,
                     args.mode or ("operational" if args.predictions else "backtest"))
    print(json.dumps(result, indent=2))
