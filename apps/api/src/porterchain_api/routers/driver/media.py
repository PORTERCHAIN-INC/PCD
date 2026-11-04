"""Driver: upload proof photos and signatures to Garage; returns the stored key used by POD/batch calls."""
from fastapi import File, UploadFile
from pydantic import BaseModel, Field

from porterchain_api.driver_engine.rbac import require_approved_driver
from porterchain_api.media_store import service as M
from porterchain_api.routers.driver._deps import Annotated, Depends, DriverContext, HTTPException, get_driver_context, router

Ctx = Annotated[DriverContext, Depends(get_driver_context)]


def _err(exc: Exception) -> HTTPException:
    if isinstance(exc, RuntimeError):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, OSError):
        return HTTPException(status_code=502, detail="media_store_unavailable")
    return HTTPException(status_code=422, detail=str(exc))


def _approved(ctx: DriverContext) -> None:
    try:
        require_approved_driver(ctx)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/media/photo")
async def upload_photo(ctx: Ctx, file: UploadFile = File(...)):
    _approved(ctx)
    data = await file.read(M.MAX_PHOTO_BYTES + 1)
    try:
        return M.store_photo(str(ctx.driver.id), data)
    except (ValueError, RuntimeError, OSError) as exc:
        raise _err(exc) from exc


class SignatureBody(BaseModel):
    data_url: str = Field(min_length=30, max_length=800_000)
    signer_name: str = Field(min_length=2, max_length=120)


@router.post("/media/signature")
def upload_signature(body: SignatureBody, ctx: Ctx):
    _approved(ctx)
    try:
        return M.store_signature(str(ctx.driver.id), body.data_url, signer_name=body.signer_name)
    except (ValueError, RuntimeError, OSError) as exc:
        raise _err(exc) from exc


class PhotoDataBody(BaseModel):
    """Mobile camera output is already a compressed JPEG/PNG data URL (no EXIF); same checks as multipart."""
    data_url: str = Field(min_length=30, max_length=14_000_000)


@router.post("/media/photo-data")
def upload_photo_data(body: PhotoDataBody, ctx: Ctx):
    _approved(ctx)
    import base64
    import binascii
    import re

    m = re.match(r"^data:image/(?:jpeg|png|webp);base64,([A-Za-z0-9+/=]+)$", body.data_url)
    if not m:
        raise HTTPException(status_code=422, detail="photo_must_be_image_data_url")
    try:
        data = base64.b64decode(m.group(1), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=422, detail="photo_bad_base64") from exc
    try:
        return M.store_photo(str(ctx.driver.id), data)
    except (ValueError, RuntimeError, OSError) as exc:
        raise _err(exc) from exc
