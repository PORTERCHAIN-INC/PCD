"""Admin Leads module matrix — Jeff Dean style (touch what is real; firewall the rest).

Admin surfaces (from Graphify):
  /leads                  inbox + manual capture + filters + metrics
  /leads?source=website_driver_partner   driver applications inbox
  /leads/pipeline         acquisition board
  /leads/calendar         call/meeting week view
  /leads/[id]             detail, convert, assist, conversations, identities, delete
  Settings → LeadIngestPanel   secrets / territory / SLA / CAPI

Real handshakes: Clerk module gates, public webhooks, nurture email queue,
referral credits, Meta/LinkedIn CAPI on convert.

Intentional NON-touch (charter + Fleetbase-first): Valhalla, OSRM, VROOM,
Fleetbase dispatch, Google Distance Matrix, Shopify ERP, Firebase push,
SocketCluster — CRM leads must not import or call these.
"""

from __future__ import annotations

import ast
import json
import re
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role
from porterchain_api.admin_models import AdminUser
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.auth.modules_catalog import ADMIN_MODULE_TO_PERMISSION
from porterchain_api.collaboration_engine.lead_ingest_service import (
    CanonicalLeadEvent,
    LeadIngestService,
)
from porterchain_api.collaboration_engine.lead_nurture import apply_nurture_after_ingest
from porterchain_api.crm_models import CrmConversation, CrmConversationMessage, CrmLead, CrmSalesTask
from porterchain_api.db import get_db
from porterchain_api.domain.crm_states import LeadStatus
from porterchain_api.main import app
from porterchain_api.routers.admin import leads as leads_mod
from porterchain_api.schemas_crm import LeadOut

REPO = Path(__file__).resolve().parents[3]
API_SRC = REPO / "apps" / "api" / "src" / "porterchain_api"
ADMIN_SRC = REPO / "apps" / "admin" / "src"
ENV_EXAMPLE = REPO / "env" / "api.env.example"

# --------------------------------------------------------------------------- #
# Forbidden import roots inside the leads CRM spine (architecture firewall)
# --------------------------------------------------------------------------- #
_FORBIDDEN_IMPORT_SUBSTRINGS = (
    "valhalla",
    "osrm",
    "vroom",
    "cuopt",
    "fleetbase",
    "socketcluster",
    "shopify",
    "firebase",
    "google.maps",
    "googlemaps",
    "distance_matrix",
    "directions_api",
)

_LEAD_SPINE_GLOBS = (
    "collaboration_engine/lead_*.py",
    "collaboration_engine/crm_leads.py",
    "collaboration_engine/crm_deals.py",
    "collaboration_engine/crm_service.py",
    "collaboration_engine/crm_helpers.py",
    "collaboration_engine/lead_channel_adapters.py",
    "routers/admin/leads.py",
    "routers/lead_webhooks.py",
    "routers/public_inquiries.py",
    "admin_engine/lead_ingest_settings.py",
    "intelligence_engine/lead_assist.py",
    "domain/crm_states.py",
    "crm_models.py",
    "schemas_crm.py",
)

# Admin page → client API methods → backend routes (page contract)
_PAGE_API_MATRIX: dict[str, list[tuple[str, str]]] = {
    "/leads": [
        ("GET", "/v1/admin/leads"),
        ("POST", "/v1/admin/leads"),
        ("GET", "/v1/admin/leads/metrics"),
    ],
    "/leads/pipeline": [
        ("GET", "/v1/admin/leads/pipeline"),
    ],
    "/leads/calendar": [
        ("GET", "/v1/admin/leads/calendar"),
    ],
    "/leads/[id]": [
        ("GET", "/v1/admin/leads/{id}"),
        ("PATCH", "/v1/admin/leads/{id}"),
        ("POST", "/v1/admin/leads/{id}/convert"),
        ("GET", "/v1/admin/leads/{id}/conversations"),
        ("GET", "/v1/admin/leads/{id}/identities"),
        ("GET", "/v1/admin/leads/{id}/assist"),
        ("POST", "/v1/admin/leads/{id}/assist/decide"),
        ("POST", "/v1/admin/leads/{id}/merge"),
        ("DELETE", "/v1/admin/leads/{id}"),
    ],
    "settings/LeadIngestPanel": [
        ("GET", "/v1/admin/settings/lead-ingest"),
        ("PUT", "/v1/admin/settings/lead-ingest"),
    ],
    "public_webhooks": [
        ("GET", "/v1/public/leads/webhooks/meta"),
        ("POST", "/v1/public/leads/webhooks/meta"),
        ("POST", "/v1/public/leads/webhooks/google"),
        ("POST", "/v1/public/leads/webhooks/linkedin"),
        ("POST", "/v1/public/leads/webhooks/x"),
        ("POST", "/v1/public/leads/webhooks/youtube"),
    ],
}


