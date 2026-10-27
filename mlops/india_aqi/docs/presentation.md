# Presentation and demonstration

## 1. Problem and India relevance
Delhi AQI varies seasonally. Demonstrate a next-day city-average forecast, with an honest persistence baseline. Public CPCB-derived data avoids API keys and scraping.

## 2. Data and leakage control
Show source hash and date range. Explain seven consecutive past days, missing-day handling, and 60/20/20 chronological splits. Never randomly shuffle time-series examples.

## 3. Model and optimization
Show MLflow parent run and depth-8/depth-16 validation experiments. Report original MAE 31.09 vs baseline 31.61. Show the added forest/boosting comparison: validation 32.53 vs 33.35 retains forest; separate 2025 holdout forest 30.04 vs persistence 29.68 does not confirm the original improvement. Show seasonal/extreme-AQI errors and explain the experimental status.

## 4. CI/CD and deployment
Explain commit -> tests -> train -> compare -> gate -> Docker smoke test -> candidate artifact. Manual dispatch on the default branch -> OIDC -> Artifact Registry -> private Cloud Run -> candidate smoke test -> traffic switch. The private repository's plan rejected required reviewers; branch and identity restrictions remain enforced. Show the successful release at https://github.com/Ranveersingh1113/delhi-aqi-mlops/actions/runs/40514155984 and verified rollback/restoration.

## 5. Monitoring and governance
Run normal monitoring, then `uv run python monitor.py --inject-drift`. Explain PSI heuristic and false alarms from seasonal shifts. Point to data hash, run ID, Git revision, approval audit and retention rules. Show four governance cards on poster.

## 6. Live demo and limits
1. Open dashboard through the authenticated Cloud Run proxy; inspect historical replay label.
2. Click Load latest CPCB data, then Predict AQI; display source date, future target and model ID. Compare prediction with persistence.
3. Submit an invalid AQI to demonstrate boundary validation.
4. Run drift injection; show explicit review recommendation.
5. Open MLflow and candidate artifacts.
6. Show the deployed private service, image digest, versioned artifacts, Cloud Logging and rollback evidence. Capture a future forecast; explain why operational MAE stays pending until its actual label arrives.

Evidence to collect: test output, model report, MLflow screenshot, CI run, image digest, GCP services, audit object and rollback screenshot. Clearly distinguish local evidence from a completed cloud deployment.
