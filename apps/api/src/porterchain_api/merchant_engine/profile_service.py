"""Merchant business profile and saved addresses."""

from sqlalchemy.orm import Session

from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import Merchant, MerchantRecipient, SavedAddress
from porterchain_api.schemas_merchant import MerchantProfileUpdateRequest


class MerchantProfileService:
    def get_profile(self, ctx: MerchantContext) -> Merchant:
        return ctx.merchant

    def update_profile(
        self,
        db: Session,
        ctx: MerchantContext,
        body: MerchantProfileUpdateRequest,
    ) -> Merchant:
        merchant = ctx.merchant
        for field in (
            "company_name",
            "legal_name",
            "phone",
            "billing_address",
            "hst_number",
            "business_number",
            "delivery_zones",
        ):
            value = getattr(body, field)
            if value is not None:
                setattr(merchant, field, value)
        if body.preferred_vehicles is not None:
            from porterchain_api.admin_engine.merchant_service import AdminMerchantService

            merchant.preferred_vehicles = AdminMerchantService._validate_preferred_vehicles(
                db, list(body.preferred_vehicles)
            )
        db.commit()
        db.refresh(merchant)
        return merchant

    def list_saved_addresses(self, db: Session, ctx: MerchantContext) -> list[SavedAddress]:
        return (
            db.query(SavedAddress)
            .filter(SavedAddress.merchant_id == ctx.merchant.id)
            .order_by(SavedAddress.is_default.desc(), SavedAddress.label)
            .all()
        )

    def create_saved_address(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        label: str,
        address_type: str,
        formatted: str,
        place_id: str | None = None,
        lat: float | None = None,
        lng: float | None = None,
        is_default: bool = False,
    ) -> SavedAddress:
        if is_default:
            db.query(SavedAddress).filter(SavedAddress.merchant_id == ctx.merchant.id).update(
                {"is_default": False}
            )
        record = SavedAddress(
            merchant_id=ctx.merchant.id,
            label=label,
            address_type=address_type,
            formatted=formatted,
            place_id=place_id,
            lat=lat,
            lng=lng,
            is_default=is_default,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def delete_saved_address(self, db: Session, ctx: MerchantContext, address_id: str) -> None:
        record = (
            db.query(SavedAddress)
            .filter(SavedAddress.id == address_id, SavedAddress.merchant_id == ctx.merchant.id)
            .first()
        )
        if not record:
            raise LookupError("address_not_found")
        db.delete(record)
        db.commit()

    def list_recipients(self, db: Session, ctx: MerchantContext) -> list[MerchantRecipient]:
        return (
            db.query(MerchantRecipient)
            .filter(MerchantRecipient.merchant_id == ctx.merchant.id)
            .order_by(MerchantRecipient.name)
            .all()
        )

    def create_recipient(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        name: str,
        email: str | None = None,
        phone: str | None = None,
        company: str | None = None,
        default_address: dict | None = None,
    ) -> MerchantRecipient:
        record = MerchantRecipient(
            merchant_id=ctx.merchant.id,
            name=name,
            email=email,
            phone=phone,
            company=company,
            default_address=default_address,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
