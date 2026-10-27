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

Open http://127.0.0.1:8015. The prefilled historical example ends 2023-12-31. Click **Load latest CPCB data**, then **Predict AQI**, to fetch seven verified official daily bulletins and forecast the following day. Missing or changed source data produces an explicit error; manual entry remains available. CPCB's bulletin is a daily city aggregate published at 4 PM, rather than an instantaneous reading.

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

Additional comparison (`uv run python compare_models.py`): forest validation MAE **32.53**, histogram gradient boosting **33.35**. Validation retains the forest. On 204 separately sourced 2025 backtest days, forest MAE **30.04** vs persistence **29.68**; the original improvement does not generalize to this period. Comparison logs to MLflow and does not automatically promote a model. Treat current predictions as experimental and compare them with the last observed AQI.

## Deployed instance

Cloud Run deployed in Mumbai (`asia-south1`) on 2026-10-27. [Private source repository](https://github.com/Ranveersingh1113/delhi-aqi-mlops); [successful fresh-data CI/CD release](https://github.com/Ranveersingh1113/delhi-aqi-mlops/actions/runs/40516989515). Actual cloud health/model/forecast/dashboard smoke and fresh CPCB ingestion passed, together with an earlier verified rollback and restoration. The service requires Google Cloud IAM access. Use `gcloud run services proxy delhi-aqi --region asia-south1 --project gen-lang-client-0903575793 --port 8017` and open http://127.0.0.1:8017. On this Windows installation, if `gcloud` is outside PATH:

```powershell
& "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" run services proxy delhi-aqi --region asia-south1 --project gen-lang-client-0903575793 --port 8017
```

Active verified revision: `delhi-aqi-00006-leh`; model run: `935c1f3f6a8a4b21a446a205741af814`. See [deployment evidence](docs/deployment-evidence.json) and [cloud dashboard screenshot](docs/dashboard-cloud.png). Forecast captured on 2026-10-27 for 2026-10-28: AQI 222.04, with operational accuracy explicitly pending the future actual observation.

Resources: Artifact Registry `aqi-models`, Cloud Run `delhi-aqi`, versioned bucket `gs://gen-lang-client-0903575793-aqi-artifacts`. Request-based serving scales to zero with service/revision maxima 3; this is not a hard spending cap. GitHub OIDC is restricted to the private repository, default branch `codex/deploy`, deployment workflow and manual dispatch. The current GitHub plan rejected independent required reviewers; a release is manually dispatched with branch restrictions and actor audit.

## Monitoring

Capture a genuine future forecast (through the authenticated proxy for Cloud Run):

```powershell
uv run python scripts/capture_forecast.py http://127.0.0.1:8017 --output-dir artifacts/operational/demo
```

This writes the deployed report, source provenance, forecast, operational CSV and an explicit `awaiting_actuals` status with no invented MAE. Use a new output directory per capture. After the target day's bulletin appears, export actuals and evaluate:

```powershell
uv run python observations.py --csv artifacts/latest-actuals.csv
uv run python monitor.py --run-dir artifacts/operational/demo --predictions artifacts/operational/demo/predictions.csv --actuals artifacts/latest-actuals.csv
```

The recent-actuals export covers seven days; archive/join older actuals separately for longer evaluations. A single matched day is insufficient for drift/error alerts; at least 30 matches are required. Forecasts already appear as structured Cloud Logging events, including input history and issuance time. Captures with historical replay, late issuance or inconsistent model versions fail explicitly.

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
