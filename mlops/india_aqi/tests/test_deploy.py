"""Exercise bootstrap and update rollouts through the real shell script."""
import os
import json
from pathlib import Path
import shutil
import subprocess

import pytest


@pytest.mark.parametrize("existing", [False, True])
def test_deploy_bootstrap_and_update(tmp_path, existing):
    bash = Path('C:/Program Files/Git/bin/bash.exe') if os.name == 'nt' else Path(shutil.which('bash'))
    run_id = 'a' * 32
    run = tmp_path / 'artifacts' / run_id
    run.mkdir(parents=True)
    (run.parent / 'latest.json').write_text('{"run_id":"' + run_id + '"}')
    (run / 'report.json').write_text('{"gate_passed":true}')
    (tmp_path / 'data').mkdir()
    (tmp_path / 'data/delhi.csv').write_text('test snapshot')
    fakebin = tmp_path / 'bin'
    fakebin.mkdir()
    commands = {
        'gcloud': '''#!/usr/bin/env bash
set -eu
printf '%s\\n' "$*" >> "$DEPLOY_TRACE"
case "$1 $2 ${3:-}" in
  'run services list') if [ "$TEST_EXISTING" = 1 ]; then echo delhi-aqi; fi ;;
  'run services describe') echo '{"status":{"url":"https://service.example","latestReadyRevisionName":"revision-1","traffic":[{"tag":"candidate","url":"https://candidate.example"}]}}' ;;
  'run deploy delhi-aqi')
    if [ "$TEST_EXISTING" = 0 ] && [[ " $* " = *" --no-traffic "* ]]; then
      echo 'Cloud Run rejects --no-traffic for a new service' >&2; exit 42
    fi ;;
  'auth print-identity-token '*) echo fake-token ;;
esac
''',
        'docker': '#!/usr/bin/env bash\nif [ "$1" = inspect ]; then echo example/image@sha256:abc; fi\n',
        'curl': '#!/usr/bin/env bash\necho \'{"status":"ok","model_version":"' + run_id + '"}\'\n',
    }
    for name, source in commands.items():
        executable = fakebin / name
        executable.write_text(source, newline='\n')
        executable.chmod(0o755)
    env = {**os.environ, 'PATH': str(fakebin) + os.pathsep + os.environ['PATH'],
           'TEST_EXISTING': str(int(existing)), 'DEPLOY_TRACE': (tmp_path / 'trace').as_posix(),
           'FAKE_BIN': fakebin.as_posix()}
    for name in ('GCP_PROJECT_ID', 'GCP_REGION', 'GCP_ARTIFACT_REPO', 'GCP_BUCKET',
                 'GCP_DEPLOY_SA', 'GCP_RUNTIME_SA', 'GITHUB_SHA', 'GITHUB_RUN_NUMBER', 'GITHUB_ACTOR'):
        env[name] = 'test'
    env['GCP_SERVICE'] = 'delhi-aqi'
    env['GITHUB_TRIGGERING_ACTOR'] = 'rerun-operator'
    env['GITHUB_RUN_ATTEMPT'] = '2'
    script = Path(__file__).resolve().parents[1] / 'scripts/deploy.sh'
    launcher = 'curl() { bash "$FAKE_BIN/curl" "$@"; }; export -f curl; source "$1"'
    result = subprocess.run([str(bash), '-c', launcher, 'test-deploy', script.as_posix()], cwd=tmp_path, env=env,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    trace = (tmp_path / 'trace').read_text().splitlines()
    deploy = next(line for line in trace if line.startswith('run deploy '))
    assert ('--no-traffic' in deploy.split()) == existing
    audit_upload = next(i for i, line in enumerate(trace) if line.startswith('storage cp deployment-audit.json'))
    switch = next(i for i, line in enumerate(trace) if line.startswith('run services update-traffic'))
    assert audit_upload < switch
    audit = json.loads((tmp_path / 'deployment-audit.json').read_text())
    assert audit['GITHUB_ACTOR'] == 'test'
    assert audit['GITHUB_TRIGGERING_ACTOR'] == 'rerun-operator'
    assert audit['GITHUB_RUN_ATTEMPT'] == '2'
