"""admin routes — pricing."""

from porterchain_api.routers.admin._deps import (
    AdminContext,
    Annotated,
    Depends,
    FuelConfigRequest,
    HTTPException,
    Merchant,
    MerchantContractCreateRequest,
    MerchantContractItem,
    PricingBreakdownResponse,
    PricingDashboardResponse,
    PricingFilters,
    PricingSimulatorRequest,
    PricingZoneCreateRequest,
    PricingZoneItem,
    PromotionCreateRequest,
    PromotionItem,
    Session,
    TariffCreateRequest,
    TariffItem,
    TariffUpdateRequest,
    TaxConfigRequest,
    _pricing,
    get_admin_context,
    get_db,
    require_module,
    router,
)


@router.get("/pricing/dashboard", response_model=PricingDashboardResponse)
def pricing_dashboard(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> PricingDashboardResponse:
    require_module(ctx, "pricing_read")
    return PricingDashboardResponse(**_pricing.dashboard(db))


@router.get("/pricing/reports")
def pricing_reports(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "pricing_read")
    return _pricing.reports(db)


@router.get("/pricing/conflicts")
def pricing_conflicts(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> list[dict]:
    require_module(ctx, "pricing_read")
    return _pricing.detect_conflicts(db)


@router.get("/pricing/tariffs", response_model=list[TariffItem])
def list_tariffs(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    tariff_type: str | None = None,
    vehicle_class: str | None = None,
    merchant_id: str | None = None,
    zone: str | None = None,
    status: str | None = None,
    search: str | None = None,
    include_inactive: bool = False,
) -> list[TariffItem]:
    require_module(ctx, "pricing_read")
    filters = PricingFilters(
        tariff_type=tariff_type,
        vehicle_class=vehicle_class,
        merchant_id=merchant_id,
        zone=zone,
        status=status,
        search=search,
        include_inactive=include_inactive,
    )
    return [TariffItem(**row) for row in _pricing.list_tariffs_enriched(db, filters)]


@router.post("/pricing/tariffs", response_model=TariffItem)
def create_tariff(
    body: TariffCreateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> TariffItem:
    require_module(ctx, "pricing")
    t = _pricing.create_tariff(db, ctx, **body.model_dump())
    merchants = {m.id: m.company_name for m in db.query(Merchant).all()}
    meta = dict((t.config or {}).get("_meta") or {})
    return TariffItem(**_pricing._tariff_row(t, merchants, meta, meta.get("status", "draft")))


@router.patch("/pricing/tariffs/{tariff_id}", response_model=TariffItem)
def update_tariff(
    tariff_id: str,
    body: TariffUpdateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> TariffItem:
    require_module(ctx, "pricing")
    try:
        t = _pricing.update_tariff(db, ctx, tariff_id, **body.model_dump(exclude_none=True))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    merchants = {m.id: m.company_name for m in db.query(Merchant).all()}
    meta = dict((t.config or {}).get("_meta") or {})
    return TariffItem(**_pricing._tariff_row(t, merchants, meta, meta.get("status", "published")))


@router.post("/pricing/tariffs/{tariff_id}/publish", response_model=TariffItem)
def publish_tariff(
    tariff_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> TariffItem:
    require_module(ctx, "pricing")
    try:
        t = _pricing.publish_tariff(db, ctx, tariff_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    merchants = {m.id: m.company_name for m in db.query(Merchant).all()}
    meta = dict((t.config or {}).get("_meta") or {})
    return TariffItem(**_pricing._tariff_row(t, merchants, meta, "published"))


@router.get("/pricing/promotions", response_model=list[PromotionItem])
def list_promotions(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> list[PromotionItem]:
    require_module(ctx, "pricing_read")
    return [PromotionItem(**row) for row in _pricing.list_promotions_enriched(db)]


@router.post("/pricing/promotions", response_model=PromotionItem)
def create_promotion(
    body: PromotionCreateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> PromotionItem:
    require_module(ctx, "pricing")
    p = _pricing.create_promotion(db, ctx, body.code, **body.model_dump(exclude={"code"}))
    row = next((r for r in _pricing.list_promotions_enriched(db) if r["id"] == p.id), None)
    if row:
        return PromotionItem(**row)
    return PromotionItem(
        id=p.id, code=p.code, promotion_type=p.promotion_type, merchant_id=p.merchant_id,
        discount_percent=p.discount_percent, discount_cents=p.discount_cents, is_active=p.is_active,
    )


@router.get("/pricing/zones", response_model=list[PricingZoneItem])
def list_pricing_zones(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> list[PricingZoneItem]:
    require_module(ctx, "pricing_read")
    return [PricingZoneItem(**row) for row in _pricing.list_zones_enriched(db)]


@router.post("/pricing/zones", response_model=PricingZoneItem)
def create_pricing_zone(
    body: PricingZoneCreateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> PricingZoneItem:
    require_module(ctx, "pricing")
    z = _pricing.create_zone(db, ctx, **body.model_dump())
    return PricingZoneItem(
        id=z.id, code=z.code, name=z.name, multiplier=z.multiplier, is_active=z.is_active,
        bounds=dict(z.bounds or {}), created_at=z.created_at,
    )


@router.get("/pricing/contracts", response_model=list[MerchantContractItem])
def list_merchant_contracts(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    merchant_id: str | None = None,
) -> list[MerchantContractItem]:
    require_module(ctx, "pricing_read")
    return [MerchantContractItem(**row) for row in _pricing.list_contracts_enriched(db, merchant_id=merchant_id)]


@router.post("/pricing/contracts", response_model=MerchantContractItem)
def create_merchant_contract(
    body: MerchantContractCreateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> MerchantContractItem:
    require_module(ctx, "pricing")
    c = _pricing.create_contract(db, ctx, **body.model_dump())
    row = next((r for r in _pricing.list_contracts_enriched(db) if r["id"] == c.id), None)
    if row:
        return MerchantContractItem(**row)
    return MerchantContractItem(
        id=c.id, merchant_id=c.merchant_id, name=c.name,
        minimum_monthly_commitment_cents=c.minimum_monthly_commitment_cents, is_active=c.is_active,
    )


@router.post("/pricing/simulate", response_model=PricingBreakdownResponse)
def simulate_pricing(
    body: PricingSimulatorRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> PricingBreakdownResponse:
    require_module(ctx, "pricing")
    result = _pricing.simulate(db, body.model_dump())
    return PricingBreakdownResponse(**result)


@router.get("/pricing/tax")
def get_tax_config(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "pricing_read")
    return _pricing.get_tax_config(db)


@router.put("/pricing/tax")
def update_tax_config(
    body: TaxConfigRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "pricing")
    return _pricing.update_tax_config(db, ctx, body.model_dump())


@router.get("/pricing/fuel")
def get_fuel_config(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "pricing_read")
    return _pricing.get_fuel_config(db)


@router.put("/pricing/fuel")
def update_fuel_config(
    body: FuelConfigRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "pricing")
    return _pricing.update_fuel_config(db, ctx, body.model_dump())


