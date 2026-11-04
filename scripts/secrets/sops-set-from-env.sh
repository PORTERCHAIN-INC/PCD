#!/usr/bin/env bash
# Copy keys from a local dotenv file into a SOPS file (doc 37).
#   sops-set-from-env.sh <name> <local.env>     e.g. sops-set-from-env.sh droplet mail-keys.local.env
# Each KEY=value line is written with `sops set`; blank values and comments are skipped.
# Needs sops and an age key that can decrypt secrets/<name>.enc.yaml. Never prints values.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
name="${1:?usage: sops-set-from-env.sh <name> <local.env>}"
src="${2:?local env file required}"
file="${SOPS_SECRETS_FILE:-$ROOT/secrets/${name}.enc.yaml}"
command -v sops >/dev/null 2>&1 || { echo "sops not installed" >&2; exit 127; }
command -v python3 >/dev/null 2>&1 || { echo "python3 required" >&2; exit 127; }
[ -f "$file" ] || { echo "no encrypted file: $file (see secrets/README.md)" >&2; exit 2; }
[ -f "$src" ] || { echo "no local env file: $src" >&2; exit 2; }
n=0
while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in ''|\#*) continue ;; esac
  key="${line%%=*}"; val="${line#*=}"
  [[ "$key" =~ ^[A-Z][A-Z0-9_]*$ ]] || { echo "skip invalid key: $key" >&2; continue; }
  val="${val%\"}"; val="${val#\"}"; val="${val%\'}"; val="${val#\'}"
  [ -n "$val" ] || continue
  sops set "$file" "[\"$key\"]" "$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$val")"
  n=$((n + 1)); echo "set $key"
done < "$src"
echo "updated $n keys in $file"
