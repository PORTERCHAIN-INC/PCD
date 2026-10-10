"""driver routes — profile."""

from porterchain_api.routers.driver._deps import (
    Annotated,
    Depends,
    DriverContext,
    DriverOnboardingResponse,
    DriverProfileResponse,
    Session,
    Settings,
    evaluate_driver_onboarding,
    get_db,
    get_driver_context,
    get_settings,
    router,
    svc,
)
from porterchain_api.routers.driver._deps import driver_profile as map_driver_profile


@router.get("/me", response_model=DriverProfileResponse)
def driver_me(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db)):
    from porterchain_api.driver_engine.wallet_ledger import wallet_balance_cents

    # Alias import — local `driver_profile` route below must not shadow the mapper.
    return map_driver_profile(
        ctx.driver,
        wallet_cents=wallet_balance_cents(db, ctx.driver.id, cached_cents=ctx.driver.wallet_balance_cents))


@router.get("/onboarding", response_model=DriverOnboardingResponse)
def driver_onboarding(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)):
    """Onboarding checklist — portal blocks until ready. Expiry revokes flags first."""
    from porterchain_api.driver_engine.compliance_expiry_service import (
        DriverComplianceExpiryService,
    )

    DriverComplianceExpiryService().refresh_and_commit(db, ctx.driver)
    return DriverOnboardingResponse(**evaluate_driver_onboarding(ctx.driver, settings=settings))


@router.get("/profile")
def driver_profile(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db)):
    from porterchain_api.driver_engine.compliance_expiry_service import (
        DriverComplianceExpiryService,
    )

    changed = DriverComplianceExpiryService().refresh_and_commit(db, ctx.driver)
    return svc.platform.profile.snapshot(db, ctx.driver)


