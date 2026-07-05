"""driver routes — auth."""

from porterchain_api.routers.driver._deps import *  # noqa: F403

@router.post("/auth/login", response_model=DriverTokenResponse)
async def driver_login(
    body: DriverLoginRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: Annotated[str | None, Header()] = None,
):
    """Driver JWT login — requires Clerk bearer token in production."""
    clerk_token: str | None = None
    if authorization and authorization.startswith("Bearer "):
        clerk_token = authorization.removeprefix("Bearer ").strip()
    try:
        driver, tokens = await _svc.auth.login(
            db, settings, email=body.email, clerk_bearer_token=clerk_token
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="driver_not_found") from None
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return DriverTokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in_seconds,
        driver_id=driver.id,
    )


@router.post("/auth/refresh", response_model=DriverTokenResponse)
def driver_refresh(
    body: DriverRefreshRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    try:
        driver, tokens = _svc.auth.refresh(db, settings, refresh_token=body.refresh_token)
    except LookupError:
        raise HTTPException(status_code=404, detail="driver_not_found") from None
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return DriverTokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in_seconds,
        driver_id=driver.id,
    )


