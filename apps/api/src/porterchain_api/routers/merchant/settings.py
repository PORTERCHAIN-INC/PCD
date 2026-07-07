"""merchant routes — settings."""

from porterchain_api.routers.merchant._deps import *  # noqa: F403

@router.get("/settings/overview")
def settings_overview(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    return _settings.overview(db, ctx)


@router.patch("/settings/notifications")
def settings_notifications(
    body: MerchantNotificationsRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    return _settings.update_notifications(db, ctx, body.model_dump(exclude_none=True))


@router.patch("/settings/branding")
def settings_branding(
    body: MerchantBrandingRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    return _settings.update_branding(db, ctx, body.model_dump(exclude_none=True))


@router.get("/settings/billing-contacts")
def settings_billing_contacts_list(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
):
    require_module(ctx, "settings")
    return _settings.list_billing_contacts(ctx)


@router.post("/settings/billing-contacts")
def settings_billing_contacts_create(
    body: BillingContactRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    return _settings.save_billing_contact(db, ctx, **body.model_dump())


@router.delete("/settings/billing-contacts/{contact_id}", status_code=204)
def settings_billing_contacts_delete(
    contact_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> None:
    require_module(ctx, "settings")
    _settings.delete_billing_contact(db, ctx, contact_id)


@router.get("/settings/warehouses")
def settings_warehouses_list(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
):
    require_module(ctx, "settings")
    return _settings.list_warehouses(ctx)


@router.post("/settings/warehouses")
def settings_warehouses_create(
    body: WarehouseRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    return _settings.save_warehouse(db, ctx, **body.model_dump())


@router.patch("/settings/warehouses/{warehouse_id}")
def settings_warehouses_update(
    warehouse_id: str,
    body: WarehouseRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    return _settings.save_warehouse(db, ctx, warehouse_id=warehouse_id, **body.model_dump())


@router.delete("/settings/warehouses/{warehouse_id}", status_code=204)
def settings_warehouses_delete(
    warehouse_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> None:
    require_module(ctx, "settings")
    _settings.delete_warehouse(db, ctx, warehouse_id)


@router.get("/settings/documents")
def settings_documents_list(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
):
    require_module(ctx, "settings")
    return _settings.list_documents(ctx)


@router.post("/settings/documents")
def settings_documents_create(
    body: BusinessDocumentRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    return _settings.add_document(db, ctx, name=body.name, doc_type=body.doc_type, reference=body.reference)


@router.delete("/settings/documents/{doc_id}", status_code=204)
def settings_documents_delete(
    doc_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> None:
    require_module(ctx, "settings")
    _settings.delete_document(db, ctx, doc_id)


@router.get("/settings/tax")
def settings_tax_get(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
):
    require_module(ctx, "settings")
    return _settings.tax_info(ctx)


@router.patch("/settings/tax")
def settings_tax_patch(
    body: MerchantProfileUpdateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    return _settings.update_tax(db, ctx, body)


@router.get("/settings/contract")
def settings_contract(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    return _settings.contract_summary(db, ctx)


@router.delete("/addresses/{address_id}", status_code=204)
def delete_address(
    address_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> None:
    require_module(ctx, "settings")
    try:
        _profile.delete_saved_address(db, ctx, address_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="address_not_found") from None

