#!/usr/bin/env bash
# Render realm-porterchain.json with IdP secrets from the environment (load them with
# scripts/secrets/sops-load.sh first). Output goes to a mode-600 file you pass; never commit it.
#   bash infrastructure/keycloak/render-realm.sh /tmp/realm.json
# APPLE_IDP_ENABLED=true keeps the Apple IdP (needs the apple provider extension installed).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
out="${1:?output path}"
umask 077
python3 - "$HERE/realm-porterchain.json" "$out" <<'PY'
import json, os, re, sys
src, out = sys.argv[1], sys.argv[2]
realm = json.load(open(src))
if os.environ.get("APPLE_IDP_ENABLED", "false") != "true":
    realm["identityProviders"] = [i for i in realm["identityProviders"] if i["alias"] != "apple"]
if os.environ.get("GOOGLE_IDP_ENABLED", "true") != "true":
    realm["identityProviders"] = [i for i in realm["identityProviders"] if i["alias"] != "google"]
text = json.dumps(realm)
missing = set()
def sub(m):
    v = os.environ.get(m.group(1))
    if v is None:
        missing.add(m.group(1)); return m.group(0)
    return json.dumps(v)[1:-1]
text = re.sub(r"\$\{([A-Z0-9_]+)\}", sub, text)
if missing and os.environ.get("ALLOW_PLACEHOLDERS") != "true":
    sys.exit("missing env: " + ", ".join(sorted(missing)))
open(out, "w").write(text)
print(f"rendered realm to {out}")
PY
