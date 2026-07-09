"""driver routes — profile."""

from porterchain_api.routers.driver._deps import (
    Annotated,
    Depends,
    DriverContext,
    DriverOnboardingResponse,
    DriverProfileResponse,
    Session,
    Settings,
    driver_profile,
    evaluate_driver_onboarding,
    get_db,
    get_driver_context,
    get_settings,
    router,
    svc,
)


@router.get("/me", response_model=DriverProfileResponse)
def driver_me(ctx: Annotated[DriverContext, Depends(get_driver_context)]):
    return driver_profile(ctx.driver)


@router.get("/onboarding", response_model=DriverOnboardingResponse)
def driver_onboarding(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    settings: Settings = Depends(get_settings),
):
    """Onboarding checklist — portal blocks until ready."""
    return DriverOnboardingResponse(**evaluate_driver_onboarding(ctx.driver, settings=settings))


@router.get("/profile")
def driverdriver_profile(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    return svc.platform.profile.snapshot(db, ctx.driver)


