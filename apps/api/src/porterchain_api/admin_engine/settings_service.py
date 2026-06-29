"""System settings and staff users."""

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import AdminUser, SystemConfig


class AdminSettingsService:
    def list_staff(self, db: Session) -> list[AdminUser]:
        return db.query(AdminUser).filter(AdminUser.is_active.is_(True)).order_by(AdminUser.email).all()

    def update_staff_role(self, db: Session, user_id: str, role: str) -> AdminUser:
        user = db.query(AdminUser).filter(AdminUser.id == user_id).first()
        if not user:
            raise LookupError("staff_not_found")
        user.role = role
        db.commit()
        db.refresh(user)
        return user

    def get_config(self, db: Session, key: str) -> SystemConfig | None:
        return db.query(SystemConfig).filter(SystemConfig.key == key).first()

    def set_config(self, db: Session, ctx: AdminContext, key: str, value: dict) -> SystemConfig:
        record = self.get_config(db, key)
        if record:
            record.value = value
        else:
            record = SystemConfig(key=key, value=value)
            db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def default_config(self, db: Session) -> dict:
        keys = ["service_areas", "vehicle_types", "package_types", "notification_templates", "integrations"]
        result = {}
        for key in keys:
            rec = self.get_config(db, key)
            result[key] = rec.value if rec else []
        return result
