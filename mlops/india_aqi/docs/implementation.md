# Delhi AQI Implementation Plan

> Execution: native in this session, as requested by the user. Use executing-plans; tests precede nontrivial implementation.

**Goal:** a runnable, documented MLOps project with an already-created vector poster.
**Architecture:** local MLflow + immutable trained run; stateless FastAPI + dashboard; Docker image and manual GCP rollout.
**Stack:** Python, NumPy, scikit-learn, MLflow, FastAPI, Docker, GitHub Actions, GCP.
**Spec:** `docs/design.md`.

## Constraints
Seven consecutive daily inputs; target next calendar day; no future information; chronological 60/20/20 split; gate candidate test MAE against persistence; no automatic promotion. Keep existing Comrade files intact.

## Review focus
Missing days must break windows. Duplicates must fail. Nonfinite or out-of-range AQI must fail. Empty monitoring joins must fail rather than report healthy. Cloud rollout must verify candidate before switching traffic.

## Tasks
1. [x] Create vector SVG/A3 PDF poster, render and inspect.
2. [x] Create `pipeline.py` (`read_series`, `examples`, `features`, `split`, `train`); copy verified source CSV with attribution; train and record evidence. Four pipeline tests pass.
3. [x] Write failing forecast/API/drift tests; create `app.py`, `monitor.py`, `dashboard.html`; run tests and actual API smoke test.
4. [x] Add Dockerfile and CI/deploy workflow; document cloud permissions, deployment/rollback and evidence. Bash/YAML checked; local Docker build blocked by unhealthy engine, live GCP unconfigured.
5. [x] Create README, model card and presentation notes mapping rubrics to files/commands. Fresh review completed; both P2 findings fixed and reviewed again. Final tests: 11 pass, including a nonfinite-JSON validation regression.

## Execution ledger

- Poster created as vector SVG/PDF before product implementation, rendered and visually checked.
- Ruling: isolate in a new project folder, preserve existing Comrade edits; no merge or commit performed.
- Real-data training beats persistence slightly; retain measured result and disclose limitation rather than tune on final test.
- Review fixes: service/revision scale caps; separate operational forecasts from backtests, require issuance time, exclude late/replay evidence, deterministically select earliest daily issuance.
- Data acquisition: all-India archive transfer was incomplete and discarded as a source; directly downloaded and checksum-verified complete Delhi CSV.
- External verification pending: GitHub workflow execution, Docker container build/smoke (engine HTTP 500), and live GCP deployment (project/OIDC not configured).
- 2026-10-27 deployment continuation: Docker engine recovered; actual image builds and passes HTTP smoke/health as non-root under 1 CPU / 512 MiB. All 11 tests pass again. User selected `gen-lang-client-0903575793`; existing gcloud credentials expired, browser login initiated. Cloud billing/access/OIDC and hosted CI remain pending. Next: deploy, then current data ingestion, validation-only model comparison, operational monitoring evidence and poster/presentation updates.

Tests: `uv run --project mlops/india_aqi pytest mlops/india_aqi/tests -q`.
Real training: `uv run --project mlops/india_aqi python mlops/india_aqi/pipeline.py train`.
