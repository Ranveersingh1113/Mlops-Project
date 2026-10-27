# Deployment and practical improvements

User authorized deployment first, then the previously proposed data, model, monitoring and presentation improvements (2026-10-27).

## Design

Keep the stateless FastAPI/Docker design. Deploy privately to Cloud Run in `asia-south1`, publish images to Artifact Registry and preserve run/audit objects in versioned Cloud Storage. Use a separate private GitHub repository and repository/branch/workflow-bound OIDC for manual releases. The current GitHub plan supports branch restrictions but rejected required reviewers; audits must not claim independent approval. Service-scoped deploy IAM supports updates; an owner must bootstrap if the service is deleted.

For fresh inputs, fetch CPCB's official dated daily bulletin PDFs without credentials. Require the expected bulletin date and exactly one valid Delhi record; require all seven consecutive days, fail clearly if a source is missing, and preserve source URL/hash. Cache successful downloads in each container temporarily; do not call cached historical data current. The dashboard keeps explicit manual inputs and gains a fresh-data button.

Compare one fixed histogram gradient boosting candidate against the current forest using chronological validation. Keep test results separate from selection; assess the selected candidate on a newer, independently sourced holdout where available. Retain the forest if the alternative fails validation or deployment gates; do not promise improved accuracy.

Capture issued current forecasts and later join observed targets for operational monitoring. An initial unlabelled forecast is pending evidence, not a measured production error. Keep retrospective and injected-drift demonstrations explicitly labelled. Update documentation and the vector poster with verified deployment/model evidence.

## Plan and ledger

1. [x] Recover Docker, build/smoke the actual container, reauthenticate GCP and verify billing. Local tests: 13 pass after bootstrap regression.
2. [x] Create cloud resources and deploy owner-bootstrap private revision. Actual cloud health/model/predict/dashboard smoke passed. Record bootstrap evidence in the artifact bucket.
3. [ ] Finish GitHub OIDC rollout, verify service version, demonstrate rollback/restoration, record logs and scaling settings.
4. [ ] Add tested official bulletin ingestion and fresh-input dashboard flow.
5. [ ] Compare one alternative model with validation-only selection and document actual results.
6. [ ] Demonstrate monitoring with captured evidence, publish final changes and update poster/presentation.

Review: bootstrap/update handling cleared. Rerun actor attribution gap reproduced with a failing test, fixed by recording original and triggering actors plus run attempt; suite 13 passes. Original first dispatch can finish safely because dispatcher and triggering actor are the same.
