#!/usr/bin/env bash
# Decrypt secrets/<name>.enc.yaml with SOPS + age (doc 37).
#   sops-load.sh <name> <out.env>          write a dotenv file (umask 077, atomic)
#   sops-load.sh <name> --exec -- <cmd…>   run cmd with secrets in its env only (nothing on disk)
# Needs: sops, and an age private key in $SOPS_AGE_KEY_FILE (default ~/.config/sops/age/keys.txt)
# or $SOPS_AGE_KEY. Never prints secret values.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
name="${1:?usage: sops-load.sh <name> <out.env> | <name> --exec -- cmd}"; shift
file="${SOPS_SECRETS_FILE:-$ROOT/secrets/${name}.enc.yaml}"
command -v sops >/dev/null 2>&1 || { echo "sops not installed (https://github.com/getsops/sops)" >&2; exit 127; }
[ -f "$file" ] || { echo "no encrypted file: $file (see secrets/README.md)" >&2; exit 2; }
if [ -z "${SOPS_AGE_KEY:-}" ] && [ ! -f "${SOPS_AGE_KEY_FILE:-$HOME/.config/sops/age/keys.txt}" ]; then
  echo "no age key: set SOPS_AGE_KEY_FILE or SOPS_AGE_KEY (see secrets/README.md)" >&2; exit 3
fi
if [ "${1:-}" = "--exec" ]; then
  shift; [ "${1:-}" = "--" ] && shift
  [ $# -gt 0 ] || { echo "nothing to exec" >&2; exit 2; }
  exec sops exec-env "$file" "$(printf '%q ' "$@")"
fi
out="${1:?output path required}"
umask 077
tmp="$(mktemp "$(dirname "$out")/.sops-load.XXXXXX")"
trap 'rm -f "$tmp"' EXIT
sops -d --output-type dotenv "$file" > "$tmp"
[ -s "$tmp" ] || { echo "decrypted file is empty" >&2; exit 4; }
mv "$tmp" "$out"; trap - EXIT
echo "wrote $(wc -l < "$out") keys to $out"
