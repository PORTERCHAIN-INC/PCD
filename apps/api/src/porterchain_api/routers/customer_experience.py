"""Public recipient experience: branded tracking payload + signed self-service link.

``/v1/orders/{n}/experience`` is public (tracking number only, privacy-safe).
``/v1/delivery-manage/*`` requires the signed, expiring token from a recipient
notification in the ``X-Manage-Token`` header.
"""

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from porterchain_api.config import Settings, get_settings
from porterchain_api.customer_experience import service as cx
from porterchain_api.db import get_db

router = APIRouter(prefix="/v1", tags=["customer-experience"])


class ScheduleRequest(BaseModel):
    window_code: str = Field(min_length=3, max_length=40)


class InstructionsRequest(BaseModel):
    gate_code: str | None = Field(default=None, max_length=64)
    buzzer: str | None = Field(default=None, max_length=64)
    safe_place: str | None = Field(default=None, max_length=240)
    notes: str | None = Field(default=None, max_length=560)


def _call(fn, *args) -> Any:
    try:
        return fn(*args)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=cx.ERROR_COPY["order_not_found"]) from exc
    except ValueError as exc:
        code = str(exc)
        if code not in cx.ERROR_STATUS:
            raise HTTPException(status_code=400, detail="That change could not be saved.") from exc
        raise HTTPException(
            status_code=cx.ERROR_STATUS[code], detail={"code": code, "message": cx.ERROR_COPY[code]}
        ) from exc


@router.get("/orders/{tracking_number}/experience")
def get_order_experience(
    tracking_number: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_manage_token: str | None = Header(default=None),
) -> dict[str, Any]:
    """Branded timeline / ETA window / stops away / POD summary (``enhanced: false`` when off)."""
    return _call(cx.experience, db, settings, tracking_number, x_manage_token)


@router.get("/delivery-manage/{tracking_number}")
def get_manage_options(
    tracking_number: str,
    x_manage_token: str = Header(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    return _call(cx.manage_options, db, settings, tracking_number, x_manage_token)


@router.post("/delivery-manage/{tracking_number}/schedule")
def post_manage_schedule(
    tracking_number: str,
    body: ScheduleRequest,
    x_manage_token: str = Header(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    return _call(cx.manage_schedule, db, settings, tracking_number, x_manage_token, body.window_code)


@router.post("/delivery-manage/{tracking_number}/instructions")
def post_manage_instructions(
    tracking_number: str,
    body: InstructionsRequest,
    x_manage_token: str = Header(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    return _call(cx.manage_instructions, db, settings, tracking_number, x_manage_token, body.model_dump())


@router.get("/delivery-manage/{tracking_number}/pod")
def get_manage_pod(
    tracking_number: str,
    x_manage_token: str = Header(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    return _call(cx.manage_pod, db, settings, tracking_number, x_manage_token)