@pytest.fixture
def admin_client(db, monkeypatch):
    monkeypatch.setattr(leads_mod, "require_module", lambda ctx, module: None)
    import porterchain_api.routers.admin.leads_360 as leads_360_mod
    import porterchain_api.routers.admin.settings as settings_mod
    from porterchain_api.admin_engine import rbac as rbac_mod
    from porterchain_api.user_models import PorterchainUser

    # settings._invoke calls require_module from rbac import inside settings module
    # assist / calendar / merge live on leads_360 (separate import binding)
    monkeypatch.setattr(leads_360_mod, "require_module", lambda ctx, module: None)
    monkeypatch.setattr(settings_mod, "require_module", lambda ctx, module: None)
    monkeypatch.setattr(rbac_mod, "require_module", lambda ctx, module: None)

    pc = PorterchainUser(
        id="user-matrix",
        clerk_user_id="clerk-leads-matrix",
        email="leads-matrix@porterchain.com",
        role="super_admin",
        status="active",
    )
    db.merge(pc)
    db.flush()

    admin = AdminContext(
        user=AdminUser(
            clerk_user_id="clerk-leads-matrix",
            email="leads-matrix@porterchain.com",
            role="super_admin",
            porterchain_user_id="user-matrix",
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
    """Unique NANP-ish phone from suffix — avoids identity merge across committed tests."""
    hexish = "".join(c for c in s.lower() if c in "0123456789abcdef") or "4242"
    n = int(hexish[:12] or "4242", 16) % 10_000_000
    return f"+1416{n:07d}"


def _seed(db, **kw) -> CrmLead:
    s = kw.pop("suffix", _suffix())
    row = CrmLead(
        company_name=kw.pop("company_name", f"Matrix Co {s}"),
        email=kw.pop("email", f"matrix-{s}@acme.test"),
        phone=kw.pop("phone", _phone(s)),
        primary_contact_name=kw.pop("primary_contact_name", "Matrix Contact"),
        source=kw.pop("source", "website_contact"),
        channel=kw.pop("channel", "website"),
        status=kw.pop("status", "new"),
        priority=kw.pop("priority", "medium"),
        intent_type=kw.pop("intent_type", "merchant"),
        decision_status=kw.pop("decision_status", "new"),
        **kw,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _route_paths() -> set[str]:
    """Collect paths from lead-owning routers (app.routes may nest/mount)."""
    from porterchain_api.routers import admin, lead_webhooks, public_inquiries

    paths: set[str] = set()
    for router in (admin.router, lead_webhooks.router, public_inquiries.router):
        for r in router.routes:
            p = getattr(r, "path", None)
            if p:
                paths.add(p)
    return paths


# =========================================================================== #
# A. Architecture & filesystem — pages / client / spine exist
# =========================================================================== #


class TestAdminLeadsFilesystem:
    def test_admin_pages_exist(self) -> None:
        pages = [
            ADMIN_SRC / "app/(ops)/leads/page.tsx",
            ADMIN_SRC / "app/(ops)/leads/pipeline/page.tsx",
            ADMIN_SRC / "app/(ops)/leads/calendar/page.tsx",
            ADMIN_SRC / "app/(ops)/leads/[id]/page.tsx",
            ADMIN_SRC / "components/settings/panels/LeadIngestPanel.tsx",
            ADMIN_SRC / "lib/leads.ts",
            ADMIN_SRC / "lib/admin-nav.ts",
            ADMIN_SRC / "components/crm/primitives.tsx",
            ADMIN_SRC / "components/crm/ActivityTimeline.tsx",
            ADMIN_SRC / "components/crm/EntityTasks.tsx",
        ]
        missing = [str(p.relative_to(REPO)) for p in pages if not p.is_file()]
        assert not missing, f"missing admin lead surfaces: {missing}"

    def test_nav_growth_links_cover_all_lead_pages(self) -> None:
        nav = (ADMIN_SRC / "lib/admin-nav.ts").read_text(encoding="utf-8")
        assert 'href: "/leads"' in nav
        assert 'href: "/leads/pipeline"' in nav
        # Sales nav is lean (Inbox / Pipeline / Call list); Calendar, Lead Agent and
        # Attribution stay one click away in the Inbox "More" menu.
        assert 'href: "/leads/today"' in nav
        inbox = (ADMIN_SRC / "components/leads/LeadsListClient.tsx").read_text(encoding="utf-8")
        for href in ('href="/leads/calendar"', 'href="/leads/agent"'):
            assert href in inbox
        assert "DRIVER_LEAD_SOURCE" in nav
        assert "website_driver_partner" in nav

    def test_leads_api_client_methods_match_pages(self) -> None:
        text = (ADMIN_SRC / "lib/leads.ts").read_text(encoding="utf-8")
        for method in (
            "list",
            "metrics",
            "pipeline",
            "detail",
            "create",
            "update",
            "remove",
            "conversations",
            "identities",
            "convert",
            "assist",
            "assistDecide",
            "calendar",
            "resolveMerge",
            "referralCredits",
        ):
            assert re.search(rf"\b{method}\b\s*\(", text), f"leadsApi missing {method}"

    def test_page_imports_leads_api(self) -> None:
        for rel in (
            "components/leads/LeadsListClient.tsx",
            "components/leads/LeadsPipelineClient.tsx",
            "components/leads/LeadsCalendarClient.tsx",
            "components/leads/LeadDetailClient.tsx",
        ):
            text = (ADMIN_SRC / rel).read_text(encoding="utf-8")
            assert "leadsApi" in text
            assert "useAdminAuth" in text  # Clerk session handshake


# =========================================================================== #
# B. FastAPI route registry — every page contract is mounted
# =========================================================================== #


class TestAdminLeadsRouteRegistry:
    def test_page_matrix_routes_registered(self) -> None:
        paths = _route_paths()
        required = [
            "/v1/admin/leads",
            "/v1/admin/leads/metrics",
            "/v1/admin/leads/pipeline",
            "/v1/admin/leads/calendar",
            "/v1/admin/leads/{lead_id}",
            "/v1/admin/leads/{lead_id}/convert",
            "/v1/admin/leads/{lead_id}/conversations",
            "/v1/admin/leads/{lead_id}/identities",
            "/v1/admin/leads/{lead_id}/assist",
            "/v1/admin/leads/{lead_id}/assist/decide",
            "/v1/admin/leads/{lead_id}/merge",
            "/v1/admin/settings/lead-ingest",
            "/v1/public/leads/webhooks/meta",
            "/v1/public/leads/webhooks/google",
            "/v1/public/leads/webhooks/linkedin",
            "/v1/public/leads/webhooks/x",
            "/v1/public/leads/webhooks/youtube",
        ]
        missing = [r for r in required if r not in paths]
        assert not missing, f"unmounted lead routes: {missing}\nknown={sorted(p for p in paths if 'lead' in p)}"

    def test_clerk_module_keys_registered(self) -> None:
        assert "crm" in ADMIN_MODULE_TO_PERMISSION
        assert "crm_read" in ADMIN_MODULE_TO_PERMISSION
        assert "settings" in ADMIN_MODULE_TO_PERMISSION


# =========================================================================== #
# C. Architecture firewall — forbidden systems stay out of lead spine
# =========================================================================== #


def _iter_lead_spine_files() -> list[Path]:
    files: list[Path] = []
    for pattern in _LEAD_SPINE_GLOBS:
        files.extend(API_SRC.glob(pattern))
    # Admin leads UI (must not call maps/fleet/shopify clients)
    files.extend(
        [
            ADMIN_SRC / "lib/leads.ts",
            ADMIN_SRC / "app/(ops)/leads/page.tsx",
            ADMIN_SRC / "app/(ops)/leads/pipeline/page.tsx",
            ADMIN_SRC / "app/(ops)/leads/calendar/page.tsx",
            ADMIN_SRC / "app/(ops)/leads/[id]/page.tsx",
            ADMIN_SRC / "components/settings/panels/LeadIngestPanel.tsx",
        ]
    )
    return [f for f in files if f.is_file()]


def _forbidden_hits(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore").lower()
    hits = []
    for needle in _FORBIDDEN_IMPORT_SUBSTRINGS:
        if needle in text:
            # Allow comments about "Google lead webhook" / "google_ads" channel / "google_business"
            if needle in ("google.maps", "googlemaps", "distance_matrix", "directions_api"):
                hits.append(needle)
            elif needle == "firebase":
                hits.append(needle)
            elif needle in ("valhalla", "osrm", "vroom", "cuopt", "fleetbase", "socketcluster", "shopify"):
                hits.append(needle)
    return hits


class TestLeadsArchitectureFirewall:
    def test_lead_spine_has_no_ops_routing_imports(self) -> None:
        """CRM must not pull Valhalla/OSRM/VROOM/Fleetbase/Shopify/Firebase."""
        violations: dict[str, list[str]] = {}
        for path in _iter_lead_spine_files():
            # Skip pure channel name mentions in adapters by AST-import scan for .py
            if path.suffix == ".py":
                tree = ast.parse(path.read_text(encoding="utf-8"))
                imported: list[str] = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        imported.extend(a.name.lower() for a in node.names)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        imported.append(node.module.lower())
                bad = [
                    m
                    for m in imported
                    if any(
                        f in m
                        for f in (
                            "valhalla",
                            "osrm",
                            "vroom",
                            "cuopt",
                            "fleetbase",
                            "socketcluster",
                            "shopify",
                            "firebase",
                            "googlemaps",
                            "google.maps",
                        )
                    )
                ]
                if bad:
                    violations[str(path.relative_to(REPO))] = bad
            else:
                # TS: no maps / firebase / fleet / shopify / routing clients on leads pages
                text = path.read_text(encoding="utf-8").lower()
                for bad in (
                    "@vis.gl/react-google-maps",
                    "@porterchain/maps",
                    "firebase/",
                    "from \"firebase",
                    "from 'firebase",
                    "fleetbase",
                    "socketcluster",
                    "shopify",
                    "valhalla",
                    "osrm",
                    "vroom",
                ):
                    if bad in text:
                        violations.setdefault(str(path.relative_to(REPO)), []).append(bad)
        assert not violations, f"leads spine imports forbidden systems: {violations}"

    def test_leads_pages_do_not_embed_map_tiles(self) -> None:
        for rel in (
            "app/(ops)/leads/page.tsx",
            "app/(ops)/leads/pipeline/page.tsx",
            "app/(ops)/leads/calendar/page.tsx",
            "app/(ops)/leads/[id]/page.tsx",
        ):
            text = (ADMIN_SRC / rel).read_text(encoding="utf-8")
            assert "@porterchain/maps" not in text
            assert "GoogleMap" not in text
            assert "useMap" not in text


# =========================================================================== #
# D. Page-level API development tests
# =========================================================================== #


class TestInboxPageApi:
    """ /leads — list, filters, capture, metrics, driver inbox """

    def test_list_and_metrics(self, admin_client, db) -> None:
        s = _suffix()
        lead = _seed(db, suffix=s, company_name=f"Inbox {s}")
        listed = admin_client.get("/v1/admin/leads", params={"search": s})
        assert listed.status_code == 200
        assert any(r["id"] == lead.id for r in listed.json()["items"])
        metrics = admin_client.get("/v1/admin/leads/metrics", params={"days": 7})
        assert metrics.status_code == 200
        body = metrics.json()
        assert body["window_days"] == 7
        assert "ingest" in body and "leads" in body and "sla" in body and "capi" in body

    def test_driver_application_filter(self, admin_client, db) -> None:
        s = _suffix()
        driver = _seed(
            db,
            suffix=s,
            source="website_driver_partner",
            channel="website",
            intent_type="driver_partner",
            company_name=f"Driver App {s}",
        )
        _seed(db, suffix=f"m{s[:6]}", source="website_contact", company_name=f"Merchant {s}")
        rows = admin_client.get(
            "/v1/admin/leads", params={"source": "website_driver_partner", "search": s}
        ).json()["items"]
        assert any(r["id"] == driver.id for r in rows)
        assert all(r["source"] == "website_driver_partner" for r in rows)

    def test_manual_capture_and_filters(self, admin_client) -> None:
        s = _suffix()
        created = admin_client.post(
            "/v1/admin/leads",
            json={
                "company_name": f"Capture {s}",
                "email": f"cap-{s}@t.test",
                "phone": _phone(s),
                "source": "phone_call",
                "channel": "phone_call",
                "priority": "urgent",
                "consent": {"marketing": True, "sms": False, "legal_basis": "consent"},
            },
        )
        assert created.status_code == 201, created.text
        LeadOut.model_validate(created.json())
        filtered = admin_client.get(
            "/v1/admin/leads",
            params={"channel": "phone_call", "priority": "urgent", "search": s},
        )
        assert filtered.status_code == 200
        assert any(r["id"] == created.json()["id"] for r in filtered.json()["items"])


class TestPipelinePageApi:
    def test_pipeline_board_shape(self, admin_client, db) -> None:
        s = _suffix()
        lead = _seed(db, suffix=s, company_name=f"Pipe {s}", status="new")
        res = admin_client.get("/v1/admin/leads/pipeline", params={"search": s})
        assert res.status_code == 200
        cols = res.json()
        assert isinstance(cols, list)
        assert cols, "pipeline must return stage columns"
        for col in cols:
            assert "stage" in col and "cards" in col and "count" in col
            assert "lead_count" in col and "deal_count" in col
        cards = [c for col in cols for c in col["cards"]]
        assert any(c.get("id") == lead.id for c in cards)


class TestCalendarPageApi:
    def test_calendar_returns_lead_call_meeting_tasks(self, admin_client, db) -> None:
        s = _suffix()
        lead = _seed(db, suffix=s)
        due = datetime.now(UTC) + timedelta(days=1)
        task = CrmSalesTask(
            title=f"Call {s}",
            task_type="call",
            entity_type="lead",
            entity_id=lead.id,
            due_at=due,
            status="open",
            priority="medium",
        )
        db.add(task)
        db.commit()
        res = admin_client.get(
            "/v1/admin/leads/calendar",
            params={
                "due_after": (due - timedelta(days=1)).isoformat(),
                "due_before": (due + timedelta(days=2)).isoformat(),
            },
        )
        assert res.status_code == 200
        rows = res.json()
        assert any(r.get("id") == task.id or r.get("title") == task.title for r in rows)


class TestDetailPageApi:
    def test_detail_conversations_identities_assist_patch(self, admin_client, db) -> None:
        s = _suffix()
        lead = _seed(db, suffix=s, company_name=f"Detail {s}")
        convo = CrmConversation(lead_id=lead.id, channel="website", status="open")
        db.add(convo)
        db.flush()
        db.add(
            CrmConversationMessage(
                conversation_id=convo.id,
                direction="inbound",
                body="Need capacity quote",
                actor_type="lead",
            )
        )
        db.commit()

        detail = admin_client.get(f"/v1/admin/leads/{lead.id}")
        assert detail.status_code == 200
        LeadOut.model_validate(detail.json())

        convos = admin_client.get(f"/v1/admin/leads/{lead.id}/conversations")
        assert convos.status_code == 200
        assert any(c["id"] == convo.id for c in convos.json())

        ids = admin_client.get(f"/v1/admin/leads/{lead.id}/identities")
        assert ids.status_code == 200

        assist = admin_client.get(f"/v1/admin/leads/{lead.id}/assist")
        assert assist.status_code == 200
        assert "draft_reply" in assist.json() or "summary" in assist.json()

        decide = admin_client.post(
            f"/v1/admin/leads/{lead.id}/assist/decide",
            json={
                "proposal_id": "test-proposal",
                "decision": "reject",
            },
        )
        assert decide.status_code == 200
        assert decide.json().get("ok") is True

        patched = admin_client.patch(
            f"/v1/admin/leads/{lead.id}",
            json={"status": "contacted", "internal_notes": f"note-{s}"},
        )
        assert patched.status_code == 200
        assert patched.json()["status"] == "replied"  # legacy name normalized

    def test_convert_and_referral_credits_endpoint(self, admin_client, db) -> None:
        s = _suffix()
        lead = _seed(db, suffix=s, primary_contact_name="Convert Me")
        with patch(
            "porterchain_api.collaboration_engine.lead_capi.emit_lead_conversion_events",
            return_value={"emitted": False},
        ):
            res = admin_client.post(
                f"/v1/admin/leads/{lead.id}/convert",
                json={"create_deal": True, "outcome": "merchant"},
            )
        assert res.status_code == 200
        assert res.json().get("company_id")

        credits = admin_client.get("/v1/admin/leads/referral-credits")
        assert credits.status_code == 200
        assert isinstance(credits.json(), list)


class TestLeadIngestSettingsPanelApi:
    def test_lead_ingest_settings_get_shape(self, admin_client) -> None:
        from porterchain_api.admin_engine.lead_ingest_settings import lead_ingest_settings_status
        from porterchain_api.config import get_settings

        status = lead_ingest_settings_status(get_settings())
        assert "secrets" in status
        assert "visible" in status
        assert "doppler" in status
        assert "META_APP_SECRET" in status["secrets"] or any(
            "META" in k for k in status["secrets"]
        )

        res = admin_client.get("/v1/admin/settings/lead-ingest")
        assert res.status_code == 200, res.text
        body = res.json()
        assert "secrets" in body and "visible" in body
        # Never leak raw secret values in status payload
        blob = str(body)
        assert "sk_live" not in blob
        assert "EAAG" not in blob  # Meta token prefix pattern if ever leaked


# =========================================================================== #
# E. Real handshakes — email nurture, webhooks, public inquiry, env/docker
# =========================================================================== #


class TestLeadHandshakes:
    def test_nurture_email_queue_respects_consent(self, db) -> None:
        s = _suffix()
        lead = _seed(
            db,
            suffix=s,
            consent={"marketing": True},
            email=f"nurture-{s}@acme.test",
        )
        result = apply_nurture_after_ingest(
            db, lead, created=True, website_url="https://porterchain.com"
        )
        assert result["scheduled"] >= 1
        # Intro may enqueue depending on redis/queue availability — bool is fine
        assert "intro_email" in result
        tasks = (
            db.query(CrmSalesTask)
            .filter(CrmSalesTask.entity_id == lead.id, CrmSalesTask.entity_type == "lead")
            .all()
        )
        assert any(t.task_type in ("email", "call", "follow_up") for t in tasks)

    def test_nurture_skips_intro_without_consent(self, db) -> None:
        s = _suffix()
        lead = _seed(db, suffix=s, consent={"marketing": False}, email=f"noc-{s}@acme.test")
        result = apply_nurture_after_ingest(
            db, lead, created=True, website_url="https://porterchain.com"
        )
        assert result["intro_email"] is False

        skipped = apply_nurture_after_ingest(
            db, lead, created=False, website_url="https://porterchain.com"
        )
        assert skipped == {"scheduled": 0, "intro_email": False}

    def test_webhook_routes_require_secrets_or_reject(self, admin_client) -> None:
        # Unsigned Meta POST must fail closed — never 2xx without auth
        res = admin_client.post("/v1/public/leads/webhooks/meta", json={"entry": []})
        assert res.status_code in (400, 401, 403, 422, 503)
        assert res.status_code < 500 or res.status_code == 503
        google = admin_client.post(
            "/v1/public/leads/webhooks/google",
            json={"email": "x@y.com", "company": "X"},
        )
        assert google.status_code in (400, 401, 403, 422, 503)
        assert google.status_code != 200

    def test_ingest_bus_from_website_source(self, db) -> None:
        s = _suffix()
        result = LeadIngestService().ingest(
            db,
            CanonicalLeadEvent(
                channel="website",
                source="website_quote",
                provider="website",
                external_event_id=f"inq-{s}",
                company_name=f"Inquiry {s}",
                email=f"inq-{s}@acme.test",
                phone=_phone(s),
                message="Website form",
            ),
        )
        assert result.created is True
        assert result.lead.status == LeadStatus.NEW.value

    def test_env_example_documents_lead_secrets(self) -> None:
        text = ENV_EXAMPLE.read_text(encoding="utf-8")
        for key in (
            "PUBLIC_INGEST_API_KEY",
            "META_APP_SECRET",
            "META_WEBHOOK_VERIFY_TOKEN",
            "GOOGLE_LEAD_WEBHOOK_SECRET",
            "SOCIAL_LEAD_WEBHOOK_SECRET",
            "META_CAPI_ACCESS_TOKEN",
            "LEAD_TERRITORY_MAP_JSON",
            "LEAD_ROUND_ROBIN_JSON",
            "LEAD_SLA_MINUTES_JSON",
            "REFERRAL_CREDIT_CENTS",
        ):
            assert key in text, f"api.env.example missing {key}"

    def test_crm_lead_model_columns_for_ui(self) -> None:
        """Detail/inbox UI fields must exist on CrmLead ORM."""
        cols = {c.name for c in CrmLead.__table__.columns}
        for required in (
            "company_name",
            "email",
            "phone",
            "source",
            "channel",
            "intent_type",
            "decision_status",
            "status",
            "priority",
            "lead_score",
            "merge_candidate_of",
            "sla_first_response_due_at",
            "consent",
            "custom_fields",
            "referred_by_merchant_id",
            "company_id",
            "deal_id",
        ):
            assert required in cols


# =========================================================================== #
# F. UI ownership — Vitest/RTL owns page UX; pytest keeps architecture firewall
# =========================================================================== #


class TestAdminLeadsUiOwnership:
    """Page UX moved to Vitest + Testing Library (+ Playwright stubs).

    See:
      apps/admin/src/lib/leads.test.ts
      apps/admin/src/app/(ops)/leads/**/*.test.tsx
      apps/admin/e2e/leads.p0.spec.ts
    """

    def test_vitest_harness_and_lead_specs_exist(self) -> None:
        required = [
            ADMIN_SRC.parent / "vitest.config.ts",
            ADMIN_SRC / "test" / "setup.tsx",
            ADMIN_SRC / "lib" / "leads.test.ts",
            ADMIN_SRC / "app" / "(ops)" / "leads" / "page.test.tsx",
            ADMIN_SRC / "app" / "(ops)" / "leads" / "pipeline" / "page.test.tsx",
            ADMIN_SRC / "app" / "(ops)" / "leads" / "calendar" / "page.test.tsx",
            ADMIN_SRC / "app" / "(ops)" / "leads" / "[id]" / "page.test.tsx",
            ADMIN_SRC / "components" / "settings" / "panels" / "LeadIngestPanel.test.tsx",
            ADMIN_SRC.parent / "e2e" / "leads.p0.spec.ts",
        ]
        missing = [str(p.relative_to(REPO)) for p in required if not p.is_file()]
        assert not missing, f"missing modern UI test harness files: {missing}"

    def test_admin_package_exposes_vitest_scripts(self) -> None:
        pkg = json.loads((ADMIN_SRC.parent / "package.json").read_text(encoding="utf-8"))
        scripts = pkg.get("scripts") or {}
        assert scripts.get("test") == "vitest run"
        assert "vitest" in (pkg.get("devDependencies") or {})
        assert "@testing-library/react" in (pkg.get("devDependencies") or {})
        assert "@playwright/test" in (pkg.get("devDependencies") or {})



# =========================================================================== #
# G. Intentional non-scope — document what we correctly do NOT test as leads
# =========================================================================== #


class TestLeadsIntentionalNonScope:
    """These systems are real in PorterChain but out of CRM leads scope.

    Jeff Dean: testing a Shopify→lead or Valhalla→lead path would encode the
    wrong architecture. We assert absence instead.
    """

    def test_no_shopify_lead_router(self) -> None:
        paths = _route_paths()
        assert not any("shopify" in p and "lead" in p for p in paths)

    def test_no_fleetbase_lead_router(self) -> None:
        paths = _route_paths()
        assert not any("fleetbase" in p and "lead" in p for p in paths)

    def test_no_vroom_valhalla_osrm_lead_router(self) -> None:
        paths = _route_paths()
        for vendor in ("vroom", "valhalla", "osrm"):
            assert not any(vendor in p and "lead" in p for p in paths)

    def test_page_matrix_documentation_complete(self) -> None:
        # Guardrail: if a new admin lead page is added, extend this matrix.
        expected_pages = {
            "/leads",
            "/leads/pipeline",
            "/leads/calendar",
            "/leads/[id]",
            "settings/LeadIngestPanel",
            "public_webhooks",
        }
        assert set(_PAGE_API_MATRIX) == expected_pages
