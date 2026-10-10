"""Forensic readiness: tamper-evident, append-only security audit chain.

Every entry stores ``hash = sha256(prev_hash + canonical_json(entry))``. Rows are
append-only (Postgres trigger rejects UPDATE/DELETE/TRUNCATE). Rows written to the
existing audit tables (admin / merchant / access) are mirrored automatically in the same
transaction; logins, failed logins, exports, erasures, webhook config and deploys are
recorded explicitly. Signed checkpoints (Ed25519, key in AUDIT_SIGNING_KEY) pin the head
so even a DB superuser rewriting history is detectable against an exported checkpoint.

Privacy: details are masked (emails/phones partially hidden) and secrets dropped.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import event, insert, select, text
from sqlalchemy.orm import Session

from porterchain_api.forensics_models import ForensicAuditEntry, ForensicCheckpoint

logger = logging.getLogger(__name__)

GENESIS = "0" * 64
_SECRET_KEY = re.compile(r"pass(word)?|secret|token|authorization|cookie|otp|api_?key|signature|assertion|credential", re.IGNORECASE)
_EMAIL = re.compile(r"([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+)")
_PHONE = re.compile(r"(?<!\d)(\+?\d[\d\s().-]{7,}\d)(?!\d)")
_LOCK_ID = 726354981  # pg advisory lock: one writer extends the chain at a time


def mask(value: Any, depth: int = 0) -> Any:
    if depth > 6:
        return "…"
    if isinstance(value, dict):
        return {str(k)[:64]: ("[redacted]" if _SECRET_KEY.search(str(k)) else mask(v, depth + 1))
                for k, v in list(value.items())[:60]}
    if isinstance(value, (list, tuple)):
        return [mask(v, depth + 1) for v in list(value)[:60]]
    if isinstance(value, str):
        s = _EMAIL.sub(lambda m: f"{m.group(1)}***@{m.group(2)}", value[:1000])
        return _PHONE.sub(lambda m: "***" + re.sub(r"\D", "", m.group(1))[-3:], s)
    if value is None or isinstance(value, (int, float, bool)):
        return value
    return str(value)[:200]


def _canonical(row: dict[str, Any]) -> bytes:
    keys = ("seq", "at", "category", "action", "actor", "target_type", "target_id", "ip", "outcome", "source", "detail")
    return json.dumps({k: row.get(k) for k in keys}, sort_keys=True, separators=(",", ":"), default=str).encode()


def entry_hash(prev: str, row: dict[str, Any]) -> str:
    return hashlib.sha256(prev.encode() + _canonical(row)).hexdigest()


def _append(rows: list[dict[str, Any]]) -> None:
    """Append in its own short transaction (the advisory lock is held for milliseconds,
    never for the length of a business transaction)."""
    if not rows:
        return
    with _engine().begin() as conn:
        _append_rows(conn, rows)


_ENGINE: Any = None


def _engine():
    """Own tiny pool: audit writes never wait on (or starve) the request connection pool."""
    global _ENGINE
    if _ENGINE is None:
        from sqlalchemy import create_engine

        from porterchain_api.db import engine

        _ENGINE = create_engine(engine.url, pool_size=2, max_overflow=3, pool_timeout=5, pool_pre_ping=True)
    return _ENGINE


def _append_rows(conn: Any, rows: list[dict[str, Any]]) -> None:
    if conn.dialect.name == "postgresql":
        conn.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _LOCK_ID})
    last = conn.execute(select(ForensicAuditEntry.seq, ForensicAuditEntry.hash)
                        .order_by(ForensicAuditEntry.seq.desc()).limit(1)).first()
    seq, prev = (int(last[0]), last[1]) if last else (0, GENESIS)
    out = []
    for r in rows:
        seq += 1
        row = {"seq": seq, "outcome": "ok", "actor": None, "target_type": None, "target_id": None, "ip": None,
               **r, "detail": mask(r.get("detail") or {})}
        row["prev_hash"] = prev
        row["hash"] = prev = entry_hash(prev, row)
        out.append(row)
    conn.execute(insert(ForensicAuditEntry), out)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def record(db: Session | None, category: str, action: str, *, actor: str | None = None,
           target_type: str | None = None, target_id: str | None = None, ip: str | None = None,
           outcome: str = "ok", detail: dict[str, Any] | None = None) -> None:
    """Explicit security event (login, export, erasure, deploy...). Written immediately in
    its own transaction so failed / rolled-back requests are still evidenced. Never raises."""
    try:
        _append([{"at": _now(), "category": category[:32], "action": action[:128], "actor": actor,
                  "target_type": target_type, "target_id": target_id, "ip": ip, "outcome": outcome[:16],
                  "source": "event", "detail": detail or {}}])
    except Exception:
        logger.exception("forensic_record_failed action=%s", action)


def record_now(category: str, action: str, **kw: Any) -> None:
    record(None, category, action, **kw)


# ── automatic mirror of existing audit tables ──────────────────────────────────────

_AUDIT_TABLES = frozenset({"admin_audit_logs", "merchant_audit_logs", "access_audit_logs"})


def _category(action: str) -> str:
    a = action.lower()
    for key, cat in (("setting", "settings"), ("pricing", "pricing"), ("price", "pricing"), ("role", "permissions"),
                     ("permission", "permissions"), ("staff", "permissions"), ("webhook", "webhooks"),
                     ("api_key", "webhooks"), ("export", "data_export"), ("erase", "erasure"),
                     ("privacy", "privacy"), ("login", "auth"), ("session", "auth"), ("impersonat", "auth")):
        if key in a:
            return cat
    return "admin_action"


def _mirror_rows(session: Session) -> list[dict[str, Any]]:

    rows = []
    for obj in session.new:
        if getattr(obj, "__tablename__", None) in _AUDIT_TABLES:
            detail = getattr(obj, "payload", None) or getattr(obj, "detail", None) or {}
            rows.append({"at": _now(), "category": _category(obj.action), "action": obj.action,
                         "actor": obj.actor_user_id, "target_type": obj.resource_type, "target_id": obj.resource_id,
                         "outcome": getattr(obj, "outcome", None) or "ok",
                         "source": f"{obj.__tablename__}:{obj.id}"[:48],
                         "detail": {**({"merchant_id": obj.merchant_id} if hasattr(obj, "merchant_id") else {}),
                                    **(detail if isinstance(detail, dict) else {"value": detail})}})
    return rows


@event.listens_for(Session, "after_commit")
def _after_commit(session: Session) -> None:
    pending = session.info.pop("forensic_pending", None)
    if pending:
        try:
            _append(pending)
        except Exception:
            logger.exception("forensic_mirror_failed")


@event.listens_for(Session, "after_rollback")
def _after_rollback(session: Session) -> None:
    session.info.pop("forensic_pending", None)  # the audited change did not happen


@event.listens_for(Session, "before_flush")
def _before_flush(session: Session, _ctx: Any, _instances: Any) -> None:
    import uuid as _uuid


    for obj in session.new:  # ids are needed for the source reference
        if getattr(obj, "__tablename__", None) in _AUDIT_TABLES and not obj.id:
            obj.id = str(_uuid.uuid4())
    rows = _mirror_rows(session)
    if rows:
        session.info.setdefault("forensic_pending", []).extend(rows)


# ── verification, checkpoints, export ─────────────────────────────────────────────

def verify(db: Session, *, limit: int | None = None) -> dict[str, Any]:
    prev, n, first_bad = GENESIS, 0, None
    q = db.query(ForensicAuditEntry).order_by(ForensicAuditEntry.seq)
    for e in q.yield_per(2000):
        row = {c: getattr(e, c) for c in ("seq", "at", "category", "action", "actor", "target_type", "target_id",
                                          "ip", "outcome", "source", "detail")}
        if e.prev_hash != prev or entry_hash(prev, row) != e.hash or e.seq != n + 1:
            first_bad = e.seq
            break
        prev, n = e.hash, n + 1
        if limit and n >= limit:
            break
    return {"ok": first_bad is None, "entries_verified": n, "head_hash": prev, "first_bad_seq": first_bad}


def _signing_key():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    raw = (os.environ.get("AUDIT_SIGNING_KEY") or "").strip()
    if not raw:
        return None
    return Ed25519PrivateKey.from_private_bytes(base64.b64decode(raw))


def public_key_b64() -> str | None:
    from cryptography.hazmat.primitives import serialization

    k = _signing_key()
    if k is None:
        return None
    return base64.b64encode(k.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()


def checkpoint(db: Session) -> dict[str, Any]:
    """Verify the whole chain, then sign (seq, head_hash, time). Requires AUDIT_SIGNING_KEY."""
    v = verify(db)
    if not v["ok"]:
        record(db, "integrity", "audit_chain.verify_failed", outcome="error", detail=v)
        raise RuntimeError(f"audit chain broken at seq {v['first_bad_seq']}")
    key = _signing_key()
    if key is None:
        raise RuntimeError("AUDIT_SIGNING_KEY not set")
    now = datetime.now(UTC)
    msg = f"porterchain-audit|{v['entries_verified']}|{v['head_hash']}|{now.isoformat()}".encode()
    pub = public_key_b64() or ""
    cp = ForensicCheckpoint(created_at=now, seq=v["entries_verified"], head_hash=v["head_hash"],
                            key_id=hashlib.sha256(pub.encode()).hexdigest()[:16], algorithm="ed25519",
                            signature=base64.b64encode(key.sign(msg)).decode())
    db.add(cp)
    db.commit()
    return {"seq": cp.seq, "head_hash": cp.head_hash, "created_at": now.isoformat(), "key_id": cp.key_id,
            "signature": cp.signature, "public_key": pub, "message": msg.decode()}


def export(db: Session, *, since: datetime | None = None, until: datetime | None = None,
           categories: set[str] | None = None) -> dict[str, Any]:
    q = db.query(ForensicAuditEntry).order_by(ForensicAuditEntry.seq)
    out = []
    for e in q.yield_per(2000):
        if since and e.at < since.isoformat():
            continue
        if until and e.at > until.isoformat():
            continue
        if categories and e.category not in categories:
            continue
        out.append({c: getattr(e, c) for c in ("seq", "at", "category", "action", "actor", "target_type",
                                               "target_id", "ip", "outcome", "source", "detail", "prev_hash", "hash")})
    cps = [{"seq": c.seq, "head_hash": c.head_hash, "created_at": c.created_at.isoformat(), "key_id": c.key_id,
            "algorithm": c.algorithm, "signature": c.signature}
           for c in db.query(ForensicCheckpoint).order_by(ForensicCheckpoint.id).all()]
    return {"generated_at": _now(), "verification": verify(db), "public_key": public_key_b64(),
            "hash_rule": "hash = sha256(prev_hash || canonical_json(seq,at,category,action,actor,target_type,"
                         "target_id,ip,outcome,source,detail)); genesis prev_hash = 64 zeros",
            "entries": out, "checkpoints": cps}
