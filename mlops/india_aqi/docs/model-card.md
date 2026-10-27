# Model card: Delhi next-day city AQI

Purpose: coursework demonstration and pollution-trend awareness. Target: next calendar day's published Delhi city-average AQI; input: seven prior consecutive days. No weather feed, causal attribution, personal exposure or medical prediction.

Data: unchanged UrbanEmissions compilation of CPCB bulletins; 3,143 records from 2015-05-01 to 2023-12-31. Missing calendar days break windows. Public source metadata does not establish an unrestricted commercial license. Credit original sources.

Model: 120-tree Random Forest, seed 42, minimum leaf size 3, depth selected from 8/16 on chronological validation. Baseline: last AQI repeated. Calendar features contain no future observations. Target-period labels are never training features.

Evaluation: fixed chronological 60/20/20 windows. First run test contains 607 dates; model MAE 31.0941, RMSE 41.2934; baseline MAE 31.6063, RMSE 43.4762. These are measured historical results, not live claims. Artifact `report.json` includes actual split boundaries, per-season metrics, AQI >=301 error, data hash and run ID.

Seasonal error reporting identifies uneven performance; it does not prove demographic fairness. City averages hide station/neighborhood differences. Sensor coverage changes over time. Rare severe events may be underpredicted. No extrapolation claim for other cities or the current pollution regime. Random forests cannot forecast unseen extreme magnitudes reliably.

Governance: baseline quality gate, trusted serialized artifacts, versioned runs, explicit deployment operator and revision audit. Test gate is a coursework demonstration; repeatedly tuning against its pass/fail response overfits that holdout. Production use requires rolling-origin validation, a new holdout, recent data, calibration of alert thresholds and station-level coverage review.

Monitoring: delayed-label error and input histogram PSI. >=30 matched samples; review when PSI >0.2 or MAE increases >25% over recorded test MAE. No automatic retraining or promotion. Model scores have no promised uncertainty interval. Staff/user must inspect forecasts before any consequential operational use.

Additional evaluation (2026-10-27): fixed histogram gradient boosting (120 iterations, 15 leaves, learning rate 0.05, L2=1, seed 42) scored validation MAE 33.3544, versus forest 32.5286. The forest remains selected by validation. Only after this selection, the separate 2025-01-09–2025-07-31 backtest (204 complete windows) yielded forest MAE 30.0427 / RMSE 39.4235 vs persistence MAE 29.6765 / RMSE 40.2136. Forest does not beat persistence MAE on this newer period. This limits the original gate's generalization; no alternative model is promoted and accuracy improvement is not claimed for current forecasts. Weather features or rolling-origin evaluation would be separate future work, not covert tuning on this holdout.

Fresh inputs: official CPCB dated PDFs; unique Delhi row, publication date, range/category and station coverage verified; source URLs and SHA-256 retained. Current inputs do not imply current accuracy. Missing recent bulletins fail explicitly; only today's missing publication permits a labelled one-day fallback.
