"""driver routes — identity + background verification."""

from pydantic import BaseModel, Field

from porterchain_api.db import db_transaction
from porterchain_api.driver_engine.abstract_service import DriverAbstractService
from porterchain_api.driver_engine.background_check_service import DriverBackgroundCheckService
from porterchain_api.driver_engine.verification_service import DriverVerificationService
from porterchain_api.routers.driver._deps import (
    Annotated,
    Depends,
    DriverContext,
    HTTPException,
    Session,
    Settings,
    get_db,
    get_driver_context,
    get_settings,
    router)

_verification = DriverVerificationService()
_background = DriverBackgroundCheckService()
_abstract = DriverAbstractService()


class MockIdentityCompleteRequest(BaseModel):
    session_id: str | None = None
    verified: bool = Field(default=True)


class MockBackgroundCompleteRequest(BaseModel):
    invitation_id: str | None = None
    result: str = Field(default="cleared")


@router.get("/verification/identity")
def identity_verification_status(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    settings: Settings = Depends(get_settings)):
    return _verification.status(ctx.driver, settings)


@router.post("/verification/identity/session")
def start_identity_verification_session(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)):
    try:
        with db_transaction(db):
            return _verification.start_identity_session(db, settings, ctx.driver)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/verification/identity/mock-complete")
def mock_complete_identity_verification(
    body: MockIdentityCompleteRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)):
    """Local-only: complete a mock Stripe Identity session without webhooks."""
    try:
        with db_transaction(db):
            return _verification.complete_mock_identity(
                db,
                settings,
                ctx.driver,
                session_id=body.session_id,
                verified=body.verified)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/verification/background")
def background_check_status(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)):
    return _background.status(ctx.driver, settings, db=db)


@router.post("/verification/background/start")
def start_background_check(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)):
    try:
        with db_transaction(db):
            return _background.start_screening(db, settings, ctx.driver)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/verification/background/mock-complete")
def mock_complete_background_check(
    body: MockBackgroundCompleteRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)):
    """Local-only: complete a mock Checkr screening without webhooks."""
    try:
        with db_transaction(db):
            return _background.complete_mock(
                db,
                settings,
                ctx.driver,
                invitation_id=body.invitation_id,
                result=body.result)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


class AbstractSubmitRequest(BaseModel):
    file_url: str
    license_class: str
    demerit_points: int = Field(default=0, ge=0, le=30)
    has_active_suspension: bool = False
    expires_at: str | None = None
    issued_at: str | None = None
    reference_number: str | None = None


@router.get("/verification/abstract")
def abstract_status(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    settings: Settings = Depends(get_settings)):
    return _abstract.status(ctx.driver, settings)


@router.post("/verification/abstract/submit")
def submit_abstract(
    body: AbstractSubmitRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)):
    try:
        with db_transaction(db):
            return _abstract.submit(
                db,
                settings,
                ctx.driver,
                file_url=body.file_url,
                license_class=body.license_class,
                demerit_points=body.demerit_points,
                has_active_suspension=body.has_active_suspension,
                expires_at=body.expires_at,
                issued_at=body.issued_at,
                reference_number=body.reference_number)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
