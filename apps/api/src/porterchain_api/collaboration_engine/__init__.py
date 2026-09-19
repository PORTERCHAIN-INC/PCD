"""Collaboration engine — CRM data for activities, contacts, and merchant notes (Phase 1 slice)."""

from porterchain_api.collaboration_engine.crm_service import CrmSalesService
from porterchain_api.collaboration_engine.lead_ingest_service import LeadIngestService

__all__ = ["CrmSalesService", "LeadIngestService"]
