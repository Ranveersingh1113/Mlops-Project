# Delhi AQI Forecasting

Predict next-day Delhi city-average AQI from the preceding seven days. A small, reproducible coursework project demonstrating training, tracking, monitoring, container serving and controlled cloud deployment.

## Poster first

- [Print A3 vector PDF](poster/delhi-aqi-poster.pdf)
- [Editable SVG](poster/delhi-aqi-poster.svg)
- [Preview PNG](poster/delhi-aqi-poster.png)
- [Poster source](poster/create_poster.py), created with Python/ReportLab; no AI-generated imagery.

## Run locally

From this folder:

```powershell
uv sync --frozen
uv run python scripts/download_data.py --verify
uv run pytest -q
uv run python pipeline.py train
uv run uvicorn app:app --host 127.0.0.1 --port 8015
```

Open http://127.0.0.1:8015. Prefilled example uses historical observations ending 2023-12-31 and predicts 2024-01-01. It is clearly labeled replay. For a current forecast, manually supply seven consecutive recent daily city AQI values. There is no live-data integration.

In a second terminal:

```powershell
uv run python scripts/smoke.py http://127.0.0.1:8015
uv run python monitor.py
uv run python monitor.py --inject-drift
uv run mlflow ui --backend-store-uri sqlite:///mlflow.db --host 127.0.0.1 --port 5001
```

MLflow contains a parent run, two validation tuning runs, metrics and artifacts. `artifacts/<run-id>/` holds a model, report and dated test predictions. `latest.json` is a local candidate pointer, not approval to deploy. A model failing the baseline gate cannot serve requests. Model artifacts use Python serialization: load only trusted artifacts you built.

## Real data and model

Public [UrbanEmissions/CPCB bulletin compilation](https://urbanemissions.info/india-air-quality/india-ncap-aqi-indian-cities-2015-2023/): 3,143 Delhi observations, 2015-05-01 through 2023-12-31. Download already works; exact source is committed as `data/delhi.csv`. [Provenance and reuse note](data/SOURCE.md). No signup or API key. Re-download the pinned snapshot with `uv run python scripts/download_data.py`; mismatched checksums fail before replacing data.

Features: seven lags (latest first), seven-day mean/std, target month and weekday. Windows require eight consecutive calendar days including the target. Missing dates are skipped, never filled from future observations. Chronological train/validation/test split is 60/20/20; forest depth 8 or 16 is chosen on validation. Final test is used once for reporting and release gate; repeated decisions against the same test invalidate its holdout role. New production retraining needs a fresh evaluation period.

Recorded first run: candidate MAE **31.09**, RMSE **41.29**; persistence MAE **31.61**, RMSE **43.48**, on 607 test days. Improvement is small (~1.6% MAE), not a claim of production-grade forecasting. See [model card](docs/model-card.md) and generated `report.json` for seasonal/extreme-event results. Always rerun training to obtain current evidence.

## Monitoring

`monitor.py` joins prediction dates to actual AQI, reports MAE/RMSE, and compares latest input AQI histograms with training using PSI. PSI > 0.2 or MAE > 1.25 times test MAE flags review; 30 matched samples required before alerting. These are documented heuristics, not statistical guarantees. Drift can be seasonal without error degradation.

For new observations, provide `--actuals <CPCB-format-csv> --predictions <csv> --run-dir <run-folder>`. Operational CSV columns: `date,prediction,last_aqi,model_version,issued_at,historical_replay`; model version must match the report. `issued_at` must include a timezone. Replays and forecasts issued on/after the target day in India time are excluded; earliest eligible forecast per date is used. API emits all these fields (`target_date` maps to `date`, `aqi` to `prediction`). External prediction files default to operational evaluation; built-in test predictions explicitly use backtest mode. Monitoring is a batch command, not a continuously running alert service. `--inject-drift` substitutes high input values solely to demonstrate monitoring and labels the report simulated.

## Docker

After training, in PowerShell:

```powershell
$aqiRun = (Get-Content artifacts/latest.json | ConvertFrom-Json).run_id
docker build --build-arg "MODEL_RUN=$aqiRun" -t delhi-aqi:local .
docker run --rm --name delhi-aqi-demo -p 8087:8080 delhi-aqi:local
```

Then `uv run python scripts/smoke.py http://127.0.0.1:8087`. Model is baked into image; serving dependencies are pinned separately from full MLflow/training dependencies. Non-root process; readiness checks real model availability. To reproduce dependency resolution: `uv pip compile --python-platform linux --python-version 3.12 requirements-serve.in -o requirements-serve.txt`.

## CI/CD and cloud

[Workflow](../../.github/workflows/india-aqi.yml) runs tests, data verification, training, drift demo, Docker build and actual container smoke test. It uploads the candidate run. Only a manual dispatch with `deploy=true` from the default branch enters the protected `aqi-demo` environment. Configure environment reviewers before using deployment.

[Cloud setup and rollback](docs/deployment.md) covers GCP Cloud Run, Artifact Registry, Cloud Storage, Cloud Logging and GitHub OIDC. [Deploy script](scripts/deploy.sh) checks the model gate, uploads artifacts, deploys a private candidate, verifies its model version and records approval before switching traffic. Cloud Run scales to zero, service/revision caps three, concurrency eight; tagged candidates may add capacity outside the production traffic split. Neither training nor monitoring auto-promotes models.

Cloud setup/deployment requires the owner's GCP project, billing and GitHub environment configuration. Local implementation and cloud templates do not prove a live cloud deployment. No Kubernetes required: Docker on managed Cloud Run covers containerization and scaling with less setup.

## Rubric evidence

| Rubric | Evidence |
|---|---|
| CO1: Cloud services / MLOps (2) | Deployment workflow and guide; capture actual GCP resources after deploying |
| CO2: Pipeline / CI/CD (2) | `pipeline.py`, chronological tests, GitHub checks and container smoke test |
| CO3: Tracking / monitoring / optimization (2) | MLflow parent/tuning runs, baseline gate, `monitor.py`, seasonal/extreme metrics |
| CO4: Documentation / deployment / presentation (4) | README, provenance, model card, cloud runbook, presentation notes, vector poster |
| Poster: pipeline / container / deployment (3) | Ordered pipeline, Docker, scaling, rollout/rollback, cold-start/IAM challenges |
| Poster: governance / responsible AI (2) | Visual cards: versioning, audit trail, compliance, seasonal bias checks |

See [presentation notes](docs/presentation.md). Rubric mapping is evidence to demonstrate, not a promised mark.
