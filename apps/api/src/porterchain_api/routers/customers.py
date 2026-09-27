"""Customer portal API — dashboard, invoices, support, rebook."""

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from porterchain_api.auth.clerk import get_clerk_claims
from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.customer import require_customer
from porterchain_api.auth.customer_onboarding import require_customer_portal_ready
from porterchain_api.booking_engine import CustomerService
from porterchain_api.booking_engine.invoice_service import InvoiceService
from porterchain_api.compliance_engine.privacy_service import PrivacyService
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.schemas import (
    CustomerDashboardResponse,
    CustomerRebookResponse,
    CustomerSupportTicketRequest,
    CustomerSupportTicketResponse,
)
from porterchain_api.schemas_booking import (
    CustomerInvoiceDetailResponse,
    CustomerInvoiceListItem,
)

router = APIRouter(prefix="/v1/customers", tags=["customers"])
_customers = CustomerService()
_invoices = InvoiceService()
_privacy = PrivacyService()


def _ready_customer(db: Session, claims: ClerkClaims, settings: Settings):
    customer = require_customer(db, claims, settings)
    try:
        require_customer_portal_ready(
            db, claims, customer, settings=settings, email=customer.email or claims.email
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return customer


@router.get("/me/dashboard", response_model=CustomerDashboardResponse)
def get_my_dashboard(
    db: Session = Depends(get_db),
    claims: ClerkClaims = Depends(get_clerk_claims),
    settings: Settings = Depends(get_settings),
) -> CustomerDashboardResponse:
    customer = require_customer(db, claims, settings)
    try:
        require_customer_portal_ready(
            db, claims, customer, settings=settings, email=customer.email or claims.email
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return CustomerDashboardResponse(**_customers.get_dashboard(db, customer.id))


@router.get("/me/invoices", response_model=list[CustomerInvoiceListItem])
def list_my_invoices(
    db: Session = Depends(get_db),
    claims: ClerkClaims = Depends(get_clerk_claims),
    settings: Settings = Depends(get_settings),
) -> list[CustomerInvoiceListItem]:
    customer = _ready_customer(db, claims, settings)
    rows = _invoices.list_for_customer(db, customer.id)
    return [CustomerInvoiceListItem(**row) for row in rows]


@router.get("/me/invoices/{invoice_id}", response_model=CustomerInvoiceDetailResponse)
def get_my_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
    claims: ClerkClaims = Depends(get_clerk_claims),
    settings: Settings = Depends(get_settings),
) -> CustomerInvoiceDetailResponse:
    customer = _ready_customer(db, claims, settings)
    try:
        detail = _invoices.detail_for_customer(db, customer.id, invoice_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="invoice_not_found") from None
    return CustomerInvoiceDetailResponse(**detail)


@router.get("/me/invoices/{invoice_id}/pdf")
def download_my_invoice_pdf(
    invoice_id: str,
    db: Session = Depends(get_db),
    claims: ClerkClaims = Depends(get_clerk_claims),
    settings: Settings = Depends(get_settings),
) -> Response:
    customer = _ready_customer(db, claims, settings)
    try:
        pdf, filename = _invoices.pdf_for_customer(db, customer.id, invoice_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="invoice_not_found") from None
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/me/support", response_model=list[CustomerSupportTicketResponse])
def list_my_support_tickets(
    db: Session = Depends(get_db),
    claims: ClerkClaims = Depends(get_clerk_claims),
    settings: Settings = Depends(get_settings),
) -> list[CustomerSupportTicketResponse]:
    customer = require_customer(db, claims, settings)
    tickets = _customers.list_support_tickets(db, customer.id)
    return [
        CustomerSupportTicketResponse(
            ticket_id=t.id,
            status=t.status,
            subject=t.subject,
            description=t.description,
            order_id=t.order_id,
            created_at=t.created_at,
        )
        for t in tickets
    ]


@router.post("/me/support", response_model=CustomerSupportTicketResponse)
def create_support_ticket(
    body: CustomerSupportTicketRequest,
    db: Session = Depends(get_db),
    claims: ClerkClaims = Depends(get_clerk_claims),
    settings: Settings = Depends(get_settings),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> CustomerSupportTicketResponse:
    customer = require_customer(db, claims, settings)
    try:
        ticket = _customers.create_support_ticket(
            db,
            customer_id=customer.id,
            subject=body.subject,
            description=body.description,
            order_id=body.order_id,
            idempotency_key=idempotency_key,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return CustomerSupportTicketResponse(
        ticket_id=ticket.id,
        status=ticket.status,
        subject=ticket.subject,
        description=ticket.description,
        order_id=ticket.order_id,
        created_at=ticket.created_at,
    )


@router.post("/me/rebook/{order_id}", response_model=CustomerRebookResponse)
def rebook_from_order(
    order_id: str,
    db: Session = Depends(get_db),
    claims: ClerkClaims = Depends(get_clerk_claims),
    settings: Settings = Depends(get_settings),
) -> CustomerRebookResponse:
    customer = require_customer(db, claims, settings)
    try:
        payload = _customers.rebook_payload(db, customer.id, order_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="order_not_found") from None
    return CustomerRebookResponse(**payload)


@router.get("/me/privacy/export")
def customer_privacy_export(
    db: Session = Depends(get_db),
    claims: ClerkClaims = Depends(get_clerk_claims),
    settings: Settings = Depends(get_settings),
):
    customer = require_customer(db, claims, settings)
    return _privacy.export_customer(db, customer)


@router.post("/me/privacy/delete-request")
def customer_privacy_delete_request(
    db: Session = Depends(get_db),
    claims: ClerkClaims = Depends(get_clerk_claims),
    settings: Settings = Depends(get_settings),
):
    customer = require_customer(db, claims, settings)
    return _privacy.request_customer_deletion(db, customer)
