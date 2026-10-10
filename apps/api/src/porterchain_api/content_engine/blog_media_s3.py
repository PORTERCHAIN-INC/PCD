"""Optional S3-compatible (R2) PUT for blog media — no boto3; uses httpx + SigV4."""

from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import UTC, datetime
from urllib.parse import quote

logger = logging.getLogger(__name__)


def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _sig_key(secret: str, datestamp: str, region: str, service: str) -> bytes:
    k_date = _sign(("AWS4" + secret).encode("utf-8"), datestamp)
    k_region = _sign(k_date, region)
    k_service = _sign(k_region, service)
    return _sign(k_service, "aws4_request")


def s3_config_from_env() -> dict[str, str] | None:
    """Return S3 config when all required vars are set; else None (disk-only)."""
    import os

    endpoint = os.environ.get("BLOG_MEDIA_S3_ENDPOINT", "").strip().rstrip("/")
    bucket = os.environ.get("BLOG_MEDIA_S3_BUCKET", "").strip()
    access = os.environ.get("BLOG_MEDIA_S3_ACCESS_KEY_ID", "").strip()
    secret = os.environ.get("BLOG_MEDIA_S3_SECRET_ACCESS_KEY", "").strip()
    if not (endpoint and bucket and access and secret):
        try:
            from porterchain_api.config import get_settings

            s = get_settings()
            endpoint = (s.blog_media_s3_endpoint or "").strip().rstrip("/")
            bucket = (s.blog_media_s3_bucket or "").strip()
            access = (s.blog_media_s3_access_key_id or "").strip()
            secret = (s.blog_media_s3_secret_access_key or "").strip()
        except Exception:
            return None
    if not (endpoint and bucket and access and secret):
        return None
    import os

    region = os.environ.get("BLOG_MEDIA_S3_REGION", "").strip()
    if not region:
        try:
            from porterchain_api.config import get_settings

            region = (get_settings().blog_media_s3_region or "").strip()
        except Exception:
            region = ""
    if not region:
        region = "auto"
    prefix = os.environ.get("BLOG_MEDIA_S3_PREFIX", "").strip().strip("/")
    if not prefix:
        try:
            from porterchain_api.config import get_settings

            prefix = (get_settings().blog_media_s3_prefix or "").strip().strip("/")
        except Exception:
            prefix = ""
    if not prefix:
        prefix = "blog-media"
    return {
        "endpoint": endpoint,
        "bucket": bucket,
        "access_key": access,
        "secret_key": secret,
        "region": region,
        "prefix": prefix,
    }


def put_blog_media_object(
    *,
    filename: str,
    content: bytes,
    content_type: str,
) -> str | None:
    """
    Upload to S3/R2 when configured. Returns object key on success, None if not configured.
    Raises ValueError on upload failure when configured.
    """
    cfg = s3_config_from_env()
    if not cfg:
        return None

    key = f"{cfg['prefix']}/{filename}"
    # Virtual-hosted–style path on custom endpoint: /{bucket}/{key}
    path = f"/{cfg['bucket']}/{key}"
    host = cfg["endpoint"].removeprefix("https://").removeprefix("http://")
    url = f"{cfg['endpoint']}{path}"

    now = datetime.now(UTC)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    datestamp = now.strftime("%Y%m%d")
    payload_hash = hashlib.sha256(content).hexdigest()
    canonical_headers = (
        f"content-type:{content_type}\n"
        f"host:{host}\n"
        f"x-amz-content-sha256:{payload_hash}\n"
        f"x-amz-date:{amz_date}\n"
    )
    signed_headers = "content-type;host;x-amz-content-sha256;x-amz-date"
    canonical_request = "\n".join(
        [
            "PUT",
            quote(path, safe="/"),
            "",
            canonical_headers,
            signed_headers,
            payload_hash,
        ]
    )
    credential_scope = f"{datestamp}/{cfg['region']}/s3/aws4_request"
    string_to_sign = "\n".join(
        [
            "AWS4-HMAC-SHA256",
            amz_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )
    signing_key = _sig_key(cfg["secret_key"], datestamp, cfg["region"], "s3")
    signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    authorization = (
        f"AWS4-HMAC-SHA256 Credential={cfg['access_key']}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    headers = {
        "Content-Type": content_type,
        "Host": host,
        "x-amz-content-sha256": payload_hash,
        "x-amz-date": amz_date,
        "Authorization": authorization,
    }
    try:
        import httpx
    except ImportError as exc:
        raise ValueError("blog_media_s3_httpx_missing") from exc
    try:
        with httpx.Client(timeout=30.0) as client:
            res = client.put(url, content=content, headers=headers)
        if res.status_code not in (200, 201):
            logger.error("blog_media_s3_put_failed status=%s body=%s", res.status_code, res.text[:300])
            raise ValueError("blog_media_s3_upload_failed")
    except httpx.HTTPError as exc:
        logger.exception("blog_media_s3_http_error")
        raise ValueError("blog_media_s3_upload_failed") from exc
    return key
