# Verification evidence

Cloud Run deployment, full GitHub OIDC CI/CD, authenticated HTTP smoke, rollback and restoration succeeded on 2026-10-27. The fresh-data follow-up also deployed successfully and passed actual Cloud Run and browser verification.

## Practical follow-up (2026-10-27)

Final follow-up release: https://github.com/Ranveersingh1113/delhi-aqi-mlops/actions/runs/40516989515 . Active revision `delhi-aqi-00006-leh`, model run `935c1f3f6a8a4b21a446a205741af814`. Authenticated Cloud Run `/observations/latest` fetched seven current official bulletins; `/predict` issued AQI 222.04 for 2026-10-28. The actual cloud dashboard journey also passed; screenshot `dashboard-cloud.png`. See `deployment-evidence.json`, `model-comparison.json`, `forecast-2026-10-28.json` and `operational-status.json`. Original rollout and follow-up release both succeeded; failed/queued intermediate attempts were not treated as successful evidence.

- Suite: 19 passed; one upstream Starlette deprecation warning.
- Official live source: seven CPCB bulletins, 2026-10-21–2026-10-27, successfully parsed in both Python and the actual Linux Docker container. Last AQI: 197. Dates, city, category, station counts and SHA-256 verified.
- Real browser flow: Load latest CPCB data -> form populated with seven current observations -> Predict AQI -> target 2026-10-28, forest prediction 222.04. Screenshot: `dashboard-fresh-local.png`.
- Operational capture: future-issued forecast persisted with provenance; `awaiting_actuals`, operational MAE null. No invented observed target or production score.
- Model comparison: forest validation MAE 32.5286 beats histogram gradient boosting 33.3544. New independent 2025 backtest has 204 complete windows: forest MAE 30.0427, persistence 29.6765. Original gain does not generalize; forest retained as an experimental demonstration and no alternative promoted.
- Initial full release passed: https://github.com/Ranveersingh1113/delhi-aqi-mlops/actions/runs/40514155984 . Revision `delhi-aqi-00002-ves`, model run `6a90206998084a58a45581cb6007635b`.
- Actual rollback to `delhi-aqi-00001-vec` passed health/model/forecast/dashboard smoke, followed by restoration to `delhi-aqi-00002-ves` and another successful smoke.
- Verified service/revision maxima 3, concurrency 8, CPU 1, memory 512 MiB, private IAM, actual forecast logs and 30-day log retention.
- GitHub reviewer protection unavailable on current private-repository plan (HTTP 422); default-branch environment restriction and repository/branch/workflow/manual-dispatch-bound OIDC are configured. Audit identifies original and triggering actor plus run attempt.
- Fresh review found a UTC/India date mismatch in the capture test; a frozen 20:00 UTC case reproduced it, then the India-date fix passed. Source fallback, holdout isolation and serving dependency wiring were reviewed.
- Updated A3 vector poster rendered and visually inspected with no clipping.

## Deployment preflight (2026-10-27)

- `uv run --frozen pytest -q`: 11 passed, one upstream Starlette deprecation warning.
- Docker Desktop engine 28.4.0 started successfully.
- Built `delhi-aqi:deploy-check` from run `53f5c4ef9f074ed8993563fad5e4ab38`.
- Image ID: `sha256:6bfcb319fd7536a69ab1c4884ae6d18bce9178b129b34d7377eef8feb2b4b2a9`.
- Started container as non-root `appuser`, limited to 1 CPU and 512 MiB, bound only to localhost port 8016.
- Real HTTP smoke passed for health, model report, prediction and dashboard. Docker health status: healthy.
- User selected GCP project `gen-lang-client-0903575793`. Existing Google Cloud CLI installation found outside PATH; cached credentials expired. Browser reauthentication initiated; project access/billing and cloud deployment still unverified.
- GitHub authentication works; remote repository default branch is `master`. Hosted workflow has not yet been run.

## Original implementation evidence (2026-10-06)

| Check | Observed result |
|---|---|
| Source verification | 144,266 bytes; SHA-256 matches pinned source; 3,143 Delhi rows |
| Complete windows | 3,031; train 1,818 / validation 606 / test 607 |
| Unit/regression suite | 11 passed; one upstream Starlette warning about `httpx` deprecation |
| Training | Depth 8 selected on validation; test MAE 31.0941 / RMSE 41.2934 |
| Baseline | Test MAE 31.6063 / RMSE 43.4762; model gate passes |
| Actual API smoke | Health, model report, forecast and dashboard passed over HTTP on localhost:8015 |
| Forecast example | 2024-01-01 AQI 371.47, explicitly historical replay; issuance timestamp included |
| Normal backtest monitor | 607 matches; PSI 0.06925; no flags |
| Injected-drift monitor | PSI 8.09682; explicit input-shift flag and review action; marked simulated |
| Browser journey | Prefilled real history -> Predict AQI -> forecast/chart/replay label; visual check saved as `dashboard.png` |
| Poster | A3 vector PDF + editable SVG; latest PDF rendered and visually checked |
| Workflow static checks | YAML parsed; check/deploy dependency verified; deploy Bash syntax passes |
| Fresh review | Two P2 findings addressed; follow-up found no remaining obvious deployment blocker |
| Invalid nonfinite JSON | Regression caught framework 500 while serializing NaN error input; handler now returns 422 for NaN/Infinity |
| Docker | Desktop remained starting; engine returned HTTP 500. Image/container not verified locally |
| Cloud | No configured GCP CLI/project/OIDC; deployment not executed |

Latest measured run: `53f5c4ef9f074ed8993563fad5e4ab38`. Immutable report and model remain locally under `artifacts/`; MLflow SQLite retains the experiment history. Git parent SHA alone does not identify uncommitted code; report includes a pipeline SHA-256 and dirty-worktree indicator.

The supplied GitHub workflow builds and smoke-tests the real image before allowing cloud deployment. Run it after pushing the source to obtain hosted CI evidence. Configure GCP and protected GitHub environment per deployment guide before producing live cloud evidence.
