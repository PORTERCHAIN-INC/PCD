"""Porterchain Merchant CRM API — /v1/admin/crm/*

Logistics-specific CRM: leads, companies, contacts, deals, quotations,
contracts, merchant conversion, activities, tasks, dashboard, reports, import.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.crm_sales_service import CrmSalesService
from porterchain_api.admin_engine.rbac import AdminContext, require_module
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.db import get_db
from porterchain_api.domain.crm_states import (
    CONTACT_ROLES,
    PIPELINE_STAGES,
    STAGE_PROBABILITY,
)
from porterchain_api.schemas_crm import (
    ActivityCreate,
    ActivityOut,
    CompanyCreate,
    CompanyOut,
    CompanyUpdate,
    ContactCreate,
    ContactOut,
    ContactUpdate,
    ContractCreate,
    ContractOut,
    ContractUpdate,
    CrmDashboardResponse,
    CrmReportsResponse,
    CsvImportRequest,
    CsvImportResult,
    InvoiceCreate,
    InvoiceOut,
    InvoiceUpdate,
    DealCreate,
    DealOut,
    DealStageUpdate,
    DealUpdate,
    LeadConvertRequest,
    LeadConvertResponse,
    LeadCreate,
    LeadOut,
    LeadUpdate,
    PipelineColumn,
    QuotationCreate,
    QuotationOut,
    QuotationUpdate,
    TaskCreate,
    TaskOut,
    TaskUpdate,
)

router = APIRouter(prefix="/v1/admin/crm", tags=["crm"])

_crm = CrmSalesService()

READ = "crm_read"
WRITE = "crm"


def _guard(ctx: AdminContext, module: str) -> None:
    try:
        require_module(ctx, module)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def _not_found(detail: str):
    return HTTPException(status_code=404, detail=detail)


Ctx = Annotated[AdminContext, Depends(get_admin_context)]


# --------------------------------------------------------------------------- #
# Meta
# --------------------------------------------------------------------------- #
@router.get("/meta")
def crm_meta(ctx: Ctx) -> dict:
    _guard(ctx, READ)
    return {
        "pipeline_stages": PIPELINE_STAGES,
        "stage_probability": STAGE_PROBABILITY,
        "contact_roles": CONTACT_ROLES,
    }


# --------------------------------------------------------------------------- #
# Dashboard + reports
# --------------------------------------------------------------------------- #
@router.get("/dashboard", response_model=CrmDashboardResponse)
def crm_dashboard(ctx: Ctx, db: Session = Depends(get_db)) -> CrmDashboardResponse:
    _guard(ctx, READ)
    return CrmDashboardResponse(**_crm.dashboard(db))


@router.get("/reports", response_model=CrmReportsResponse)
def crm_reports(ctx: Ctx, db: Session = Depends(get_db)) -> CrmReportsResponse:
    _guard(ctx, READ)
    return CrmReportsResponse(**_crm.reports(db))


# --------------------------------------------------------------------------- #
# Companies
# --------------------------------------------------------------------------- #
@router.get("/companies/facets")
def company_facets(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, READ)
    return _crm.company_facets(db)


@router.get("/companies/stats")
def company_stats(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, READ)
    return _crm.company_stats(db)


@router.get("/companies", response_model=list[CompanyOut])
def list_companies(
    ctx: Ctx,
    db: Session = Depends(get_db),
    search: str | None = None,
    merchant_status: str | None = None,
    owner_id: str | None = None,
    industry: str | None = None,
    city: str | None = None,
    province: str | None = None,
    pinned: bool | None = None,
    limit: int = Query(500, le=10000),
    offset: int = 0,
) -> list[CompanyOut]:
    _guard(ctx, READ)
    rows = _crm.list_companies(
        db, search=search, merchant_status=merchant_status, owner_id=owner_id,
        industry=industry, city=city, province=province, pinned=pinned, limit=limit, offset=offset,
    )
    return [CompanyOut.model_validate(c) for c in rows]


@router.post("/companies", response_model=CompanyOut)
def create_company(body: CompanyCreate, ctx: Ctx, db: Session = Depends(get_db)) -> CompanyOut:
    _guard(ctx, WRITE)
    company = _crm.create_company(db, ctx, body.model_dump())
    return CompanyOut.model_validate(company)


@router.get("/companies/{company_id}", response_model=CompanyOut)
def get_company(company_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> CompanyOut:
    _guard(ctx, READ)
    company = _crm.get_company(db, company_id)
    if not company:
        raise _not_found("company_not_found")
    return CompanyOut.model_validate(company)


@router.patch("/companies/{company_id}", response_model=CompanyOut)
def update_company(
    company_id: str, body: CompanyUpdate, ctx: Ctx, db: Session = Depends(get_db)
) -> CompanyOut:
    _guard(ctx, WRITE)
    try:
        company = _crm.update_company(db, company_id, body.model_dump(exclude_unset=True))
    except LookupError:
        raise _not_found("company_not_found") from None
    return CompanyOut.model_validate(company)


@router.delete("/companies/{company_id}", status_code=204)
def delete_company(company_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> None:
    _guard(ctx, WRITE)
    try:
        _crm.delete_company(db, company_id)
    except LookupError:
        raise _not_found("company_not_found") from None


@router.post("/companies/{company_id}/convert-merchant")
def convert_company_to_merchant(company_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, WRITE)
    try:
        return _crm.convert_company_to_merchant(db, ctx, company_id)
    except LookupError:
        raise _not_found("company_not_found") from None


# --------------------------------------------------------------------------- #
# Contacts
# --------------------------------------------------------------------------- #
@router.get("/contacts", response_model=list[ContactOut])
def list_contacts(
    ctx: Ctx,
    db: Session = Depends(get_db),
    company_id: str | None = None,
    search: str | None = None,
) -> list[ContactOut]:
    _guard(ctx, READ)
    rows = _crm.list_contacts(db, company_id=company_id, search=search)
    return [ContactOut.model_validate(c) for c in rows]


@router.post("/contacts", response_model=ContactOut)
def create_contact(body: ContactCreate, ctx: Ctx, db: Session = Depends(get_db)) -> ContactOut:
    _guard(ctx, WRITE)
    contact = _crm.create_contact(db, ctx, body.model_dump())
    return ContactOut.model_validate(contact)


@router.patch("/contacts/{contact_id}", response_model=ContactOut)
def update_contact(
    contact_id: str, body: ContactUpdate, ctx: Ctx, db: Session = Depends(get_db)
) -> ContactOut:
    _guard(ctx, WRITE)
    try:
        contact = _crm.update_contact(db, contact_id, body.model_dump(exclude_unset=True))
    except LookupError:
        raise _not_found("contact_not_found") from None
    return ContactOut.model_validate(contact)


@router.delete("/contacts/{contact_id}", status_code=204)
def delete_contact(contact_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> None:
    _guard(ctx, WRITE)
    try:
        _crm.delete_contact(db, contact_id)
    except LookupError:
        raise _not_found("contact_not_found") from None


# --------------------------------------------------------------------------- #
# Leads
# --------------------------------------------------------------------------- #
@router.get("/leads/facets")
def lead_facets(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, READ)
    return _crm.lead_filter_facets(db)


@router.get("/leads", response_model=list[LeadOut])
def list_leads(
    ctx: Ctx,
    db: Session = Depends(get_db),
    status: str | None = None,
    priority: str | None = None,
    assigned_to: str | None = None,
    source: str | None = None,
    industry: str | None = None,
    city: str | None = None,
    province: str | None = None,
    min_score: int | None = None,
    unassigned: bool | None = None,
    converted: bool | None = None,
    search: str | None = None,
    limit: int = Query(500, le=10000),
) -> list[LeadOut]:
    _guard(ctx, READ)
    rows = _crm.list_leads(
        db,
        status=status,
        priority=priority,
        assigned_to=assigned_to,
        source=source,
        industry=industry,
        city=city,
        province=province,
        min_score=min_score,
        unassigned=unassigned,
        converted=converted,
        search=search,
        limit=limit,
    )
    return [LeadOut.model_validate(l) for l in rows]


@router.post("/leads", response_model=LeadOut)
def create_lead(body: LeadCreate, ctx: Ctx, db: Session = Depends(get_db)) -> LeadOut:
    _guard(ctx, WRITE)
    lead = _crm.create_lead(db, ctx, body.model_dump())
    return LeadOut.model_validate(lead)


@router.get("/leads/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> LeadOut:
    _guard(ctx, READ)
    lead = _crm.get_lead(db, lead_id)
    if not lead:
        raise _not_found("lead_not_found")
    return LeadOut.model_validate(lead)


@router.patch("/leads/{lead_id}", response_model=LeadOut)
def update_lead(lead_id: str, body: LeadUpdate, ctx: Ctx, db: Session = Depends(get_db)) -> LeadOut:
    _guard(ctx, WRITE)
    try:
        lead = _crm.update_lead(db, lead_id, body.model_dump(exclude_unset=True))
    except LookupError:
        raise _not_found("lead_not_found") from None
    return LeadOut.model_validate(lead)


@router.delete("/leads/{lead_id}", status_code=204)
def delete_lead(lead_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> None:
    _guard(ctx, WRITE)
    try:
        _crm.delete_lead(db, lead_id)
    except LookupError:
        raise _not_found("lead_not_found") from None


@router.post("/leads/{lead_id}/convert", response_model=LeadConvertResponse)
def convert_lead(
    lead_id: str, body: LeadConvertRequest, ctx: Ctx, db: Session = Depends(get_db)
) -> LeadConvertResponse:
    _guard(ctx, WRITE)
    try:
        result = _crm.convert_lead(
            db, ctx, lead_id,
            create_deal=body.create_deal,
            deal_name=body.deal_name,
            expected_revenue_cents=body.expected_revenue_cents,
            target_stage=body.target_stage,
        )
    except LookupError:
        raise _not_found("lead_not_found") from None
    return LeadConvertResponse(**result)


# --------------------------------------------------------------------------- #
# Deals / pipeline
# --------------------------------------------------------------------------- #
@router.get("/deals/board")
def deals_board(ctx: Ctx, db: Session = Depends(get_db)) -> list[dict]:
    _guard(ctx, READ)
    return _crm.board(db)


@router.get("/pipeline", response_model=list[PipelineColumn])
def pipeline(
    ctx: Ctx,
    db: Session = Depends(get_db),
    search: str | None = None,
    card_type: str | None = None,
    min_value_cents: int | None = None,
) -> list[PipelineColumn]:
    """Unified merchant-acquisition board: un-converted leads + deals."""
    _guard(ctx, READ)
    cols = _crm.pipeline_board(db, search=search, card_type=card_type, min_value_cents=min_value_cents)
    return [PipelineColumn(**col) for col in cols]


@router.get("/deals", response_model=list[DealOut])
def list_deals(
    ctx: Ctx,
    db: Session = Depends(get_db),
    stage: str | None = None,
    owner_id: str | None = None,
    company_id: str | None = None,
) -> list[DealOut]:
    _guard(ctx, READ)
    rows = _crm.list_deals(db, stage=stage, owner_id=owner_id, company_id=company_id)
    return [DealOut.model_validate(_crm.deal_with_company_name(db, d)) for d in rows]


@router.post("/deals", response_model=DealOut)
def create_deal(body: DealCreate, ctx: Ctx, db: Session = Depends(get_db)) -> DealOut:
    _guard(ctx, WRITE)
    deal = _crm.create_deal(db, ctx, body.model_dump())
    return DealOut.model_validate(_crm.deal_with_company_name(db, deal))


@router.get("/deals/{deal_id}", response_model=DealOut)
def get_deal(deal_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> DealOut:
    _guard(ctx, READ)
    deal = _crm.get_deal(db, deal_id)
    if not deal:
        raise _not_found("deal_not_found")
    return DealOut.model_validate(_crm.deal_with_company_name(db, deal))


@router.patch("/deals/{deal_id}", response_model=DealOut)
def update_deal(deal_id: str, body: DealUpdate, ctx: Ctx, db: Session = Depends(get_db)) -> DealOut:
    _guard(ctx, WRITE)
    try:
        deal = _crm.update_deal(db, ctx, deal_id, body.model_dump(exclude_unset=True))
    except LookupError:
        raise _not_found("deal_not_found") from None
    return DealOut.model_validate(_crm.deal_with_company_name(db, deal))


@router.post("/deals/{deal_id}/move", response_model=DealOut)
def move_deal(deal_id: str, body: DealStageUpdate, ctx: Ctx, db: Session = Depends(get_db)) -> DealOut:
    _guard(ctx, WRITE)
    try:
        deal = _crm.move_deal(db, ctx, deal_id, body.stage, body.position)
    except LookupError:
        raise _not_found("deal_not_found") from None
    return DealOut.model_validate(_crm.deal_with_company_name(db, deal))


@router.delete("/deals/{deal_id}", status_code=204)
def delete_deal(deal_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> None:
    _guard(ctx, WRITE)
    try:
        _crm.delete_deal(db, deal_id)
    except LookupError:
        raise _not_found("deal_not_found") from None


# --------------------------------------------------------------------------- #
# Quotations
# --------------------------------------------------------------------------- #
@router.get("/quotations", response_model=list[QuotationOut])
def list_quotations(
    ctx: Ctx,
    db: Session = Depends(get_db),
    deal_id: str | None = None,
    company_id: str | None = None,
) -> list[QuotationOut]:
    _guard(ctx, READ)
    rows = _crm.list_quotations(db, deal_id=deal_id, company_id=company_id)
    return [QuotationOut.model_validate(q) for q in rows]


@router.post("/quotations", response_model=QuotationOut)
def create_quotation(body: QuotationCreate, ctx: Ctx, db: Session = Depends(get_db)) -> QuotationOut:
    _guard(ctx, WRITE)
    quotation = _crm.create_quotation(db, ctx, body.model_dump())
    return QuotationOut.model_validate(quotation)


@router.post("/quotations/{quotation_id}/revise", response_model=QuotationOut)
def revise_quotation(
    quotation_id: str, body: QuotationUpdate, ctx: Ctx, db: Session = Depends(get_db)
) -> QuotationOut:
    _guard(ctx, WRITE)
    try:
        quotation = _crm.revise_quotation(db, ctx, quotation_id, body.model_dump(exclude_unset=True))
    except LookupError:
        raise _not_found("quotation_not_found") from None
    return QuotationOut.model_validate(quotation)


@router.post("/quotations/{quotation_id}/status", response_model=QuotationOut)
def set_quotation_status(
    quotation_id: str, ctx: Ctx, status: str = Query(...), db: Session = Depends(get_db)
) -> QuotationOut:
    _guard(ctx, WRITE)
    try:
        quotation = _crm.update_quotation_status(db, ctx, quotation_id, status)
    except LookupError:
        raise _not_found("quotation_not_found") from None
    return QuotationOut.model_validate(quotation)


@router.post("/quotations/{quotation_id}/convert-contract", response_model=ContractOut)
def convert_quotation_to_contract(
    quotation_id: str, ctx: Ctx, db: Session = Depends(get_db)
) -> ContractOut:
    _guard(ctx, WRITE)
    try:
        contract = _crm.convert_quotation_to_contract(db, ctx, quotation_id)
    except LookupError:
        raise _not_found("quotation_not_found") from None
    return ContractOut.model_validate(contract)


# --------------------------------------------------------------------------- #
# Contracts
# --------------------------------------------------------------------------- #
@router.get("/contracts", response_model=list[ContractOut])
def list_contracts(
    ctx: Ctx,
    db: Session = Depends(get_db),
    company_id: str | None = None,
    status: str | None = None,
) -> list[ContractOut]:
    _guard(ctx, READ)
    rows = _crm.list_contracts(db, company_id=company_id, status=status)
    return [ContractOut.model_validate(c) for c in rows]


@router.post("/contracts", response_model=ContractOut)
def create_contract(body: ContractCreate, ctx: Ctx, db: Session = Depends(get_db)) -> ContractOut:
    _guard(ctx, WRITE)
    contract = _crm.create_contract(db, ctx, body.model_dump())
    return ContractOut.model_validate(contract)


@router.patch("/contracts/{contract_id}", response_model=ContractOut)
def update_contract(
    contract_id: str, body: ContractUpdate, ctx: Ctx, db: Session = Depends(get_db)
) -> ContractOut:
    _guard(ctx, WRITE)
    try:
        contract = _crm.update_contract(db, contract_id, body.model_dump(exclude_unset=True))
    except LookupError:
        raise _not_found("contract_not_found") from None
    return ContractOut.model_validate(contract)


# --------------------------------------------------------------------------- #
# Invoices
# --------------------------------------------------------------------------- #
@router.get("/invoices", response_model=list[InvoiceOut])
def list_invoices(
    ctx: Ctx,
    db: Session = Depends(get_db),
    company_id: str | None = None,
    status: str | None = None,
) -> list[InvoiceOut]:
    _guard(ctx, READ)
    rows = _crm.list_invoices(db, company_id=company_id, status=status)
    return [InvoiceOut.model_validate(i) for i in rows]


@router.post("/invoices", response_model=InvoiceOut)
def create_invoice(body: InvoiceCreate, ctx: Ctx, db: Session = Depends(get_db)) -> InvoiceOut:
    _guard(ctx, WRITE)
    invoice = _crm.create_invoice(db, ctx, body.model_dump())
    return InvoiceOut.model_validate(invoice)


@router.patch("/invoices/{invoice_id}", response_model=InvoiceOut)
def update_invoice(invoice_id: str, body: InvoiceUpdate, ctx: Ctx, db: Session = Depends(get_db)) -> InvoiceOut:
    _guard(ctx, WRITE)
    try:
        invoice = _crm.update_invoice(db, ctx, invoice_id, body.model_dump(exclude_unset=True))
    except LookupError:
        raise _not_found("invoice_not_found") from None
    return InvoiceOut.model_validate(invoice)


# --------------------------------------------------------------------------- #
# Activities
# --------------------------------------------------------------------------- #
@router.get("/activities", response_model=list[ActivityOut])
def list_activities(
    ctx: Ctx,
    db: Session = Depends(get_db),
    entity_type: str | None = None,
    entity_id: str | None = None,
    limit: int = Query(100, le=500),
) -> list[ActivityOut]:
    _guard(ctx, READ)
    rows = _crm.list_activities(db, entity_type=entity_type, entity_id=entity_id, limit=limit)
    return [ActivityOut(**_crm.activity_dict(a)) for a in rows]


@router.post("/activities", response_model=ActivityOut)
def create_activity(body: ActivityCreate, ctx: Ctx, db: Session = Depends(get_db)) -> ActivityOut:
    _guard(ctx, WRITE)
    activity = _crm.log_activity(
        db,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        activity_type=body.activity_type,
        subject=body.subject,
        body=body.body,
        metadata=body.metadata,
        actor_id=ctx.user.id if ctx.user else None,
        occurred_at=body.occurred_at,
    )
    return ActivityOut(**_crm.activity_dict(activity))


# --------------------------------------------------------------------------- #
# Tasks
# --------------------------------------------------------------------------- #
@router.get("/tasks", response_model=list[TaskOut])
def list_tasks(
    ctx: Ctx,
    db: Session = Depends(get_db),
    status: str | None = None,
    assigned_to: str | None = None,
    entity_id: str | None = None,
) -> list[TaskOut]:
    _guard(ctx, READ)
    rows = _crm.list_tasks(db, status=status, assigned_to=assigned_to, entity_id=entity_id)
    return [TaskOut.model_validate(t) for t in rows]


@router.post("/tasks", response_model=TaskOut)
def create_task(body: TaskCreate, ctx: Ctx, db: Session = Depends(get_db)) -> TaskOut:
    _guard(ctx, WRITE)
    task = _crm.create_task(db, ctx, body.model_dump())
    return TaskOut.model_validate(task)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: str, body: TaskUpdate, ctx: Ctx, db: Session = Depends(get_db)) -> TaskOut:
    _guard(ctx, WRITE)
    try:
        task = _crm.update_task(db, task_id, body.model_dump(exclude_unset=True))
    except LookupError:
        raise _not_found("task_not_found") from None
    return TaskOut.model_validate(task)


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> None:
    _guard(ctx, WRITE)
    try:
        _crm.delete_task(db, task_id)
    except LookupError:
        raise _not_found("task_not_found") from None


# --------------------------------------------------------------------------- #
# CSV / Excel import
# --------------------------------------------------------------------------- #
@router.post("/import", response_model=CsvImportResult)
def import_records(body: CsvImportRequest, ctx: Ctx, db: Session = Depends(get_db)) -> CsvImportResult:
    _guard(ctx, WRITE)
    result = _crm.import_rows(db, ctx, body.entity, body.rows, dedupe=body.dedupe)
    return CsvImportResult(**result)
