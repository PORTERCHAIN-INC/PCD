#!/usr/bin/env python3
"""Repair local Fleetbase so the PorterChain permanent bond can create orders.

SSOT: docs/FLEETBASE_PERMANENT_BOND.md · operator entry: ``pnpm fleetbase:bond``.

Root cause (local): incomplete vendor migrations / missing sandbox DB grants /
empty OrderConfig / API throttle during catch-up. Payload mapping is fine —
POST /v1/orders fails before PC places matter.

SSOT path (fleetbase-install.sh §7):
  1. Ensure fleetbase_sandbox exists + fleetbase user can CREATE
  2. docker compose exec application ./deploy.sh  OR  migrate --step with
     stamp-on-duplicate for hand-patched drift (activity/comments/directives)
  3. Seed company + API credential + OrderConfig key=transport
  4. Smoke POST /v1/orders → 201
  5. Optional: replay_fleetbase_sync (requires THROTTLE_ENABLED=false locally)

Does not change MapsService / VROOM / PorterChain order payloads.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FLEETBASE_DIR = ROOT / "apps" / "fleetbase"
COMPOSE_OVERRIDE = ROOT / "infrastructure" / "docker" / "fleetbase.porterchain.override.yml"
API_ENV = ROOT / "apps" / "api" / ".env"
ENV_ENV = ROOT / "env" / ".env"

DEFAULT_COMPANY_UUID = "e136168f-516e-4b43-b6c2-ed4178169bce"
MYSQL_HOST = "127.0.0.1"
MYSQL_PORT = "3307"
MYSQL_DB = "fleetbase"
MYSQL_USER = "fleetbase"


def _info(msg: str) -> None:
    print(f"ℹ  {msg}")


def _ok(msg: str) -> None:
    print(f"✔  {msg}")


def _err(msg: str) -> None:
    print(f"✖  {msg}", file=sys.stderr)


def _read_kv(path: Path, key: str) -> str | None:
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith(f"{key}=") and not line.strip().startswith("#"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def _write_kv(path: Path, key: str, value: str) -> None:
    if not path.exists():
        path.write_text(f"{key}={value}\n", encoding="utf-8")
        return
    lines = path.read_text(encoding="utf-8").splitlines(True)
    out: list[str] = []
    found = False
    for line in lines:
        if line.startswith(f"{key}="):
            out.append(f"{key}={value}\n")
            found = True
        else:
            out.append(line)
    if not found:
        if out and not out[-1].endswith("\n"):
            out[-1] = out[-1] + "\n"
        out.append(f"{key}={value}\n")
    path.write_text("".join(out), encoding="utf-8")


def _compose_cmd(*extra: str) -> list[str]:
    return [
        "docker",
        "compose",
        "-f",
        "docker-compose.yml",
        "-f",
        "docker-compose.override.yml",
        "-f",
        str(COMPOSE_OVERRIDE),
        *extra,
    ]


def _docker_env() -> dict[str, str]:
    env = {**os.environ}
    sock = Path.home() / ".docker" / "run" / "docker.sock"
    if sock.exists():
        env["DOCKER_HOST"] = f"unix://{sock}"
    return env


def _mysql_passwords() -> tuple[str, str]:
    override = FLEETBASE_DIR / "docker-compose.override.yml"
    text = override.read_text(encoding="utf-8", errors="ignore") if override.exists() else ""
    root_m = re.search(r'MYSQL_ROOT_PASSWORD:\s*"([^"]+)"', text)
    user_m = re.search(r'MYSQL_PASSWORD:\s*"([^"]+)"', text)
    if not root_m or not user_m:
        raise SystemExit("Cannot resolve MYSQL_* passwords from apps/fleetbase/docker-compose.override.yml")
    return root_m.group(1), user_m.group(1)


def mysql(sql: str, *, password: str, user: str = MYSQL_USER, database: str = MYSQL_DB) -> str:
    env = {**os.environ, "MYSQL_PWD": password}
    cmd = [
        "mysql",
        "--protocol=TCP",
        f"-h{MYSQL_HOST}",
        f"-P{MYSQL_PORT}",
        f"-u{user}",
        database,
        "-N",
        "-e",
        sql,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or r.stdout.strip() or "mysql failed")
    return r.stdout


def ensure_sandbox_grants(root_password: str) -> None:
    mysql(
        """
