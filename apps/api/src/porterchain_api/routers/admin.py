"""Admin operations API — /v1/admin/*"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.claims_service import AdminClaimsService
from porterchain_api.admin_engine.crm_service import AdminCrmService
from porterchain_api.admin_engine.dashboard_service import AdminDashboardService
from porterchain_api.admin_engine.driver_service import AdminDriverService
from porterchain_api.admin_engine.finance_service import AdminFinanceService
from porterchain_api.admin_engine.merchant_service import AdminMerchantService
from porterchain_api.admin_engine.operations_service import AdminOperationsService
from porterchain_api.admin_engine.orders_service import AdminOrdersService
from porterchain_api.admin_engine.pricing_service import AdminPricingService
from porterchain_api.admin_engine.rbac import AdminContext, require_module
from porterchain_api.admin_engine.reports_service import AdminReportsService
from porterchain_api.admin_engine.settings_service import AdminSettingsService
from porterchain_api.admin_engine.support_service import AdminSupportService
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.models import Order
from porterchain_api.schemas_admin import (
    AdminDashboardResponse,
    AssignDriverRequest,
    ClaimCreateRequest,
    ClaimItem,
    CrmNoteCreateRequest,
    CrmSummaryResponse,
    CrmTaskCreateRequest,
    DriverItem,
    DriverVerifyRequest,
    LeadItem,
    MerchantAdminItem,
    MerchantUpdateRequest,
    OrderAdminItem,
    ReportsSummaryResponse,
    StaffItem,
    StaffRoleUpdateRequest,
    TariffCreateRequest,
    TariffItem,
    TicketCreateRequest,
    TicketItem,
    PromotionItem,
    PromotionCreateRequest,
    PricingZoneItem,
    PricingZoneCreateRequest,
    MerchantContractItem,
    MerchantContractCreateRequest,
    PricingSimulatorRequest,
    PricingBreakdownResponse,
    TaxConfigRequest,
    FuelConfigRequest,
)

router = APIRouter(prefix="/v1/admin", tags=["admin"])

_dashboard = AdminDashboardService()
_crm = AdminCrmService()
_merchants = AdminMerchantService()
_drivers = AdminDriverService()
_ops = AdminOperationsService()
_orders = AdminOrdersService()
_claims = AdminClaimsService()
_pricing = AdminPricingService()
_finance = AdminFinanceService()
_support = AdminSupportService()
_reports = AdminReportsService()
_settings = AdminSettingsService()


def _perm(exc: PermissionError) -> None:
    raise HTTPException(status_code=403, detail=str(exc)) from exc


def _order_item(o: Order) -> OrderAdminItem:
    return OrderAdminItem(
        order_id=o.id,
        order_number=o.order_number,
        tracking_number=o.tracking_number,
        state=o.state,
        amount_cents=o.amount_cents,
        currency=o.currency,
        merchant_id=o.merchant_id,
        customer_id=o.customer_id,
        scheduled_at=o.scheduled_at,
        pickup=o.pickup,
        dropoff=o.dropoff,
        created_at=o.created_at,
    )


@router.get("/dashboard", response_model=AdminDashboardResponse)
def admin_dashboard(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> AdminDashboardResponse:
    require_module(ctx, "dashboard")
    return AdminDashboardResponse(**_dashboard.get_dashboard(db))


@router.get("/crm/summary", response_model=CrmSummaryResponse)
def crm_summary(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> CrmSummaryResponse:
    try:
        require_module(ctx, "crm_read")
        return CrmSummaryResponse(**_crm.pipeline_summary(db))
    except PermissionError as e:
        _perm(e)


@router.get("/crm/leads", response_model=list[LeadItem])
def crm_leads(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> list[LeadItem]:
    require_module(ctx, "crm_read")
    return [
        LeadItem(
            id=l.id, source=l.source, email=l.email, phone=l.phone, stage=l.stage,
            quote_id=l.quote_id, created_at=l.created_at,
        )
        for l in _crm.list_leads(db)
    ]


@router.post("/crm/tasks")
def crm_create_task(
    body: CrmTaskCreateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "crm")
    return _crm.create_task(db, ctx, title=body.title, lead_id=body.lead_id, merchant_id=body.merchant_id)


@router.post("/crm/notes")
def crm_create_note(
    body: CrmNoteCreateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "crm")
    return _crm.add_note(db, ctx, entity_type=body.entity_type, entity_id=body.entity_id, body=body.body)


@router.get("/merchants", response_model=list[MerchantAdminItem])
def list_merchants(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    status: str | None = None,
) -> list[MerchantAdminItem]:
    require_module(ctx, "merchants_read")
    rows = _merchants.list_merchants(db, status=status)
    return [
        MerchantAdminItem(
            id=m.id, status=m.status, company_name=m.company_name, email=m.email,
            payment_terms=m.payment_terms, created_at=m.created_at,
        )
        for m in rows
    ]


@router.post("/merchants/{merchant_id}/approve", response_model=MerchantAdminItem)
def approve_merchant(
    merchant_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> MerchantAdminItem:
    try:
        require_module(ctx, "merchants")
        m = _merchants.approve_merchant(db, ctx, merchant_id)
        return MerchantAdminItem(
            id=m.id, status=m.status, company_name=m.company_name, email=m.email,
            payment_terms=m.payment_terms, created_at=m.created_at,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="merchant_not_found") from None
    except PermissionError as e:
        _perm(e)


@router.post("/merchants/{merchant_id}/suspend", response_model=MerchantAdminItem)
def suspend_merchant(
    merchant_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> MerchantAdminItem:
    try:
        require_module(ctx, "merchants")
        m = _merchants.suspend_merchant(db, ctx, merchant_id)
        return MerchantAdminItem(
            id=m.id, status=m.status, company_name=m.company_name, email=m.email,
            payment_terms=m.payment_terms, created_at=m.created_at,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="merchant_not_found") from None


@router.patch("/merchants/{merchant_id}", response_model=MerchantAdminItem)
def update_merchant(
    merchant_id: str,
    body: MerchantUpdateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> MerchantAdminItem:
    require_module(ctx, "merchants")
    m = _merchants.update_merchant_terms(
        db, ctx, merchant_id,
        payment_terms=body.payment_terms,
        pricing_config=body.pricing_config,
        credit_limit_cents=body.credit_limit_cents,
    )
    return MerchantAdminItem(
        id=m.id, status=m.status, company_name=m.company_name, email=m.email,
        payment_terms=m.payment_terms, created_at=m.created_at,
    )


@router.get("/drivers", response_model=list[DriverItem])
def list_drivers(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    status: str | None = None,
) -> list[DriverItem]:
    require_module(ctx, "drivers_read")
    return [
        DriverItem(
            id=d.id, status=d.status, full_name=d.full_name, email=d.email, phone=d.phone,
            license_verified=d.license_verified, insurance_verified=d.insurance_verified,
            vehicle_verified=d.vehicle_verified, background_check_status=d.background_check_status,
            rating=d.rating, is_online=d.is_online, wallet_balance_cents=d.wallet_balance_cents,
            created_at=d.created_at,
        )
        for d in _drivers.list_drivers(db, status=status)
    ]


@router.post("/drivers/{driver_id}/approve", response_model=DriverItem)
def approve_driver(
    driver_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_module(ctx, "drivers")
    d = _drivers.approve_driver(db, ctx, driver_id, settings)
    return DriverItem(
        id=d.id, status=d.status, full_name=d.full_name, email=d.email, phone=d.phone,
        license_verified=d.license_verified, insurance_verified=d.insurance_verified,
        vehicle_verified=d.vehicle_verified, background_check_status=d.background_check_status,
        rating=d.rating, is_online=d.is_online, wallet_balance_cents=d.wallet_balance_cents,
        created_at=d.created_at,
    )


@router.patch("/drivers/{driver_id}/verification", response_model=DriverItem)
def verify_driver(
    driver_id: str,
    body: DriverVerifyRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "drivers")
    d = _drivers.update_verification(db, ctx, driver_id, **body.model_dump(exclude_unset=True))
    return DriverItem(
        id=d.id, status=d.status, full_name=d.full_name, email=d.email, phone=d.phone,
        license_verified=d.license_verified, insurance_verified=d.insurance_verified,
        vehicle_verified=d.vehicle_verified, background_check_status=d.background_check_status,
        rating=d.rating, is_online=d.is_online, wallet_balance_cents=d.wallet_balance_cents,
        created_at=d.created_at,
    )


@router.get("/dispatch/queue", response_model=list[OrderAdminItem])
def dispatch_queue(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> list[OrderAdminItem]:
    require_module(ctx, "dispatch_read")
    return [_order_item(o) for o in _ops.dispatch_queue(db)]


@router.post("/dispatch/orders/{order_id}/assign", response_model=OrderAdminItem)
def assign_driver(
    order_id: str,
    body: AssignDriverRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> OrderAdminItem:
    require_module(ctx, "dispatch")
    o = _ops.assign_driver(db, settings, ctx, order_id, body.driver_id)
    return _order_item(o)


@router.get("/map/live")
def live_map(ctx: Annotated[AdminContext, Depends(get_admin_context)], db: Session = Depends(get_db)):
    require_module(ctx, "map")
    return _ops.live_map_snapshot(db)


@router.get("/orders", response_model=list[OrderAdminItem])
def list_orders(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    state: str | None = None,
    search: str | None = None,
) -> list[OrderAdminItem]:
    require_module(ctx, "orders_read")
    return [_order_item(o) for o in _orders.list_orders(db, state=state, search=search)]


@router.get("/orders/{order_id}/timeline")
def order_timeline(
    order_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "orders_read")
    events = _orders.order_timeline(db, order_id)
    return [
        {
            "event_type": e.event_type,
            "from_state": e.from_state,
            "to_state": e.to_state,
            "occurred_at": e.occurred_at.isoformat(),
            "payload": e.payload,
        }
        for e in events
    ]


@router.get("/claims", response_model=list[ClaimItem])
def list_claims(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    status: str | None = None,
) -> list[ClaimItem]:
    require_module(ctx, "claims_read")
    return [
        ClaimItem(
            id=c.id, order_id=c.order_id, claim_type=c.claim_type, status=c.status,
            description=c.description, created_at=c.created_at,
        )
        for c in _claims.list_claims(db, status=status)
    ]


@router.post("/claims", response_model=ClaimItem)
def create_claim(
    body: ClaimCreateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> ClaimItem:
    require_module(ctx, "claims")
    c = _claims.open_claim(db, ctx, order_id=body.order_id, claim_type=body.claim_type, description=body.description)
    return ClaimItem(
        id=c.id, order_id=c.order_id, claim_type=c.claim_type, status=c.status,
        description=c.description, created_at=c.created_at,
    )


@router.get("/pricing/tariffs", response_model=list[TariffItem])
def list_tariffs(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> list[TariffItem]:
    require_module(ctx, "pricing_read")
    return [
        TariffItem(
            id=t.id, name=t.name, tariff_type=t.tariff_type, vehicle_class=t.vehicle_class,
            zone=t.zone, base_cents=t.base_cents, per_km_cents=t.per_km_cents,
            fuel_surcharge_percent=t.fuel_surcharge_percent, is_active=t.is_active,
        )
        for t in _pricing.list_tariffs(db)
    ]


@router.post("/pricing/tariffs", response_model=TariffItem)
def create_tariff(
    body: TariffCreateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> TariffItem:
    require_module(ctx, "pricing")
    t = _pricing.create_tariff(db, ctx, **body.model_dump())
    return TariffItem(
        id=t.id, name=t.name, tariff_type=t.tariff_type, vehicle_class=t.vehicle_class,
        zone=t.zone, base_cents=t.base_cents, per_km_cents=t.per_km_cents,
        fuel_surcharge_percent=t.fuel_surcharge_percent, is_active=t.is_active,
    )


@router.get("/pricing/promotions", response_model=list[PromotionItem])
def list_promotions(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> list[PromotionItem]:
    require_module(ctx, "pricing_read")
    return [
        PromotionItem(
            id=p.id, code=p.code, promotion_type=getattr(p, "promotion_type", "coupon"),
            merchant_id=getattr(p, "merchant_id", None),
            discount_percent=p.discount_percent, discount_cents=p.discount_cents,
            is_active=p.is_active,
        )
        for p in _pricing.list_promotions(db)
    ]


@router.post("/pricing/promotions", response_model=PromotionItem)
def create_promotion(
    body: PromotionCreateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> PromotionItem:
    require_module(ctx, "pricing")
    p = _pricing.create_promotion(db, body.code, **body.model_dump(exclude={"code"}))
    return PromotionItem(
        id=p.id, code=p.code, promotion_type=p.promotion_type,
        merchant_id=p.merchant_id, discount_percent=p.discount_percent,
        discount_cents=p.discount_cents, is_active=p.is_active,
    )


@router.get("/pricing/zones", response_model=list[PricingZoneItem])
def list_pricing_zones(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> list[PricingZoneItem]:
    require_module(ctx, "pricing_read")
    return [
        PricingZoneItem(id=z.id, code=z.code, name=z.name, multiplier=z.multiplier, is_active=z.is_active)
        for z in _pricing.list_zones(db)
    ]


@router.post("/pricing/zones", response_model=PricingZoneItem)
def create_pricing_zone(
    body: PricingZoneCreateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> PricingZoneItem:
    require_module(ctx, "pricing")
    z = _pricing.create_zone(db, **body.model_dump())
    return PricingZoneItem(id=z.id, code=z.code, name=z.name, multiplier=z.multiplier, is_active=z.is_active)


@router.get("/pricing/contracts", response_model=list[MerchantContractItem])
def list_merchant_contracts(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    merchant_id: str | None = None,
) -> list[MerchantContractItem]:
    require_module(ctx, "pricing_read")
    return [
        MerchantContractItem(
            id=c.id, merchant_id=c.merchant_id, name=c.name,
            minimum_monthly_commitment_cents=c.minimum_monthly_commitment_cents, is_active=c.is_active,
        )
        for c in _pricing.list_contracts(db, merchant_id=merchant_id)
    ]


@router.post("/pricing/contracts", response_model=MerchantContractItem)
def create_merchant_contract(
    body: MerchantContractCreateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> MerchantContractItem:
    require_module(ctx, "pricing")
    c = _pricing.create_contract(db, ctx, **body.model_dump())
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
    return _pricing.update_tax_config(db, body.model_dump())


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
    return _pricing.update_fuel_config(db, body.model_dump())


@router.get("/finance/summary")
def finance_summary(ctx: Annotated[AdminContext, Depends(get_admin_context)], db: Session = Depends(get_db)):
    require_module(ctx, "finance_read")
    return _finance.revenue_summary(db)


@router.get("/support/tickets", response_model=list[TicketItem])
def list_tickets(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    status: str | None = None,
) -> list[TicketItem]:
    require_module(ctx, "support")
    return [
        TicketItem(
            id=t.id, status=t.status, priority=t.priority, subject=t.subject,
            order_id=t.order_id, created_at=t.created_at,
        )
        for t in _support.list_tickets(db, status=status)
    ]


@router.post("/support/tickets", response_model=TicketItem)
def create_ticket(
    body: TicketCreateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> TicketItem:
    require_module(ctx, "support")
    t = _support.create_ticket(db, ctx, **body.model_dump())
    return TicketItem(
        id=t.id, status=t.status, priority=t.priority, subject=t.subject,
        order_id=t.order_id, created_at=t.created_at,
    )


@router.get("/reports/summary", response_model=ReportsSummaryResponse)
def reports_summary(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> ReportsSummaryResponse:
    require_module(ctx, "reports")
    return ReportsSummaryResponse(**_reports.summary(db))


@router.get("/settings/staff", response_model=list[StaffItem])
def list_staff(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> list[StaffItem]:
    require_module(ctx, "settings")
    return [
        StaffItem(id=u.id, email=u.email, name=u.name, role=u.role, created_at=u.created_at)
        for u in _settings.list_staff(db)
    ]


@router.patch("/settings/staff/{user_id}/role", response_model=StaffItem)
def update_staff_role(
    user_id: str,
    body: StaffRoleUpdateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> StaffItem:
    require_module(ctx, "settings")
    u = _settings.update_staff_role(db, user_id, body.role)
    return StaffItem(id=u.id, email=u.email, name=u.name, role=u.role, created_at=u.created_at)


@router.get("/settings/config")
def get_system_config(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    return _settings.default_config(db)
