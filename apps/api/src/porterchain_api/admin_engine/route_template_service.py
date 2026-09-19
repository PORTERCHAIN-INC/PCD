"""Wholesale route templates — admin CRUD on RouteCenterTemplate (§8.1.10)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_models import RouteCenterTemplate

WHOLESALE_TYPE = "wholesale"


class AdminRouteTemplateService:
    def list_templates(
        self,
        db: Session,
        *,
        merchant_id: str | None = None,
        active_only: bool = True,
    ) -> list[RouteCenterTemplate]:
        q = db.query(RouteCenterTemplate).filter(RouteCenterTemplate.template_type == WHOLESALE_TYPE)
        if merchant_id:
            q = q.filter(RouteCenterTemplate.merchant_id == merchant_id)
        if active_only:
            q = q.filter(RouteCenterTemplate.is_active.is_(True))
        return q.order_by(RouteCenterTemplate.name.asc()).all()

    def get_template(self, db: Session, template_id: str) -> RouteCenterTemplate | None:
        return (
            db.query(RouteCenterTemplate)
            .filter(
                RouteCenterTemplate.id == template_id,
                RouteCenterTemplate.template_type == WHOLESALE_TYPE,
            )
            .first()
        )

    def create_template(
        self,
        db: Session,
        *,
        name: str,
        merchant_id: str | None,
        zone: str | None,
        schedule: dict[str, Any],
        stops: list[dict[str, Any]],
        config: dict[str, Any],
        created_by: str | None,
    ) -> RouteCenterTemplate:
        record = RouteCenterTemplate(
            name=name,
            template_type=WHOLESALE_TYPE,
            merchant_id=merchant_id,
            zone=zone,
            schedule=schedule,
            stops=stops,
            config=config,
            created_by=created_by,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def update_template(
        self,
        db: Session,
        template_id: str,
        *,
        name: str | None = None,
        merchant_id: str | None = None,
        zone: str | None = None,
        schedule: dict[str, Any] | None = None,
        stops: list[dict[str, Any]] | None = None,
        config: dict[str, Any] | None = None,
        is_active: bool | None = None,
    ) -> RouteCenterTemplate:
        record = self.get_template(db, template_id)
        if not record:
            raise LookupError("route_template_not_found")
        if name is not None:
            record.name = name
        if merchant_id is not None:
            record.merchant_id = merchant_id
        if zone is not None:
            record.zone = zone
        if schedule is not None:
            record.schedule = schedule
        if stops is not None:
            record.stops = stops
        if config is not None:
            record.config = config
        if is_active is not None:
            record.is_active = is_active
        db.commit()
        db.refresh(record)
        return record

    def delete_template(self, db: Session, template_id: str) -> None:
        record = self.get_template(db, template_id)
        if not record:
            raise LookupError("route_template_not_found")
        record.is_active = False
        db.commit()

    def serialize(self, record: RouteCenterTemplate) -> dict[str, Any]:
        return {
            "id": record.id,
            "name": record.name,
            "template_type": record.template_type,
            "merchant_id": record.merchant_id,
            "zone": record.zone,
            "schedule": record.schedule or {},
            "stops": record.stops or [],
            "config": record.config or {},
            "is_active": record.is_active,
            "created_by": record.created_by,
            "created_at": record.created_at,
        }