CREATE DATABASE IF NOT EXISTS fleetbase_sandbox CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON fleetbase.* TO 'fleetbase'@'%';
GRANT ALL PRIVILEGES ON fleetbase_sandbox.* TO 'fleetbase'@'%';
GRANT CREATE ON *.* TO 'fleetbase'@'%';
FLUSH PRIVILEGES;
""",
        password=root_password,
        user="root",
        database="mysql",
    )
    _ok("fleetbase_sandbox + CREATE grants OK")


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'")


def ensure_company_and_credential(password: str, company_uuid: str) -> str:
    import httpx

    existing = _read_kv(API_ENV, "FLEETBASE_API_KEY") or ""
    if existing.startswith("flb_"):
        try:
            r = httpx.get(
                "http://127.0.0.1:8000/v1/orders",
                params={"limit": 1},
                headers={"Authorization": f"Bearer {existing}"},
                timeout=10,
            )
            if r.status_code == 200:
                _ok("Existing FLEETBASE_API_KEY authenticates")
                return existing
        except Exception:
            pass

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    user_uuid = str(uuid.uuid4())
    cred_uuid = str(uuid.uuid4())
    cu_uuid = str(uuid.uuid4())
    raw = secrets.token_urlsafe(12).replace("-", "").replace("_", "")[:16]
    api_key = f"flb_live_{raw}"
    secret = "$2y$10$" + secrets.token_hex(26)

    mysql(f"DELETE FROM api_credentials WHERE company_uuid='{company_uuid}';", password=password)
    mysql(f"DELETE FROM company_users WHERE company_uuid='{company_uuid}';", password=password)
    mysql(f"DELETE FROM users WHERE company_uuid='{company_uuid}';", password=password)
    n = mysql(f"SELECT COUNT(*) FROM companies WHERE uuid='{company_uuid}';", password=password).strip()
    if n == "0":
        mysql(
            f"""
INSERT INTO companies (uuid, public_id, name, currency, country, timezone, status, type, slug, created_at, updated_at)
VALUES ('{company_uuid}', 'company_{company_uuid[:8]}', 'PorterChain', 'CAD', 'CA',
        'America/Toronto', 'active', 'vendor', 'porterchain', '{now}', '{now}');
""",
            password=password,
        )
    mysql(
        f"""
INSERT INTO users (uuid, public_id, company_uuid, username, email, password, name, type, status,
                   email_verified_at, created_at, updated_at)
VALUES ('{user_uuid}', 'user_{user_uuid[:8]}', '{company_uuid}', 'porterchain_ops',
        'ops@porterchain.local', '{_esc(secret)}', 'PorterChain Ops', 'admin', 'active',
        '{now}', '{now}', '{now}');
""",
        password=password,
    )
    mysql(f"UPDATE companies SET owner_uuid='{user_uuid}' WHERE uuid='{company_uuid}';", password=password)
    mysql(
        f"""
INSERT INTO company_users (uuid, company_uuid, user_uuid, status, created_at, updated_at)
VALUES ('{cu_uuid}', '{company_uuid}', '{user_uuid}', 'active', '{now}', '{now}');
""",
        password=password,
    )
    mysql(
        f"""
INSERT INTO api_credentials (uuid, user_uuid, company_uuid, name, `key`, secret, test_mode, created_at, updated_at)
VALUES ('{cred_uuid}', '{user_uuid}', '{company_uuid}', 'PorterChain Local Bridge',
        '{_esc(api_key)}', '{_esc(secret)}', 0, '{now}', '{now}');
""",
        password=password,
    )
    _write_kv(API_ENV, "FLEETBASE_API_KEY", api_key)
    _write_kv(API_ENV, "FLEETBASE_DEFAULT_COMPANY_UUID", company_uuid)
    if ENV_ENV.exists():
        _write_kv(ENV_ENV, "FLEETBASE_API_KEY", api_key)
        _write_kv(ENV_ENV, "PORTERCHAIN_FLEETBASE_DEFAULT_COMPANY_UUID", company_uuid)
    _ok(f"Bootstrapped company + API credential (key_len={len(api_key)})")
    return api_key


def ensure_transport_order_config(password: str, company_uuid: str) -> None:
    n = mysql(
        f"SELECT COUNT(*) FROM order_configs WHERE company_uuid='{company_uuid}' AND `key`='transport' AND deleted_at IS NULL",
        password=password,
    ).strip()
    if n != "0":
        # Prefer FleetOps-shaped flow (Activity needs array attrs). If a private
        # transport config exists with nested activities, copy onto published.
        try:
            mysql(
                f"""
UPDATE order_configs pub
JOIN order_configs priv
  ON priv.company_uuid = pub.company_uuid
 AND priv.`key` = 'transport'
 AND priv.status = 'private'
 AND priv.deleted_at IS NULL
SET pub.flow = priv.flow, pub.status = 'published'
WHERE pub.company_uuid = '{company_uuid}'
  AND pub.`key` = 'transport'
  AND pub.status = 'published'
  AND pub.deleted_at IS NULL
  AND JSON_TYPE(JSON_EXTRACT(pub.flow, '$.created')) = 'STRING'
