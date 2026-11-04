from __future__ import annotations

from fastapi.responses import Response

from porterchain_api.media_store import s3
from porterchain_api.media_store.service import is_media_key


def fetch(key: str) -> Response:
    if not is_media_key(key):
        raise LookupError("media_not_found")
    cfg = s3.config_from_env()
    if cfg is None:
        raise RuntimeError("media_storage_not_configured")
    data, ctype = s3.get_object(cfg, key)
    return Response(content=data, media_type=ctype, headers={"Cache-Control": "private, max-age=300"})
