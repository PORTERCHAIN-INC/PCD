#!/usr/bin/env bash
# Self-test for sops-load.sh with a THROWAWAY age key in a temp dir (deleted on exit).
# Uses fake values only. Run: bash scripts/secrets/test-sops-load.sh
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
age-keygen -o "$T/key.txt" 2>/dev/null
PUB="$(grep -o 'age1[0-9a-z]*' "$T/key.txt" | head -1)"
printf 'FAKE_A=alpha\nFAKE_B=beta value\n' > "$T/plain.env"
(cd "$T" && sops -e --age "$PUB" --input-type dotenv --output-type yaml plain.env > x.enc.yaml)
grep -q '^sops:' "$T/x.enc.yaml"; ! grep -q alpha "$T/x.enc.yaml"
export SOPS_AGE_KEY_FILE="$T/key.txt" SOPS_SECRETS_FILE="$T/x.enc.yaml"
bash "$HERE/sops-load.sh" x "$T/out.env" >/dev/null
grep -qx 'FAKE_A=alpha' "$T/out.env"; [ "$(stat -c %a "$T/out.env")" = 600 ]
[ "$(bash "$HERE/sops-load.sh" x --exec -- printenv FAKE_A)" = alpha ]
SOPS_AGE_KEY_FILE="$T/none" bash "$HERE/sops-load.sh" x "$T/o2" 2>/dev/null && exit 1 || [ $? -eq 3 ]
echo "sops-load self-test: 5/5 passed"
