"""Driver training modules."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

_DEFAULT_MODULES = [
    {"id": "safety", "title": "Safety & Compliance", "duration_minutes": 15},
    {"id": "pod", "title": "Proof of Delivery", "duration_minutes": 10},
    {"id": "customer", "title": "Customer Service", "duration_minutes": 12},
    {"id": "emergency", "title": "Emergency Procedures", "duration_minutes": 8},
]


class TrainingService:
    def list_modules(self, driver: Any) -> list[dict]:
        progress = (driver.performance or {}).get("training", {})
        modules = []
        for mod in _DEFAULT_MODULES:
            mod_id = mod["id"]
            entry = progress.get(mod_id, {})
            modules.append({**mod, "completed": entry.get("completed", False), "completed_at": entry.get("completed_at")})
        return modules

    def complete_module(self, db: Session, driver: Any, module_id: str) -> dict:
        from datetime import UTC, datetime

        perf = dict(driver.performance or {})
        training = dict(perf.get("training", {}))
        training[module_id] = {"completed": True, "completed_at": datetime.now(UTC).isoformat()}
        perf["training"] = training
        driver.performance = perf
        db.flush()
        return {"module_id": module_id, "completed": True}
