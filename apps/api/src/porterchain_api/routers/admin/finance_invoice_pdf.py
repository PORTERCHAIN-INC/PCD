"""Admin invoice PDF — split from finance.py (D2 §0.3.9)."""

from fastapi.responses import Response

from porterchain_api.reporting.order_documents import pdf_bytes_for_invoice_id
from porterchain_api.routers.admin._deps import (
    AdminContext,
    Annotated,
    Depends,
    HTTPException,
    Session,
    get_admin_context,
    get_db,
    require_module,
    router,
)


@router.get("/finance/invoices/{invoice_id}/pdf")
def finance_invoice_pdf(
    invoice_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> Response:
    require_module(ctx, "finance_read")
    result = pdf_bytes_for_invoice_id(db, invoice_id)
    if not result:
        raise HTTPException(status_code=404, detail="invoice_not_found")
    pdf, filename = result
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
