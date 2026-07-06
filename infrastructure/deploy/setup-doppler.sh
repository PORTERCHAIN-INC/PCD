#!/usr/bin/env bash
# One-time Doppler setup for Porterchain production (DD-14).
#
# Prerequisites:
#   brew install dopplerhq/cli/doppler
#   doppler login
#   gh auth login
#   SSH access to prod droplet (DEPLOY_* secrets in GitHub)
#
# Usage:
#   bash infrastructure/deploy/setup-doppler.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

PROJECT="${DOPPLER_PROJECT:-pcd}"
CONFIG="${DOPPLER_CONFIG:-prd}"
DROPLET_HOST="${DEPLOY_HOST:-}"
SSH_KEY="${DEPLOY_SSH_KEY_PATH:-$HOME/.ssh/pcd_deploy}"
SSH_USER="${DEPLOY_USER:-root}"
IMPORT_ENV="$(mktemp)"
IMPORT_JSON="$(mktemp)"
trap 'rm -f "$IMPORT_ENV" "$IMPORT_JSON"' EXIT

echo "==> Checking Doppler CLI..."
command -v doppler >/dev/null
if ! doppler me >/dev/null 2>&1; then
  echo "Not logged in. Opening browser for doppler login..."
  doppler login
fi
echo "Logged in as: $(doppler me --json | python3 -c 'import json,sys; print(json.load(sys.stdin).get("user",{}).get("email","?"))')"

echo "==> Ensuring project ${PROJECT} / config ${CONFIG}..."
if ! doppler projects get "$PROJECT" >/dev/null 2>&1; then
  doppler projects create "$PROJECT" --description "Porterchain production secrets"
fi
if ! doppler configs get --project "$PROJECT" "$CONFIG" >/dev/null 2>&1; then
  doppler configs create "$CONFIG" --project "$PROJECT"
fi

echo "==> Fetching prod .env from droplet..."
if [ -z "$DROPLET_HOST" ]; then
  if command -v gh >/dev/null && gh secret list 2>/dev/null | grep -q DEPLOY_HOST; then
    echo "Set DEPLOY_HOST env var or export from: gh secret list"
    DROPLET_HOST="$(gh api repos/:owner/:repo/actions/secrets/DEPLOY_HOST 2>/dev/null || true)"
  fi
fi
if [ -z "$DROPLET_HOST" ]; then
  # Known prod IP from deploy docs
  DROPLET_HOST="68.183.103.49"
  echo "Using default droplet host ${DROPLET_HOST}"
fi

ssh -i "$SSH_KEY" -o ConnectTimeout=15 "${SSH_USER}@${DROPLET_HOST}" 'cat /opt/porterchain/.env' > "$IMPORT_ENV"
ssh -i "$SSH_KEY" -o ConnectTimeout=15 "${SSH_USER}@${DROPLET_HOST}" 'cat /opt/porterchain/secrets/firebase-service-account.json' > "$IMPORT_JSON"

# Merge GitHub vars not always on droplet .env
{
  cat "$IMPORT_ENV"
  echo "PORTERCHAIN_PUSH_ENABLED=true"
  echo "PORTERCHAIN_PUSH_SEND=true"
  echo "API_REPLICAS=2"
} | grep -v '^#' | grep -v '^$' | sort -u -t= -k1,1 > "${IMPORT_ENV}.merged"
mv "${IMPORT_ENV}.merged" "$IMPORT_ENV"

# Add Firebase JSON as single-line secret
python3 - <<PY
import json
from pathlib import Path
env_path = Path("$IMPORT_ENV")
json_path = Path("$IMPORT_JSON")
if json_path.stat().st_size > 2:
    compact = json.dumps(json.loads(json_path.read_text()))
    lines = [l for l in env_path.read_text().splitlines() if not l.startswith("FIREBASE_CREDENTIALS_JSON=")]
    lines.append(f"FIREBASE_CREDENTIALS_JSON={compact}")
    env_path.write_text("\n".join(lines) + "\n")
PY

echo "==> Uploading secrets to Doppler (${PROJECT}/${CONFIG})..."
doppler secrets upload "$IMPORT_ENV" --project "$PROJECT" --config "$CONFIG"

echo "==> Creating deploy service token..."
TOKEN_NAME="github-deploy-$(date +%Y%m%d)"
SERVICE_TOKEN="$(doppler configs tokens create "$TOKEN_NAME" \
  --project "$PROJECT" \
  --config "$CONFIG" \
  --max-age 0s \
  --plain)"

echo "==> Setting GitHub secret DOPPLER_TOKEN..."
gh secret set DOPPLER_TOKEN -b "$SERVICE_TOKEN"
gh variable set DOPPLER_PROJECT -b "$PROJECT" 2>/dev/null || gh variable set DOPPLER_PROJECT -b "$PROJECT"
gh variable set DOPPLER_CONFIG -b "$CONFIG" 2>/dev/null || gh variable set DOPPLER_CONFIG -b "$CONFIG"

echo ""
echo "✓ Doppler configured: project=${PROJECT} config=${CONFIG}"
echo "✓ GitHub secret DOPPLER_TOKEN set"
echo ""
echo "Next: run Deploy workflow (or push to main) — sync-secrets.sh will use Doppler."
echo "Verify on droplet after deploy:"
echo "  ssh ${SSH_USER}@${DROPLET_HOST} 'head -1 /opt/porterchain/.env && doppler secrets --only-names 2>/dev/null || true'"
