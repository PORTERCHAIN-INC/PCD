#!/usr/bin/env bash
# Compatibility wrapper. SSOT: infrastructure/deploy/deploy-rules.json
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
if [[ $# -gt 0 && -f "$1" ]]; then
  python3 "$root/scripts/resolve_deploy_plan.py" --changed-files "$1" --github-output \
    | awk -F= '/^scope=/{print $2; exit}'
else
  python3 "$root/scripts/resolve_deploy_plan.py" --github-output \
    | awk -F= '/^scope=/{print $2; exit}'
fi
