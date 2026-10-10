"""Leads — all development test levels (unit → service → API → flow).

Covers the admin CRM lead spine that Leaf 1–5 already partially exercise:
list/create/get/patch/pipeline/metrics/convert/referral validation, plus
service filters and schema contracts.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role
from porterchain_api.admin_models import AdminUser
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.collaboration_engine import CrmSalesService, LeadIngestService
from porterchain_api.collaboration_engine.lead_ingest_service import CanonicalLeadEvent
from porterchain_api.crm_models import CrmLead, CrmLeadIdentity
from porterchain_api.db import get_db
from porterchain_api.domain.crm_states import (
    LeadDecisionStatus,
    LeadIntentType,
    LeadPriority,
    LeadSourceChannel,
    LeadStatus,
    channel_for_source,
)
from porterchain_api.main import app
from porterchain_api.merchant_models import Merchant
from porterchain_api.routers.admin import leads as leads_mod
from porterchain_api.schemas_crm import (
    LeadConvertRequest,
    LeadCreate,
    LeadOut,
    LeadUpdate,
)

# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def crm() -> CrmSalesService:
    return CrmSalesService()


@pytest.fixture
def staff_ctx() -> SimpleNamespace:
    return SimpleNamespace(user=SimpleNamespace(id="staff-leads-dev"))


@pytest.fixture
def admin_client(db, monkeypatch):
    monkeypatch.setattr(leads_mod, "require_module", lambda ctx, module: None)
    import porterchain_api.routers.admin.leads_360 as leads_360_mod
    from porterchain_api.user_models import PorterchainUser

    # assist / calendar / merge live on leads_360 (separate import binding)
    monkeypatch.setattr(leads_360_mod, "require_module", lambda ctx, module: None)

    pc = PorterchainUser(
        id="user-leads-dev",
        clerk_user_id="clerk-leads-dev",
        email="leads-dev@porterchain.com",
        role="super_admin",
        status="active",
    )
    db.merge(pc)
    db.flush()

    admin = AdminContext(
        user=AdminUser(
            clerk_user_id="clerk-leads-dev",
            email="leads-dev@porterchain.com",
            role="super_admin",
            porterchain_user_id="user-leads-dev",
        ),
        role=parse_admin_role("super_admin"),
    )
    app.dependency_overrides[get_admin_context] = lambda: admin
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def _suffix() -> str:
    return uuid.uuid4().hex[:8]


def _phone(s: str) -> str:
    # Full hex → 7 subscriber digits; XOR random so shared DB merges stay rare.
    # Callers sometimes prefix suffixes ("t…", "m…") — strip non-hex first.
    hexish = "".join(c for c in s.lower() if c in "0123456789abcdef") or "4242"
    n = (int(hexish[:12], 16) ^ int(uuid.uuid4().hex[:8], 16)) % 10_000_000
    return f"+1416{n:07d}"


def _seed_lead(db, *, suffix: str | None = None, **overrides) -> CrmLead:
    s = suffix or _suffix()
    row = CrmLead(
        company_name=overrides.pop("company_name", f"Dev Co {s}"),
        email=overrides.pop("email", f"dev-{s}@acme.test"),
        phone=overrides.pop("phone", _phone(s)),
        primary_contact_name=overrides.pop("primary_contact_name", "Dev Contact"),
        source=overrides.pop("source", "website_contact"),
        channel=overrides.pop("channel", "website"),
        status=overrides.pop("status", LeadStatus.NEW.value),
        priority=overrides.pop("priority", LeadPriority.MEDIUM.value),
        intent_type=overrides.pop("intent_type", LeadIntentType.MERCHANT.value),
        decision_status=overrides.pop("decision_status", LeadDecisionStatus.NEW.value),
        address=overrides.pop("address", {"city": "Toronto", "province": "ON"}),
        industry=overrides.pop("industry", "food"),
        **overrides,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# =========================================================================== #
# Level 1 — Unit (schemas / enums / pure helpers)
# =========================================================================== #


class TestLeadsUnit:
    def test_lead_create_requires_company_name(self) -> None:
        with pytest.raises(ValidationError):
            LeadCreate(email="a@b.com")  # type: ignore[call-arg]

    def test_lead_create_defaults(self) -> None:
        body = LeadCreate(company_name="Acme", email="a@acme.test")
        assert body.status == "new"
        assert body.priority == "medium"
        assert body.intent_type == "merchant"
        assert body.source == "website"

    def test_lead_update_partial_ok(self) -> None:
        body = LeadUpdate(status="contacted", priority="high")
        assert body.model_dump(exclude_unset=True) == {
            "status": "contacted",
            "priority": "high",
        }

    def test_convert_request_outcomes(self) -> None:
        req = LeadConvertRequest(outcome="retail_customer", create_deal=False)
        assert req.outcome == "retail_customer"
        assert req.to_merchant is False

    def test_enum_values_stable(self) -> None:
        assert LeadStatus.NEW.value == "new"
        assert LeadStatus.CONVERTED.value == "won"  # legacy alias
        assert [s.value for s in LeadStatus] == ["new", "replied", "quoted", "won", "lost", "archived"]
        assert LeadPriority.URGENT.value == "urgent"
        assert LeadIntentType.DRIVER_PARTNER.value == "driver_partner"
        assert LeadDecisionStatus.READY_TO_CONVERT.value == "ready_to_convert"
        assert LeadSourceChannel.MERCHANT_REFERRAL.value == "merchant_referral"

    def test_channel_for_source_matrix(self) -> None:
        assert channel_for_source("website_quote") == "website"
        assert channel_for_source("phone_call") == "phone_call"
        assert channel_for_source("merchant_referral") == "merchant_referral"
        assert channel_for_source("instagram") == "instagram"


# =========================================================================== #
# Level 2 — Service (CrmSalesService / ingest helpers)
# =========================================================================== #


class TestLeadsService:
    def test_create_get_update_roundtrip(self, db, crm, staff_ctx) -> None:
        s = _suffix()
        lead = crm.create_lead(
            db,
            staff_ctx,
            {
                "company_name": f"Svc Co {s}",
                "email": f"svc-{s}@t.test",
                "phone": _phone(s),
                "source": "phone_call",
                "priority": "high",
                "estimated_deliveries_per_month": 120,
            },
        )
        assert lead.id
        assert lead.channel == "phone_call"
        assert lead.lead_score >= 20
        assert lead.assigned_to == staff_ctx.user.id

        got = crm.get_lead(db, lead.id)
        assert got is not None and got.email == lead.email

        updated = crm.update_lead(
            db, lead.id, {"status": LeadStatus.CONTACTED.value, "decision_status": "researching"}
        )
        assert updated.status == "replied"
        assert updated.decision_status == "researching"

    def test_list_filters_status_channel_search_unassigned(self, db, crm) -> None:
        s = _suffix()
        a = _seed_lead(
            db,
            suffix=f"a{s[:6]}",
            company_name=f"Alpha Filter {s}",
            channel="whatsapp",
            status="new",
            assigned_to=None,
        )
        _seed_lead(
            db,
            suffix=f"b{s[:6]}",
            company_name=f"Beta Other {s}",
            channel="website",
            status="qualified",
            assigned_to="owner-1",
        )

        by_channel = crm.list_leads(db, channel="whatsapp", search=f"Alpha Filter {s}")
        assert any(r.id == a.id for r in by_channel)

        unassigned = crm.list_leads(db, unassigned=True, search=s)
        assert all(r.assigned_to is None for r in unassigned)
        assert any(r.id == a.id for r in unassigned)

        status_rows = crm.list_leads(db, status="qualified", search=s)
        assert all(r.status == "qualified" for r in status_rows)

    def test_list_sla_breached_and_merge_candidates(self, db, crm) -> None:
        s = _suffix()
        target = _seed_lead(db, suffix=f"t{s[:6]}")
        breached = _seed_lead(
            db,
            suffix=f"s{s[:6]}",
            status="new",
            sla_first_response_due_at=datetime.now(UTC) - timedelta(hours=1),
        )
        merge = _seed_lead(
            db,
            suffix=f"m{s[:6]}",
            merge_candidate_of=target.id,
        )

        sla_rows = crm.list_leads(db, sla_breached=True)
        assert any(r.id == breached.id for r in sla_rows)

        merge_rows = crm.list_leads(db, merge_candidates=True)
        assert any(r.id == merge.id for r in merge_rows)

    def test_facets_include_seeded_city_industry(self, db, crm) -> None:
        s = _suffix()
        _seed_lead(
            db,
            suffix=s,
            industry=f"coldchain-{s}",
            address={"city": f"Mississauga-{s}", "province": "ON"},
        )
        facets = crm.lead_filter_facets(db)
        assert f"coldchain-{s}" in facets["industries"]
        cities = {c["name"] for c in facets["cities"]}
        assert f"Mississauga-{s}" in cities

    def test_pipeline_board_includes_open_lead(self, db, crm) -> None:
        s = _suffix()
        lead = _seed_lead(db, suffix=s, company_name=f"Pipe Lead {s}", status="new")
        board = crm.pipeline_board(db, search=s)
        assert isinstance(board, list)
        cards = [c for col in board for c in col.get("cards", [])]
        assert any(c.get("type") == "lead" and c.get("id") == lead.id for c in cards)

    def test_convert_creates_company_and_deal(self, db, crm, staff_ctx) -> None:
        s = _suffix()
        lead = _seed_lead(
            db,
            suffix=s,
            company_name=f"Convert Co {s}",
            primary_contact_name="Pat Convert",
            estimated_revenue_cents=250_000,
        )
        result = crm.convert_lead(db, staff_ctx, lead.id, create_deal=True)
        assert result["company_id"]
        assert result["deal_id"]
        refreshed = crm.get_lead(db, lead.id)
        assert refreshed is not None
        assert refreshed.status == LeadStatus.CONVERTED.value
        assert refreshed.company_id == result["company_id"]


# =========================================================================== #
# Level 3 — API (admin router via TestClient)
# =========================================================================== #


class TestLeadsApi:
    def test_create_requires_email_or_phone(self, admin_client) -> None:
        res = admin_client.post(
            "/v1/admin/leads",
            json={"company_name": "No Contact Co"},
        )
        assert res.status_code == 400
        assert res.json()["detail"] == "email_or_phone_required"

    def test_create_list_get_patch(self, admin_client, db) -> None:
        s = _suffix()
        email = f"api-{s}@acme.test"
        create = admin_client.post(
            "/v1/admin/leads",
            json={
                "company_name": f"API Co {s}",
                "email": email,
                "phone": _phone(s),
                "source": "manual",
                "priority": "high",
                "internal_notes": "Called from front desk",
                "tags": ["dev-level"],
            },
        )
        assert create.status_code == 201, create.text
        body = create.json()
        lead_id = body["id"]
        assert body["email"] == email
        assert body["channel"] == "manual"
        assert body["source"] == "manual"
        assert body["lead_score"] >= 0
        LeadOut.model_validate(body)

        listed = admin_client.get("/v1/admin/leads", params={"search": s})
        assert listed.status_code == 200
        assert any(row["id"] == lead_id for row in listed.json()["items"])

        got = admin_client.get(f"/v1/admin/leads/{lead_id}")
        assert got.status_code == 200
        assert got.json()["company_name"] == f"API Co {s}"

        patched = admin_client.patch(
            f"/v1/admin/leads/{lead_id}",
            json={"status": "contacted", "decision_status": "questions_open"},
        )
        assert patched.status_code == 200
        assert patched.json()["status"] == "replied"
        assert patched.json()["decision_status"] == "questions_open"

        missing = admin_client.get(f"/v1/admin/leads/{uuid.uuid4()}")
        assert missing.status_code == 404

    def test_pipeline_and_metrics(self, admin_client, db) -> None:
        s = _suffix()
        _seed_lead(db, suffix=s, company_name=f"Metrics Co {s}")

        pipeline = admin_client.get("/v1/admin/leads/pipeline", params={"search": s})
        assert pipeline.status_code == 200
        assert isinstance(pipeline.json(), list)

        metrics = admin_client.get("/v1/admin/leads/metrics", params={"days": 30})
        assert metrics.status_code == 200
        data = metrics.json()
        assert data["window_days"] == 30
        assert "leads" in data
        assert "funnel_by_channel" in data["leads"] or "total" in data["leads"]

    def test_identities_and_assist(self, admin_client, db) -> None:
        s = _suffix()
        lead = _seed_lead(db, suffix=s)
        db.add(
            CrmLeadIdentity(
                lead_id=lead.id,
                kind="email",
                value_normalized=lead.email or f"id-{s}@t.test",
                raw_value=lead.email,
            )
        )
        db.commit()

        ids = admin_client.get(f"/v1/admin/leads/{lead.id}/identities")
        assert ids.status_code == 200
        assert any(row["kind"] == "email" for row in ids.json())

        assist = admin_client.get(f"/v1/admin/leads/{lead.id}/assist")
        assert assist.status_code == 200
        assert isinstance(assist.json(), dict)

    def test_referral_missing_merchant_404(self, admin_client) -> None:
        res = admin_client.post(
            "/v1/admin/leads/referral",
            json={
                "company_name": "Referred Co",
                "email": "ref@t.test",
                "referred_by_merchant_id": str(uuid.uuid4()),
            },
        )
        assert res.status_code == 404
        assert res.json()["detail"] == "referring_merchant_not_found"

    def test_referral_happy_path(self, admin_client, db) -> None:
        s = _suffix()
        merchant = Merchant(
            company_name=f"Referrer {s}",
            email=f"referrer-{s}@m.test",
            status="ACTIVE",
        )
        db.add(merchant)
        db.commit()
        db.refresh(merchant)

        res = admin_client.post(
            "/v1/admin/leads/referral",
            json={
                "company_name": f"Prospect {s}",
                "email": f"prospect-{s}@t.test",
                "phone": _phone(s),
                "referred_by_merchant_id": merchant.id,
                "primary_contact_name": "Ref Contact",
            },
        )
        assert res.status_code == 201, res.text
        body = res.json()
        assert body["referred_by_merchant_id"] == merchant.id
        assert body["channel"] == "merchant_referral"
        assert body["source"] == "merchant_referral"

    def test_convert_merchant_api(self, admin_client, db) -> None:
        s = _suffix()
        lead = _seed_lead(
            db,
            suffix=s,
            company_name=f"API Convert {s}",
            primary_contact_name="Kim Convert",
        )
        with patch(
            "porterchain_api.collaboration_engine.lead_capi.emit_lead_conversion_events",
            return_value={"emitted": False},
        ):
            res = admin_client.post(
                f"/v1/admin/leads/{lead.id}/convert",
                json={
                    "create_deal": True,
                    "outcome": "merchant",
                    "to_merchant": False,
                    "deal_name": f"Deal {s}",
                },
            )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["company_id"]
        assert body["outcome"] == "merchant"
        refreshed = db.get(CrmLead, lead.id)
        assert refreshed is not None
        assert refreshed.status == "won"

    def test_convert_driver_partner_queues_task(self, admin_client, db) -> None:
        s = _suffix()
        lead = _seed_lead(
            db,
            suffix=s,
            company_name=f"Driver Lead {s}",
            intent_type="driver_partner",
        )
        with patch(
            "porterchain_api.collaboration_engine.lead_capi.emit_lead_conversion_events",
            return_value={},
        ):
            res = admin_client.post(
                f"/v1/admin/leads/{lead.id}/convert",
                json={"outcome": "driver_partner", "create_deal": False},
            )
        assert res.status_code == 200, res.text
        assert res.json().get("driver_partner", {}).get("queued") is True

    def test_create_lead_manual_router_validation(self, db, monkeypatch) -> None:
        """Direct router call — email_or_phone gate without HTTP stack."""
        monkeypatch.setattr(leads_mod, "require_module", lambda ctx, module: None)
        ctx = AdminContext(
            user=AdminUser(
                clerk_user_id="x",
                email="x@t.test",
                role="sales",
            ),
            role=parse_admin_role("sales"),
        )
        with pytest.raises(HTTPException) as exc:
            leads_mod.create_lead_manual(
                body=LeadCreate(company_name="No contact"),
                ctx=ctx,
                db=db,
            )
        assert exc.value.status_code == 400


# =========================================================================== #
# Level 4 — Flow (ingest → workbench → convert)
# =========================================================================== #


class TestLeadsFlow:
    def test_ingest_to_list_to_convert(self, db, crm, staff_ctx, admin_client) -> None:
        s = _suffix()
        email = f"flow-{s}@acme.test"
        phone = _phone(s)
        ingested = LeadIngestService().ingest(
            db,
            CanonicalLeadEvent(
                channel="website",
                source="website_contact",
                provider="test",
                external_event_id=f"flow-{s}",
                company_name=f"Flow Co {s}",
                primary_contact_name="Flow Contact",
                email=email,
                phone=phone,
                message="Need GTA capacity",
                priority="high",
            ),
        )
        assert ingested.created is True
        lead_id = ingested.lead.id

        rows = admin_client.get(
            "/v1/admin/leads",
            params={"channel": "website", "search": s},
        )
        assert rows.status_code == 200
        assert any(r["id"] == lead_id for r in rows.json()["items"])

        patched = admin_client.patch(
            f"/v1/admin/leads/{lead_id}",
            json={"status": "qualified", "decision_status": "ready_to_convert"},
        )
        assert patched.status_code == 200

        with patch(
            "porterchain_api.collaboration_engine.lead_capi.emit_lead_conversion_events",
            return_value={"ok": True},
        ):
            converted = admin_client.post(
                f"/v1/admin/leads/{lead_id}/convert",
                json={"create_deal": True, "outcome": "merchant"},
            )
        assert converted.status_code == 200, converted.text
        assert converted.json()["company_id"]

        final = crm.get_lead(db, lead_id)
        assert final is not None
        assert final.status == LeadStatus.CONVERTED.value
        assert final.deal_id is not None
