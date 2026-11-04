from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import quote

import httpx


@dataclass(frozen=True)
class S3Config:
    endpoint: str
    bucket: str
    access_key: str
    secret_key: str
    region: str = "garage"


def config_from_env() -> S3Config | None:
    e = {k: os.environ.get(f"POD_S3_{k}", "").strip() for k in ("ENDPOINT", "BUCKET", "ACCESS_KEY_ID", "SECRET_ACCESS_KEY")}
    if not all(e.values()):
        return None
    return S3Config(e["ENDPOINT"].rstrip("/"), e["BUCKET"], e["ACCESS_KEY_ID"], e["SECRET_ACCESS_KEY"],
                    os.environ.get("POD_S3_REGION", "garage").strip() or "garage")


def _hm(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


def _headers(cfg: S3Config, method: str, path: str, payload: bytes, content_type: str | None) -> dict[str, str]:
    now = datetime.now(UTC)
    amz, day = now.strftime("%Y%m%dT%H%M%SZ"), now.strftime("%Y%m%d")
    host = cfg.endpoint.split("://", 1)[-1]
    ph = hashlib.sha256(payload).hexdigest()
    h = {"host": host, "x-amz-content-sha256": ph, "x-amz-date": amz}
    if content_type:
        h["content-type"] = content_type
    names = sorted(h)
    canon = "\n".join([method, quote(path, safe="/"), "", "".join(f"{n}:{h[n]}\n" for n in names), ";".join(names), ph])
    scope = f"{day}/{cfg.region}/s3/aws4_request"
    sts = "\n".join(["AWS4-HMAC-SHA256", amz, scope, hashlib.sha256(canon.encode()).hexdigest()])
    k = _hm(_hm(_hm(_hm(("AWS4" + cfg.secret_key).encode(), day), cfg.region), "s3"), "aws4_request")
    sig = hmac.new(k, sts.encode(), hashlib.sha256).hexdigest()
    h["authorization"] = (f"AWS4-HMAC-SHA256 Credential={cfg.access_key}/{scope}, "
                          f"SignedHeaders={';'.join(names)}, Signature={sig}")
    return h


def put_object(cfg: S3Config, key: str, data: bytes, content_type: str, http: httpx.Client | None = None) -> None:
    path = f"/{cfg.bucket}/{key}"
    c = http or httpx.Client(timeout=30)
    r = c.put(cfg.endpoint + path, content=data, headers=_headers(cfg, "PUT", path, data, content_type))
    if r.status_code not in (200, 201):
        raise OSError(f"media_put_failed:{r.status_code}")


def get_object(cfg: S3Config, key: str, http: httpx.Client | None = None) -> tuple[bytes, str]:
    path = f"/{cfg.bucket}/{key}"
    c = http or httpx.Client(timeout=30)
    r = c.get(cfg.endpoint + path, headers=_headers(cfg, "GET", path, b"", None))
    if r.status_code == 404:
        raise LookupError("media_not_found")
    if r.status_code != 200:
        raise OSError(f"media_get_failed:{r.status_code}")
    return r.content, r.headers.get("content-type", "application/octet-stream")
