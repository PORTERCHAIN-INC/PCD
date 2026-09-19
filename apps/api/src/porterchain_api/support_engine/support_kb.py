"""Support knowledge base, macros, and automation rules."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_models import SystemConfig
from porterchain_api.platform.admin_audit import log_admin_audit
from porterchain_api.support_engine.support_helpers import SupportActor


class SupportKbMixin:
    def get_knowledge_base(self, db: Session) -> dict[str, Any]:
        row = db.query(SystemConfig).filter(SystemConfig.key == "support_kb").first()
        if row and row.value:
            return row.value
        default = {
            "categories": [
                {"id": "customers", "name": "Customer Guides"},
                {"id": "merchants", "name": "Merchant Guides"},
                {"id": "drivers", "name": "Driver Guides"},
                {"id": "developers", "name": "Developer Guides"},
                {"id": "internal", "name": "Internal Documentation"},
            ],
            "articles": [
                {
                    "id": "faq-tracking",
                    "category_id": "customers",
                    "title": "How to track your delivery",
                    "body": "Use your tracking number on the Porterchain tracking page.",
                    "version": 1,
                    "published": True,
                },
                {
                    "id": "faq-refund",
                    "category_id": "customers",
                    "title": "Refund policy",
                    "body": "Refunds are processed within 5-10 business days after approval.",
                    "version": 1,
                    "published": True,
                },
            ],
            "faq": [
                {"question": "Where is my parcel?", "answer": "Check tracking or contact support with your tracking number."},
            ],
        }
        return default

    def save_kb_article(self, db: Session, ctx: SupportActor, article: dict[str, Any]) -> dict[str, Any]:
        kb = self.get_knowledge_base(db)
        articles = list(kb.get("articles") or [])
        aid = article.get("id") or str(uuid.uuid4())
        article["id"] = aid
        article["version"] = int(article.get("version") or 1)
        existing = next((i for i, a in enumerate(articles) if a.get("id") == aid), None)
        if existing is not None:
            articles[existing] = {**articles[existing], **article, "version": articles[existing].get("version", 1) + 1}
        else:
            articles.append(article)
        kb["articles"] = articles
        row = db.query(SystemConfig).filter(SystemConfig.key == "support_kb").first()
        if not row:
            row = SystemConfig(key="support_kb", value=kb)
            db.add(row)
        else:
            row.value = kb
        log_admin_audit(db, ctx, action="support.kb.update", resource_type="system_config", resource_id=aid)
        db.commit()
        return article

    def get_macros(self, db: Session) -> list[dict[str, Any]]:
        row = db.query(SystemConfig).filter(SystemConfig.key == "support_macros").first()
        if row and row.value:
            if isinstance(row.value, dict):
                return list(row.value.get("macros") or [])
            if isinstance(row.value, list):
                return list(row.value)
        return [
            {
                "id": "greeting",
                "title": "Greeting",
                "body": "Hello, thank you for contacting Porterchain Support. How can I help you today?",
                "channel": "email",
            },
            {
                "id": "tracking",
                "title": "Tracking update",
                "body": "I have checked your shipment and will provide an update shortly.",
                "channel": "email",
            },
        ]

    def save_macro(self, db: Session, ctx: SupportActor, macro: dict[str, Any]) -> dict[str, Any]:
        macros = self.get_macros(db)
        mid = macro.get("id") or str(uuid.uuid4())
        macro["id"] = mid
        existing = next((i for i, m in enumerate(macros) if m.get("id") == mid), None)
        if existing is not None:
            macros[existing] = {**macros[existing], **macro}
        else:
            macros.append(macro)
        row = db.query(SystemConfig).filter(SystemConfig.key == "support_macros").first()
        payload = {"macros": macros}
        if not row:
            row = SystemConfig(key="support_macros", value=payload)
            db.add(row)
        else:
            row.value = payload
        log_admin_audit(db, ctx, action="support.macro.update", resource_type="system_config", resource_id=mid)
        db.commit()
        return macro

    def get_automation_rules(self, db: Session) -> dict[str, Any]:
        row = db.query(SystemConfig).filter(SystemConfig.key == "support_automation").first()
        if row and row.value:
            return row.value
        return {
            "auto_assign": True,
            "auto_escalate_breached_sla": True,
            "auto_close_resolved_days": 7,
            "auto_reminder_hours": 24,
            "auto_tagging": True,
            "auto_categorization": True,
            "auto_merge_duplicates": False,
        }

    def set_automation_rules(self, db: Session, ctx: SupportActor, rules: dict[str, Any]) -> dict[str, Any]:
        merged = {**self.get_automation_rules(db), **rules}
        row = db.query(SystemConfig).filter(SystemConfig.key == "support_automation").first()
        if not row:
            row = SystemConfig(key="support_automation", value=merged)
            db.add(row)
        else:
            row.value = merged
        log_admin_audit(db, ctx, action="support.automation.update", resource_type="system_config", resource_id="support_automation")
        db.commit()
        return merged
