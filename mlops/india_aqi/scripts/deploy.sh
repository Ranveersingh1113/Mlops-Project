#!/usr/bin/env bash
set -euo pipefail
for name in GCP_PROJECT_ID GCP_REGION GCP_ARTIFACT_REPO GCP_BUCKET GCP_DEPLOY_SA GCP_RUNTIME_SA GCP_SERVICE GITHUB_SHA GITHUB_RUN_NUMBER GITHUB_ACTOR GITHUB_TRIGGERING_ACTOR GITHUB_RUN_ATTEMPT; do
  if [[ -z "${!name:-}" ]]; then echo "Missing configuration: $name" >&2; exit 1; fi
done
RUN_ID=$(python -c 'import json; print(json.load(open("artifacts/latest.json"))["run_id"])')
export RUN_ID
python -c 'import json,os; r=json.load(open("artifacts/"+os.environ["RUN_ID"]+"/report.json")); assert r["gate_passed"], "Candidate failed baseline gate"'
gcloud config set project "$GCP_PROJECT_ID"
gcloud auth configure-docker "${GCP_REGION}-docker.pkg.dev" --quiet
IMAGE="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${GCP_ARTIFACT_REPO}/${GCP_SERVICE}:${GITHUB_SHA}-${GITHUB_RUN_NUMBER}"
docker build --build-arg "MODEL_RUN=$RUN_ID" -t "$IMAGE" .
docker push "$IMAGE"
IMAGE_DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' "$IMAGE")
export IMAGE_DIGEST
test -n "$IMAGE_DIGEST"
gcloud storage cp "artifacts/$RUN_ID/"* "gs://${GCP_BUCKET}/runs/${RUN_ID}/"
gcloud storage cp data/delhi.csv "gs://${GCP_BUCKET}/data/${RUN_ID}.csv"
gcloud storage cp artifacts/model-comparison.json "gs://${GCP_BUCKET}/comparisons/${RUN_ID}.json"
EXISTING=$(gcloud run services list --region "$GCP_REGION" --filter="metadata.name=${GCP_SERVICE}" --format='value(metadata.name)')
if [[ -n "$EXISTING" ]]; then
  gcloud run services describe "$GCP_SERVICE" --region "$GCP_REGION" --format=json > before-rollout.json
  TRAFFIC_ARGS=(--no-traffic)
else
  printf '{"status":{"traffic":[]}}\n' > before-rollout.json
  # Cloud Run requires initial traffic on a new private service.
  TRAFFIC_ARGS=()
fi
gcloud run deploy "$GCP_SERVICE" --image "$IMAGE_DIGEST" --region "$GCP_REGION" \
  --service-account "$GCP_RUNTIME_SA" --no-allow-unauthenticated "${TRAFFIC_ARGS[@]}" --tag candidate \
  --min-instances 0 --max 3 --max-instances 3 --concurrency 8 --cpu 1 --memory 512Mi --port 8080 --quiet
gcloud run services describe "$GCP_SERVICE" --region "$GCP_REGION" --format=json > candidate-service.json
SERVICE_URL=$(python -c 'import json; print(json.load(open("candidate-service.json"))["status"]["url"])')
CANDIDATE_URL=$(python -c 'import json; print(next(t["url"] for t in json.load(open("candidate-service.json"))["status"]["traffic"] if t.get("tag")=="candidate"))')
REVISION=$(python -c 'import json; print(json.load(open("candidate-service.json"))["status"]["latestReadyRevisionName"])')
export REVISION SERVICE_URL
TOKEN=$(gcloud auth print-identity-token --impersonate-service-account "$GCP_DEPLOY_SA" --audiences "$SERVICE_URL")
curl --fail --silent --show-error --retry 5 --retry-delay 3 \
  --header "Authorization: Bearer ${TOKEN}" "${CANDIDATE_URL}/health" > smoke-result.json
python -c 'import json,os; r=json.load(open("smoke-result.json")); assert r["status"]=="ok" and r["model_version"]==os.environ["RUN_ID"]'
# Archive the proposed switch BEFORE modifying traffic, so a record exists even if the final archive fails.
python - <<'PY'
import json, os
from datetime import datetime, timezone
record = {key: os.environ[key] for key in ("GITHUB_ACTOR", "GITHUB_TRIGGERING_ACTOR", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA", "GITHUB_RUN_NUMBER", "RUN_ID", "IMAGE_DIGEST", "REVISION", "SERVICE_URL")}
record["approved_at"] = datetime.now(timezone.utc).isoformat()
record["approval"] = "manual workflow dispatch on default branch; GitHub environment aqi-demo"
record["previous_traffic"] = json.load(open("before-rollout.json"))["status"].get("traffic", [])
record["status"] = "approved_switch_pending"
json.dump(record, open("deployment-audit.json", "w"), indent=2)
PY
gcloud storage cp deployment-audit.json "gs://${GCP_BUCKET}/audit/${RUN_ID}-${GITHUB_RUN_NUMBER}.json"
gcloud run services update-traffic "$GCP_SERVICE" --region "$GCP_REGION" --to-revisions="${REVISION}=100" --quiet
python -c 'import json; p="deployment-audit.json"; r=json.load(open(p)); r["status"]="traffic_switched"; json.dump(r,open(p,"w"),indent=2)'
gcloud storage cp deployment-audit.json "gs://${GCP_BUCKET}/audit/${RUN_ID}-${GITHUB_RUN_NUMBER}.json"
echo "Deployment complete: $SERVICE_URL"
