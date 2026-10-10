"""Forensic audit CLI (run inside the api container).

  python -m porterchain_api.forensics_cli event deploy --detail '{"sha":"..."}'
  python -m porterchain_api.forensics_cli verify
  python -m porterchain_api.forensics_cli checkpoint
  python -m porterchain_api.forensics_cli export > audit.json
  python -m porterchain_api.forensics_cli keygen      # prints a new AUDIT_SIGNING_KEY (base64)
"""

from __future__ import annotations

import argparse
import base64
import json
import sys


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="forensics_cli")
    sub = p.add_subparsers(dest="cmd", required=True)
    ev = sub.add_parser("event")
    ev.add_argument("action")
    ev.add_argument("--category", default="deploy")
    ev.add_argument("--actor", default=None)
    ev.add_argument("--detail", default="{}")
    for c in ("verify", "checkpoint", "export", "keygen"):
        sub.add_parser(c)
    a = p.parse_args(argv)

    if a.cmd == "keygen":
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        raw = Ed25519PrivateKey.generate().private_bytes(
            serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
        print(base64.b64encode(raw).decode())
        return 0

    from porterchain_api import admin_models  # noqa: F401 - registers models + listeners
    from porterchain_api.db import SessionLocal
    from porterchain_api.platform import forensics

    db = SessionLocal()
    try:
        if a.cmd == "event":
            forensics.record(db, a.category, a.action, actor=a.actor, detail=json.loads(a.detail or "{}"))
            db.commit()
            print("recorded")
        elif a.cmd == "verify":
            v = forensics.verify(db)
            print(json.dumps(v))
            return 0 if v["ok"] else 2
        elif a.cmd == "checkpoint":
            print(json.dumps(forensics.checkpoint(db)))
        elif a.cmd == "export":
            json.dump(forensics.export(db), sys.stdout, default=str)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