""",
                password=password,
            )
        except RuntimeError:
            pass
        mysql(
            f"UPDATE order_configs SET status='published' WHERE company_uuid='{company_uuid}' AND `key`='transport' AND deleted_at IS NULL AND status!='published' LIMIT 5",
            password=password,
        )
        _ok("OrderConfig key=transport present (published)")
        return
    author = mysql(f"SELECT owner_uuid FROM companies WHERE uuid='{company_uuid}';", password=password).strip()
    if not author:
        raise RuntimeError("company has no owner_uuid")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    oc_uuid = str(uuid.uuid4())
    # Minimal FleetOps Activity-shaped flow (strings break Activity::__construct).
    created = {
        "key": "created",
        "code": "created",
        "color": "#1f2937",
        "logic": [],
        "events": [],
        "status": "Order Created",
        "actions": [],
        "details": "New order was created.",
        "options": [],
        "complete": False,
        "entities": [],
        "sequence": 0,
        "activities": ["dispatched"],
    }
    dispatched = {
        **created,
        "key": "dispatched",
        "code": "dispatched",
        "status": "Order Dispatched",
        "details": "Order was dispatched.",
        "sequence": 1,
        "activities": ["completed"],
    }
    completed = {
        **created,
        "key": "completed",
        "code": "completed",
        "status": "Order Completed",
        "details": "Order completed.",
        "complete": True,
        "sequence": 2,
        "activities": [],
    }
    flow = json.dumps({"created": created, "dispatched": dispatched, "completed": completed})
    mysql(
        f"""
INSERT INTO order_configs
 (uuid, public_id, company_uuid, author_uuid, name, namespace, description, `key`, status, version,
  core_service, flow, entities, tags, meta, created_at, updated_at)
