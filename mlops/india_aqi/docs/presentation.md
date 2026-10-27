# Presentation and demonstration

## 1. Problem and India relevance
Delhi AQI varies seasonally. Demonstrate a next-day city-average forecast, with an honest persistence baseline. Public CPCB-derived data avoids API keys and scraping.

## 2. Data and leakage control
Show source hash and date range. Explain seven consecutive past days, missing-day handling, and 60/20/20 chronological splits. Never randomly shuffle time-series examples.

## 3. Model and optimization
Show MLflow parent run and depth-8/depth-16 validation experiments. Report measured MAE 31.09 vs baseline 31.61, not just a pass label. Show seasonal and extreme-AQI errors; acknowledge modest improvement.

## 4. CI/CD and deployment
Explain commit -> tests -> train -> gate -> Docker smoke test -> candidate artifact. Manual dispatch and protected environment -> OIDC -> Artifact Registry -> private Cloud Run -> smoke test -> traffic switch. Show rollback command and image digest.

## 5. Monitoring and governance
Run normal monitoring, then `uv run python monitor.py --inject-drift`. Explain PSI heuristic and false alarms from seasonal shifts. Point to data hash, run ID, Git revision, approval audit and retention rules. Show four governance cards on poster.

## 6. Live demo and limits
1. Open dashboard and inspect historical replay label.
2. Predict from prefilled real seven-day example; display target date and model ID.
3. Submit an invalid AQI to demonstrate boundary validation.
4. Run drift injection; show explicit review recommendation.
5. Open MLflow and candidate artifacts.
6. If GCP configured, show private service through `gcloud run services proxy`, then restore previous revision.

Evidence to collect: test output, model report, MLflow screenshot, CI run, image digest, GCP services, audit object and rollback screenshot. Clearly distinguish local evidence from a completed cloud deployment.
