# Archive — vendor cold-outbound notes

**Status:** archive-only after ingest. **CSV is not in git** (PII / dial lists stay local).

| Rule                 | Detail                                                                                      |
| -------------------- | ------------------------------------------------------------------------------------------- |
| SSOT                 | PCD `CrmLead` (`source=vendor_import` / `crm_import`) — database only                       |
| Local file           | Keep `vendors.csv` on disk next to this README or pass path to the importer — never commit  |
| CRM re-ingest        | `cd apps/api && PYTHONPATH=src python scripts/import_crm_leads.py` (reads sibling `CRM` DB) |
| Vendor CSV re-ingest | `PYTHONPATH=src python scripts/import_vendors.py` (idempotent; local CSV path)              |

Dial from Admin → Today Dial / Lead Agent. Production gets leads via import scripts against prod DB, not via git.
