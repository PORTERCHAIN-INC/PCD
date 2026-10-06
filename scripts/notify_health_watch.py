"""Outside probe. Run from cron on the droplet, not from the API process.

Emails OPS_WATCH_EMAILS when API readiness, the worker heartbeat, or an
optional URL is down. A dead API cannot send this itself.

  OPS_WATCH_EMAILS=ops@porterchain.com \
  HEALTH_READY_URL=https://api.porterchain.com/health/ready \
  REDIS_URL=redis://... \
  python scripts/notify_health_watch.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def _get(url: str, timeout: float = 8.0) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read(400).decode("utf-8", errors="replace")
            if response.status >= 400:
                return False, f"http_{response.status}"
            if '"status": "ok"' in body or '"status":"ok"' in body:
                return True, "ok"
            # Readiness returns checks; a non-ok database string is a failure.
            if "error:" in body or '"unavailable"' in body:
                return False, body[:240]
            return True, "ok"
    except urllib.error.HTTPError as exc:
        return False, f"http_{exc.code}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _worker_heartbeat() -> tuple[bool, str]:
    url = os.environ.get("REDIS_URL", "").strip()
    if not url:
        return True, "redis_not_configured"
    try:
        import redis

        client = redis.Redis.from_url(url)
        beat = client.get("porterchain:worker:heartbeat")
        if beat:
            return True, "ok"
        return False, "no_heartbeat"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _mail(to: list[str], subject: str, body: str) -> None:
    token = (os.environ.get("ZEPTOMAIL_TOKEN") or os.environ.get("MAIL_PASSWORD") or "").strip()
    sender = (os.environ.get("MAIL_FROM_ADDRESS") or "noreply@porterchain.com").strip()
    api = (os.environ.get("ZEPTOMAIL_API_URL") or "https://api.zeptomail.ca/v1.1/email").strip()
    if not token or not to:
        print(body)
        return
    auth = token if token.startswith("Zoho-enczapikey") else f"Zoho-enczapikey {token}"
    payload = {
        "from": {"address": sender, "name": "PorterChain"},
        "to": [{"email_address": {"address": address}} for address in to],
        "subject": subject,
        "textbody": body,
    }
    request = urllib.request.Request(
        api,
        data=json.dumps(payload).encode(),
        headers={"accept": "application/json", "authorization": auth, "content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        response.read()


def main() -> int:
    failures: list[str] = []
    ready = os.environ.get("HEALTH_READY_URL", "http://127.0.0.1:8001/health/ready")
    ok, detail = _get(ready)
    if not ok:
        failures.append(f"api {ready}: {detail}")
    for raw in os.environ.get("HEALTH_EXTRA_URLS", "").split(","):
        url = raw.strip()
        if not url:
            continue
        extra_ok, extra_detail = _get(url)
        if not extra_ok:
            failures.append(f"url {url}: {extra_detail}")
    beat_ok, beat_detail = _worker_heartbeat()
    if not beat_ok:
        failures.append(f"worker: {beat_detail}")
    if not failures:
        print("ok")
        return 0
    watchers = [part.strip() for part in os.environ.get("OPS_WATCH_EMAILS", "").split(",") if "@" in part]
    text = "PorterChain health probe\n\n" + "\n".join(failures)
    _mail(watchers, "PorterChain service down", text)
    print(text, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
