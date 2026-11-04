"""Dump in-app notification subjects/bodies as dictionary keys ({name} -> {0}, {1}...).

The apps translate server text at render time with the same EN-keyed dictionary, so these
keys let in-app notices show in French without a second template set.
"""
import json, re, sys
sys.path.insert(0, "apps/api/src")
from porterchain_api.notification_engine.templates import TEMPLATES  # noqa: E402

out = set()
for t in TEMPLATES.values():
    for k in ("subject", "body"):
        v = t.get(k) or ""
        if not v or "\n" in v or " / " in v:  # bilingual email-only texts are already EN/FR
            continue
        names = []
        def sub(m):
            if m.group(1) not in names:
                names.append(m.group(1))
            return "{%d}" % names.index(m.group(1))
        out.add(re.sub(r"\{([a-z_]+)\}", sub, v))
# Activity-feed labels shown in the merchant portal (server text).
from porterchain_api.merchant_engine import audit_copy  # noqa: E402

for name in dir(audit_copy):
    v = getattr(audit_copy, name)
    if isinstance(v, dict):
        out.update(x for x in v.values() if isinstance(x, str) and "{" not in x)
json.dump(sorted(out), sys.stdout, ensure_ascii=False)
