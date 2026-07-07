"""Merchant saved booking templates."""

from sqlalchemy.orm import Session

from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import MerchantBookingTemplate


class MerchantTemplateService:
    def list_templates(self, db: Session, ctx: MerchantContext) -> list[MerchantBookingTemplate]:
        return (
            db.query(MerchantBookingTemplate)
            .filter(MerchantBookingTemplate.merchant_id == ctx.merchant.id)
            .order_by(MerchantBookingTemplate.name.asc())
            .all()
        )

    def create_template(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        name: str,
        payload: dict,
        is_recurring: bool = False,
        recurrence_rule: str | None = None,
    ) -> MerchantBookingTemplate:
        record = MerchantBookingTemplate(
            merchant_id=ctx.merchant.id,
            name=name,
            payload=payload,
            is_recurring=is_recurring,
            recurrence_rule=recurrence_rule,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def delete_template(self, db: Session, ctx: MerchantContext, template_id: str) -> None:
        record = (
            db.query(MerchantBookingTemplate)
            .filter(
                MerchantBookingTemplate.id == template_id,
                MerchantBookingTemplate.merchant_id == ctx.merchant.id,
            )
            .first()
        )
        if not record:
            raise LookupError("template_not_found")
        db.delete(record)
        db.commit()
