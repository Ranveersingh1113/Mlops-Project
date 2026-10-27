"""Past-only next-day AQI training, chronological evaluation, and MLflow tracking."""
import argparse
import csv
import hashlib
import json
import math
import subprocess
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import joblib
import numpy as np

ROOT = Path(__file__).resolve().parent
SOURCE_SHA256 = "3bb4435d91457dca820e1189357446849235bcce18e4092267a5c6fc1e9fd61d"
FEATURES = [f"lag_{i}" for i in range(1, 8)] + ["mean_7", "std_7", "month", "weekday"]


def read_series(path):
    series, seen = {}, set()
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not {"date", "City", "Index Value"}.issubset(reader.fieldnames or []):
            raise ValueError("CSV must include date, City and Index Value")
        for row in reader:
            if row["City"].strip() != "Delhi":
                continue
            day = date.fromisoformat(row["date"])
            if day in seen:
                raise ValueError(f"Duplicate Delhi date: {day}")
            seen.add(day)
            if not row["Index Value"].strip():
                continue  # Explicit missing measurement; breaks consecutive windows.
            value = float(row["Index Value"])
            if not math.isfinite(value) or not 0 <= value <= 500:
                raise ValueError(f"Invalid AQI on {day}")
            series[day] = value
    if not series:
        raise ValueError("No valid Delhi measurements")
    return series


def features(history, target_date):
    a = np.asarray(history, dtype=float)
    if a.shape != (7,) or not np.isfinite(a).all() or (a < 0).any() or (a > 500).any():
        raise ValueError("Exactly seven finite AQI values in [0,500] required")
    return np.array([*a[::-1], a.mean(), a.std(), target_date.month, target_date.weekday()])


def examples(series):
    x, y, days = [], [], []
    for target in sorted(series):
        preceding = [target - timedelta(days=i) for i in range(7, 0, -1)]
        if all(day in series for day in preceding):
            x.append(features([series[day] for day in preceding], target))
            y.append(series[target])
            days.append(target)
    if not days:
        raise ValueError("No complete eight-day windows")
    return np.array(x), np.array(y), days


def split(values):
    n = len(values)
    if n < 30:
        raise ValueError("At least 30 complete windows required")
    return values[:int(n * .6)], values[int(n * .6):int(n * .8)], values[int(n * .8):]


def metrics(actual, predicted):
    error = np.asarray(actual) - np.asarray(predicted)
    return {"mae": float(np.abs(error).mean()), "rmse": float(np.sqrt((error ** 2).mean()))}


def season(day):
    return ("winter" if day.month in (12, 1, 2) else "summer" if day.month in (3, 4, 5)
            else "monsoon" if day.month in (6, 7, 8, 9) else "post_monsoon")


def train(source=None):
    import mlflow
    from sklearn.ensemble import RandomForestRegressor

    source = Path(source or ROOT / "data/delhi.csv")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    series = read_series(source)
    x, y, days = examples(series)
    xt, xv, xe = split(x)
    yt, yv, ye = split(y)
    dt, dv, de = split(days)
    mlflow.set_tracking_uri(f"sqlite:///{(ROOT / 'mlflow.db').as_posix()}")
    mlflow.set_experiment("delhi-next-day-aqi")
    with mlflow.start_run(run_name="chronological-forest") as run:
        candidates = []
        for depth in (8, 16):
            model = RandomForestRegressor(n_estimators=120, max_depth=depth, min_samples_leaf=3,
                                          random_state=42, n_jobs=-1)
            model.fit(xt, yt)
            validation = metrics(yv, model.predict(xv))
            with mlflow.start_run(run_name=f"depth-{depth}", nested=True):
                mlflow.log_params({"max_depth": depth, "trees": 120, "seed": 42})
                mlflow.log_metrics({f"validation_{k}": v for k, v in validation.items()})
            candidates.append((validation["mae"], depth, model))
        validation_mae, depth, model = min(candidates, key=lambda item: item[0])
        prediction = model.predict(xe)
        baseline = xe[:, 0]
        model_score, baseline_score = metrics(ye, prediction), metrics(ye, baseline)
        grouped = {}
        for group in sorted({season(d) for d in de}):
            mask = np.array([season(d) == group for d in de])
            grouped[group] = {"n": int(mask.sum()), **metrics(ye[mask], prediction[mask])}
        extreme = ye >= 301
        report = {
            "run_id": run.info.run_id, "created_at": datetime.now(timezone.utc).isoformat(),
            "data_sha256": digest, "source_matches_pinned": digest == SOURCE_SHA256,
            "pipeline_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "model": "RandomForestRegressor", "features": FEATURES, "max_depth": depth,
            "validation_mae": validation_mae, "model_test": model_score,
            "baseline_test": baseline_score, "gate_passed": model_score["mae"] < baseline_score["mae"],
            "seasonal_test": grouped,
            "extreme_test": {"n": int(extreme.sum()), **metrics(ye[extreme], prediction[extreme])} if extreme.any() else {"n": 0},
            "splits": {name: {"n": len(part), "start": str(part[0]), "end": str(part[-1])}
                       for name, part in [("train", dt), ("validation", dv), ("test", de)]},
            "raw_records": len(series), "complete_windows": len(days),
            "latest_history": [{"date": str(day), "aqi": series[day]} for day in sorted(series)[-7:]],
            "latest_target": str(max(series) + timedelta(days=1)),
            "training_histogram": np.histogram(xt[:, 0], bins=[0, 50, 100, 150, 200, 300, 400, 501])[0].tolist(),
        }
        git = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
        if git.returncode:
            report["git_sha"] = "unavailable"
            report["git_warning"] = git.stderr.strip()
        else:
            report["git_sha"] = git.stdout.strip()
        status = subprocess.run(["git", "status", "--porcelain", "--", "."], cwd=ROOT, capture_output=True, text=True)
        report["git_dirty"] = bool(status.stdout.strip()) if status.returncode == 0 else None
        if status.returncode:
            report["git_status_warning"] = status.stderr.strip()
        out = ROOT / "artifacts" / run.info.run_id
        out.mkdir(parents=True)
        joblib.dump(model, out / "model.joblib")
        (out / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        with (out / "test_predictions.csv").open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["date", "actual", "prediction", "baseline", "last_aqi", "model_version"])
            writer.writerows((str(d), float(a), float(p), float(b), float(b), run.info.run_id)
                             for d, a, p, b in zip(de, ye, prediction, baseline))
        mlflow.log_params({"data_sha256": digest, "git_sha": report["git_sha"], "max_depth": depth,
                           "train_n": len(xt), "validation_n": len(xv), "test_n": len(xe)})
        mlflow.log_metrics({f"test_{k}": v for k, v in model_score.items()})
        mlflow.log_metrics({f"baseline_{k}": v for k, v in baseline_score.items()})
        mlflow.log_artifacts(str(out), artifact_path="run")
        pointer = ROOT / "artifacts/latest.json"
        pointer.write_text(json.dumps({"run_id": run.info.run_id}) + "\n", encoding="utf-8")
    print(json.dumps({"run_id": report["run_id"], "model_test": model_score,
                      "baseline_test": baseline_score, "gate_passed": report["gate_passed"]}, indent=2))
    return out, report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["train"])
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    train(args.source)
