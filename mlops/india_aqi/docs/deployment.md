# Cloud deployment and rollback

Status: configuration/runbook supplied. A live GCP deployment must be performed and verified in the owner's account before claiming cloud marks.

## One-time setup

Use Google Cloud CLI/Cloud Shell. Choose a project with billing enabled and a region; `asia-south1` is a suitable India-region example. Set your values; commands create resources and may incur charges.

```bash
export GCP_PROJECT_ID=YOUR_PROJECT
export GCP_REGION=asia-south1
export GCP_ARTIFACT_REPO=aqi-models
export GCP_BUCKET=YOUR_GLOBALLY_UNIQUE_BUCKET
gcloud config set project "$GCP_PROJECT_ID"
gcloud services enable run.googleapis.com artifactregistry.googleapis.com storage.googleapis.com iamcredentials.googleapis.com logging.googleapis.com
gcloud artifacts repositories create "$GCP_ARTIFACT_REPO" --repository-format=docker --location="$GCP_REGION"
gcloud storage buckets create "gs://$GCP_BUCKET" --location="$GCP_REGION" --uniform-bucket-level-access
gcloud storage buckets update "gs://$GCP_BUCKET" --versioning
gcloud iam service-accounts create aqi-deploy
gcloud iam service-accounts create aqi-runtime
export GCP_DEPLOY_SA="aqi-deploy@${GCP_PROJECT_ID}.iam.gserviceaccount.com"
export GCP_RUNTIME_SA="aqi-runtime@${GCP_PROJECT_ID}.iam.gserviceaccount.com"
gcloud projects add-iam-policy-binding "$GCP_PROJECT_ID" --member="serviceAccount:$GCP_DEPLOY_SA" --role=roles/run.admin
gcloud projects add-iam-policy-binding "$GCP_PROJECT_ID" --member="serviceAccount:$GCP_DEPLOY_SA" --role=roles/run.invoker
gcloud artifacts repositories add-iam-policy-binding "$GCP_ARTIFACT_REPO" --location="$GCP_REGION" --member="serviceAccount:$GCP_DEPLOY_SA" --role=roles/artifactregistry.writer
gcloud storage buckets add-iam-policy-binding "gs://$GCP_BUCKET" --member="serviceAccount:$GCP_DEPLOY_SA" --role=roles/storage.objectAdmin
gcloud iam service-accounts add-iam-policy-binding "$GCP_RUNTIME_SA" --member="serviceAccount:$GCP_DEPLOY_SA" --role=roles/iam.serviceAccountUser
gcloud iam service-accounts add-iam-policy-binding "$GCP_DEPLOY_SA" --member="serviceAccount:$GCP_DEPLOY_SA" --role=roles/iam.serviceAccountTokenCreator
```

Runtime needs no application resource permissions: the model is inside the image, and logs go to stdout. Cloud Run service agent needs image-reader access (same-project default generally supplies it); investigate actual permission failures rather than granting broad runtime access.

Configure [GitHub Workload Identity Federation](https://github.com/google-github-actions/auth#workload-identity-federation-through-a-service-account). Trust only your specific repository and default branch; bind `roles/iam.workloadIdentityUser` on `aqi-deploy` to that federated principal set. Use repository owner/repository IDs where possible to prevent name-reuse attacks. No exported service-account key needed.

Create GitHub environment `aqi-demo`, require reviewers, restrict it to default branch. Set its variables: `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_ARTIFACT_REPO`, `GCP_BUCKET`, `GCP_DEPLOY_SA`, `GCP_RUNTIME_SA`, `GCP_WIF_PROVIDER`. Workflow checks the repository's configured default branch. Protect workflow changes with code review.

## Release

Manually dispatch **Delhi AQI MLOps**, choose `deploy=true`, then approve the `aqi-demo` environment. Failed checks prevent deployment. Candidate is deployed privately with a tagged URL, no intended production traffic; health smoke-test confirms exact run ID. The script records approver and prior traffic in versioned Cloud Storage before switching to the candidate revision. First deployment has no previous production revision; private access limits exposure during bootstrap. Monitor CLI and training do not deploy.

Cloud Run settings: 1 CPU, 512 MiB, scale-to-zero, service-level maximum 3 (`--max`), revision maximum 3 (`--max-instances`), concurrency 8. Tagged candidates can add capacity outside the production traffic split. Maximum instances is a capacity control, not a hard billing cap. API schema rejects invalid AQI/gaps; private service IAM limits callers. [Scaling reference](https://docs.cloud.google.com/run/docs/configuring/max-instances). For dashboard access:

```bash
gcloud run services proxy delhi-aqi --region "$GCP_REGION" --port 8080
```

Open localhost:8080. Grant operator `roles/run.invoker` if needed. For automation, identity-token audience is the service URL, including when calling a tagged revision. API logs emit `textPayload` containing JSON event records; inspect latency, status and forecast model/version with Cloud Logging.

## Monitor and rollback

Export structured forecast logs to CSV (`date=target_date`, `prediction=aqi`, `last_aqi`, `model_version`, `issued_at`, `historical_replay`), obtain actual daily AQI, and run `monitor.py --run-dir ... --predictions ... --actuals ...`. The operational evaluator excludes replays and late forecasts; earliest eligible issuance per date is selected. Retrospective test CSVs use explicitly labeled backtest mode. Inspect flags; do not auto-promote. Retraining on newer data requires a reviewed source and fresh holdout.

From the audit object, retrieve previous revision names and traffic shares. To restore a prior single revision:

```bash
gcloud run services update-traffic delhi-aqi --region "$GCP_REGION" --to-revisions=PREVIOUS_REVISION=100
gcloud run services describe delhi-aqi --region "$GCP_REGION" --format=json
```

Record rollback actor/time/revision as another audit object. Preserve the prior image in Artifact Registry. For a prior split, restore its recorded percentages instead of guessing a single revision. Failed candidate smoke test leaves the prior intended traffic split unchanged; a failure after the traffic switch is explicitly reported, and the pre-switch audit supplies rollback information.

## Retention and demonstration evidence

Keep application logs 30 days (Cloud Logging `_Default` bucket setting); CI artifacts 14 days. Preserve model provenance and deploy audit for the coursework period; restrict bucket access and do not put personal information in logs. Configure bucket lifecycle separately before long-running use; do not confuse proposed policy with configured retention.

Capture actual successful CI, deployed revision, image digest, Cloud Storage artifacts, Cloud Logging event, scale settings and rollback. Cost and accuracy are not guaranteed; no clinical or compliance certification claimed.

References: [Cloud Run rollout/rollback](https://docs.cloud.google.com/run/docs/rollouts-rollbacks-traffic-migration), [private service access](https://docs.cloud.google.com/run/docs/authenticating/developers), [GitHub OIDC action](https://github.com/google-github-actions/auth), [MLflow tracking](https://mlflow.org/docs/latest/ml/tracking/).