VALUES (
  '{oc_uuid}', 'order_config_transport', '{company_uuid}', '{author}',
  'Transport', 'fleet-ops', 'Default PorterChain transport order config',
  'transport', 'published', '0.0.1', 1,
  '{_esc(flow)}', JSON_ARRAY(), JSON_ARRAY(), JSON_OBJECT('porterchain', true),
  '{now}', '{now}'
);
""",
        password=password,
    )
    _ok("Seeded OrderConfig key=transport (Activity-shaped flow)")


def stamp_migration(root_password: str, migration: str) -> None:
    batch = mysql(
        "SELECT COALESCE(MAX(batch),0)+1 FROM migrations",
        password=root_password,
        user="root",
    ).strip()
    mysql(
        f"INSERT IGNORE INTO migrations (migration, batch) VALUES ('{_esc(migration)}', {batch})",
        password=root_password,
        user="root",
    )
    _info(f"Stamped drift migration {migration} (batch={batch})")


def _parse_failed_migration(out: str) -> str | None:
    m = re.search(r"Migrating:\s+([0-9]{4}_[0-9a-z_]+)", out)
    if m:
        return m.group(1)
    m = re.search(r"^\s*([0-9]{4}_[0-9]{2}_[0-9]{2}_[0-9]{6}_[a-z0-9_]+)\s+.*FAIL", out, re.M)
    if m:
        return m.group(1)
    m = re.search(r"([0-9]{4}_[0-9]{2}_[0-9]{2}_[0-9]{6}_[a-z0-9_]+).*FAIL", out)
    return m.group(1) if m else None


def migrate_with_drift_stamp(root_password: str, *, max_steps: int = 200) -> bool:
    env = _docker_env()
    for step in range(1, max_steps + 1):
        r = subprocess.run(
            _compose_cmd("exec", "-T", "application", "bash", "-c", "php artisan migrate --force --step"),
            cwd=str(FLEETBASE_DIR),
            capture_output=True,
            text=True,
            env=env,
            timeout=180,
        )
        out = (r.stdout or "") + (r.stderr or "")
        if "Nothing to migrate" in out:
            _ok(f"Migrations complete (after {step - 1} steps)")
            return True
        if r.returncode == 0 and "FAIL" not in out:
            continue
        if re.search(r"Duplicate column|already exists|Duplicate key name", out, re.I):
            mig = _parse_failed_migration(out)
            if not mig:
                _err("Duplicate drift but could not parse migration name")
                print(out[-1500:])
                return False
            stamp_migration(root_password, mig)
            continue
        _err(f"Non-drift migrate failure at step {step}")
        print(out[-2000:])
        return False
    _err(f"Exceeded {max_steps} migrate steps")
    return False


def try_deploy_sh() -> bool:
    _info("Trying docker compose exec application ./deploy.sh …")
    r = subprocess.run(
        _compose_cmd("exec", "-T", "application", "bash", "-c", "./deploy.sh"),
        cwd=str(FLEETBASE_DIR),
        capture_output=True,
        text=True,
        env=_docker_env(),
        timeout=900,
    )
    if r.returncode == 0:
        _ok("deploy.sh completed")
        return True
    _info(f"deploy.sh failed — will migrate --step: {(r.stderr or r.stdout or '')[:200].strip()}")
    return False


def smoke_post(api_key: str, company_uuid: str) -> bool:
    import httpx

    payload = {
        "type": "transport",
        "company_uuid": company_uuid,
        "internal_id": f"pc-repair-{uuid.uuid4().hex[:8]}",
        "pickup": {
            "name": "1 King St W",
            "street1": "1 King St W",
            "city": "Toronto",
            "province": "ON",
            "postal_code": "M5H1A1",
            "country": "CA",
            "location": {"type": "Point", "coordinates": [-79.3817, 43.6488]},
        },
        "dropoff": {
            "name": "2 Bay St",
            "street1": "2 Bay St",
            "city": "Toronto",
            "province": "ON",
            "postal_code": "M5J2R8",
            "country": "CA",
            "location": {"type": "Point", "coordinates": [-79.3797, 43.6476]},
        },
        "meta": {"porterchain_repair": True},
    }
    r = httpx.post(
        "http://127.0.0.1:8000/v1/orders",
        json=payload,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30,
    )
    if r.status_code in {200, 201}:
        _ok(f"POST /v1/orders → {r.status_code}")
        return True
    _err(f"POST /v1/orders → {r.status_code}: {r.text[:400]}")
    return False


def recreate_application_for_throttle() -> None:
    """Pick up THROTTLE_ENABLED=false from porterchain override."""
    _info("Recreating application to load THROTTLE_ENABLED=false …")
    r = subprocess.run(
        _compose_cmd("up", "-d", "--force-recreate", "application"),
        cwd=str(FLEETBASE_DIR),
        capture_output=True,
        text=True,
        env=_docker_env(),
        timeout=180,
    )
    if r.returncode != 0:
        _info(f"recreate skipped: {(r.stderr or r.stdout)[:200]}")
        return
    subprocess.run(
        _compose_cmd("exec", "-T", "application", "bash", "-c", "php artisan config:clear; php artisan cache:clear"),
        cwd=str(FLEETBASE_DIR),
        capture_output=True,
        text=True,
        env=_docker_env(),
        timeout=60,
    )
    _ok("application recreated + config cleared")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-docker", action="store_true")
    parser.add_argument("--skip-recreate", action="store_true", help="Do not recreate application for throttle env")
    parser.add_argument(
        "--company-uuid",
        default=_read_kv(API_ENV, "FLEETBASE_DEFAULT_COMPANY_UUID") or DEFAULT_COMPANY_UUID,
    )
    parser.add_argument("--replay", action="store_true")
    parser.add_argument("--target-pct", type=float, default=90.0)
    args = parser.parse_args()

    root_pw, user_pw = _mysql_passwords()
    ensure_sandbox_grants(root_pw)

    tables = int(
        mysql(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE()",
            password=user_pw,
        ).strip()
    )
    _ok(f"MySQL reachable ({tables} tables in {MYSQL_DB})")

    if not args.skip_docker:
        if not try_deploy_sh():
            if not migrate_with_drift_stamp(root_pw):
                return 1
        # seed / permissions best-effort
        subprocess.run(
            _compose_cmd(
                "exec",
                "-T",
                "application",
                "bash",
                "-c",
                "php artisan fleetbase:seed || true; php artisan fleetbase:create-permissions || true; php artisan cache:clear || true",
            ),
            cwd=str(FLEETBASE_DIR),
            env=_docker_env(),
            timeout=300,
        )

    if not args.skip_recreate and not args.skip_docker:
        recreate_application_for_throttle()

    api_key = ensure_company_and_credential(user_pw, args.company_uuid)
    ensure_transport_order_config(user_pw, args.company_uuid)

    if not smoke_post(api_key, args.company_uuid):
        return 1

    if args.replay:
        env = {
            **os.environ,
            "PYTHONPATH": "src:../../shared/python:../../services/python:../../services/fleetbase-adapter:"
            "../../services/pricing-engine:../../services/event-bus:../../services/driver-platform",
        }
        r = subprocess.run(
            [
                str(ROOT / "apps" / "api" / ".venv" / "bin" / "python"),
                "scripts/replay_fleetbase_sync.py",
                "--requeue-all",
                "--max-rounds",
                "80",
                "--round-sleep",
                "1.5",
                "--target-pct",
                str(args.target_pct),
            ],
            cwd=str(ROOT / "apps" / "api"),
            env=env,
            timeout=3600,
        )
        return r.returncode

    _ok("Fleetbase local repair complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
