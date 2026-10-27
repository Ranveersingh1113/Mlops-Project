# Delhi AQI forecasting design

User objective: an implementable MLOps coursework project relevant to India, with accessible real data. Create a poster before implementation. User selected Delhi forecasting and instructed implementation to start.

Build a separate project here, leaving Comrade application code untouched. Python/scikit-learn trains a next-day city-average AQI regressor from the preceding seven consecutive days and forecast-date calendar fields. Persistence (tomorrow equals today) is the honest baseline. Public Delhi CPCB bulletin compilation supplies 3,143 observations, May 2015 through December 2023. Missing dates remain missing: never interpolate with future observations. Duplicate dates and invalid AQI values fail validation.

Use fixed chronological 60/20/20 train/validation/test partitions. Tune two Random Forest depths on validation, evaluate the selected model on test once. Gate release on beating persistence test MAE, and report MAE, RMSE, seasonal MAE and extreme-AQI error. Model-selection results are limited to this historical split, not unseen cities or live performance.

FastAPI serves a static dashboard and validates exactly seven dated consecutive AQI observations in [0,500]. It exposes health, model report and forecast endpoints. Responses identify model/run version, date and freshness; historical inputs are labeled replay. A CLI monitoring report joins timestamped predictions to actual observations, checks input distribution shift and produces an explicit review recommendation; it never promotes models.

MLflow tracks local experiments in SQLite. Each immutable run folder includes trusted model artifact, report, test predictions, provenance and input histogram. Artifact loading never accepts a user-supplied pickle. Docker bakes a specified run into the image. CI tests and trains on committed source data; manual GCP deployment uses OIDC, Artifact Registry, Cloud Storage, Cloud Logging and private Cloud Run with a three-instance cap. Deploy candidate without traffic, smoke-test tagged revision, switch traffic only during the manually dispatched deployment. Record operator, run, image digest and revision; document rollback.

Governance: SHA-256 data hashes, Git revision, MLflow run ID, deployment audit; public aggregate data only; retain logs 30 days; report seasonal errors and extreme-event limitations. This project forecasts AQI, not clinical outcomes. Historical data alone cannot provide current forecasts.

Validation: regressions for missing dates, duplicate dates, past-only features, chronological split, invalid API requests, forecast date, stale input, model gate and drift. Train real data, perform API smoke test and build/test container if Docker is available. Cloud deployment requires a configured GCP project and GitHub OIDC; no live cloud success claim without evidence.
