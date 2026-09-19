"""Porterchain Merchant CRM — sales engine.

Implements the logistics merchant-acquisition workflow: leads → companies →
deals → quotations → contracts → active merchants, plus the activity timeline,
tasks, dashboard, reporting, and CSV import.
"""

from porterchain_api.collaboration_engine.crm_activity import CrmActivityMixin
from porterchain_api.collaboration_engine.crm_companies import CrmCompaniesMixin
from porterchain_api.collaboration_engine.crm_contacts import CrmContactsMixin
from porterchain_api.collaboration_engine.crm_contracts import CrmContractsMixin
from porterchain_api.collaboration_engine.crm_dashboard import CrmDashboardMixin
from porterchain_api.collaboration_engine.crm_deals import CrmDealsMixin
from porterchain_api.collaboration_engine.crm_helpers import province_from_postal
from porterchain_api.collaboration_engine.crm_import import CrmImportMixin
from porterchain_api.collaboration_engine.crm_leads import CrmLeadsMixin
from porterchain_api.collaboration_engine.crm_numbers import CrmNumbersMixin
from porterchain_api.collaboration_engine.crm_quotations import CrmQuotationsMixin
from porterchain_api.collaboration_engine.crm_reports import CrmReportsMixin
from porterchain_api.collaboration_engine.crm_tasks import CrmTasksMixin


class CrmSalesService(
    CrmActivityMixin,
    CrmNumbersMixin,
    CrmCompaniesMixin,
    CrmContactsMixin,
    CrmLeadsMixin,
    CrmDealsMixin,
    CrmQuotationsMixin,
    CrmContractsMixin,
    CrmTasksMixin,
    CrmDashboardMixin,
    CrmReportsMixin,
    CrmImportMixin,
):
    """Unified CRM sales service composed from domain mixins."""


__all__ = ["CrmSalesService", "province_from_postal"]
