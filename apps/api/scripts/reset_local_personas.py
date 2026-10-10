"""Wipe local Docker Postgres (except staff + passkeys) and seed complete personas.

Keeps:
  - alembic_version, system_config, pricing catalog, blog_posts
  - Real staff admin_users (admin@, seed-admin@, porterchaininc@, anyone with a passkey)
  - staff_webauthn_credentials and those admins' porterchain_users / identity_links / user_emails

Seeds one fully-populated merchant (company file + CRM company + contacts),
one approved driver (documents + vehicle), and one retail customer.

Usage:
    cd apps/api && PYTHONPATH=src python scripts/reset_local_personas.py
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import text

from porterchain_api.admin_models import (
    AdminUser,
    Driver,
    MerchantContract,
    StaffWebAuthnCredential,
    Vehicle,
)
from porterchain_api.auth.dev import (
    DEV_CUSTOMER_EMAIL,
    DEV_CUSTOMER_SUBJECT,
    DEV_MERCHANT_EMAIL,
    DEV_MERCHANT_SUBJECT,
)
from porterchain_api.booking_engine.numbers import generate_customer_reference
from porterchain_api.booking_engine.stop_sync import persist_address
from porterchain_api.booking_models import Customer
from porterchain_api.crm_models import (
    CrmActivity,
    CrmCompany,
    CrmContact,
    CrmContract,
    CrmDocument,
)
from porterchain_api.db import SessionLocal, init_db
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.domain.contacts import TEAM_ROLE_TAG
from porterchain_api.domain.crm_states import CompanyMerchantStatus, ContractStatus
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.driver_engine.document_store import record_document
from porterchain_api.identity_models import IdentityLink
from porterchain_api.merchant_engine.organization_sync import project_merchant_company, stamp_identity_meta
from porterchain_api.merchant_engine.provision import create_onboarding_merchant
from porterchain_api.merchant_models import (
    MerchantApiKey,
    MerchantRecipient,
    MerchantUser,
    SavedAddress,
)
from porterchain_api.unified_identity_models import UserEmail
from porterchain_api.user_models import PorterchainUser

KEEP_ADMIN_EMAILS = {
    "admin@porterchain.com",
    "seed-admin@porterchain.com",
    "porterchaininc@gmail.com",
}

KEEP_TABLES = {
    "alembic_version",
    "admin_users",
    "staff_webauthn_credentials",
    "porterchain_users",
    "identity_links",
    "user_emails",
    "system_config",
    "blog_posts",
    "pricing_tariffs",
    "pricing_fsa_rates",
    "pricing_zones",
}

DEV_ORG = "dev_merchant_org"
NOW = datetime.now(UTC)

WAREHOUSE = {
    "formatted": "100 Queen St W, Toronto, ON M5H 2N2",
    "line1": "100 Queen St W",
    "city": "Toronto",
    "region": "ON",
    "postal": "M5H 2N2",
    "country": "CA",
    "lat": 43.6532,
    "lng": -79.3832,
    "place_id": "ChIJpTvG15DL1IkRd8S0KlBVNTI",
    "contact_name": "Receiving Dock",
    "phone": "+1 416-555-2100",
}

BILLING_ADDRESS = {
    "formatted": "100 Queen St W, Suite 1200, Toronto, ON M5H 2N2",
    "line1": "100 Queen St W",
    "line2": "Suite 1200",
    "city": "Toronto",
    "region": "ON",
    "postal": "M5H 2N2",
    "country": "CA",
    "lat": 43.6532,
    "lng": -79.3832,
}

CUSTOMER_HOME = {
    "formatted": "220 King St W, Toronto, ON M5H 1K4",
    "line1": "220 King St W",
    "city": "Toronto",
    "region": "ON",
    "postal": "M5H 1K4",
    "country": "CA",
    "lat": 43.6475,
    "lng": -79.3860,
    "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
    "contact_name": "Priya Sharma",
    "phone": "+1 416-555-4401",
}


def _uuid() -> str:
    return str(uuid.uuid4())


def _keep_admin_ids(db) -> set[str]:
    keep: set[str] = set()
    for row in db.query(AdminUser).all():
        email = (row.email or "").strip().lower()
        if email in KEEP_ADMIN_EMAILS:
            keep.add(row.id)
    for cred in db.query(StaffWebAuthnCredential).all():
        keep.add(cred.admin_user_id)
    return keep


def wipe_except_staff(db) -> dict[str, int]:
    keep_admins = _keep_admin_ids(db)
    if not keep_admins:
        raise RuntimeError("Refusing to wipe: no staff admin rows matched keep list or passkeys.")

    tables = [
        row[0]
        for row in db.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
        )
    ]
    wipe = [t for t in tables if t not in KEEP_TABLES]
    db.commit()
    db.execute(text("SET session_replication_role = replica"))
    if wipe:
        quoted = ", ".join(f'"{t}"' for t in wipe)
        db.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))
    db.execute(text("SET session_replication_role = DEFAULT"))
    db.commit()
    db.expire_all()

    keep_admins = _keep_admin_ids(db)
    keep_users = {
        admin.porterchain_user_id
        for admin in db.query(AdminUser).filter(AdminUser.id.in_(keep_admins)).all()
        if admin.porterchain_user_id
    }

    junk_admins = db.query(AdminUser).filter(AdminUser.id.notin_(keep_admins)).all()
    junk_admin_ids = [a.id for a in junk_admins]
    if junk_admin_ids:
        db.query(StaffWebAuthnCredential).filter(
            StaffWebAuthnCredential.admin_user_id.in_(junk_admin_ids)
        ).delete(synchronize_session=False)
        db.query(AdminUser).filter(AdminUser.id.in_(junk_admin_ids)).delete(synchronize_session=False)

    drop_users = [u.id for u in db.query(PorterchainUser).all() if u.id not in keep_users]
    if drop_users:
        db.query(IdentityLink).filter(IdentityLink.platform_user_id.in_(drop_users)).delete(
            synchronize_session=False
        )
        db.query(UserEmail).filter(UserEmail.user_id.in_(drop_users)).delete(synchronize_session=False)
        db.query(PorterchainUser).filter(PorterchainUser.id.in_(drop_users)).delete(
            synchronize_session=False
        )

    db.execute(text("DELETE FROM system_config WHERE key LIKE 'test.%'"))
    db.commit()
    return {
        "kept_admins": len(keep_admins),
        "removed_admins": len(junk_admin_ids),
        "truncated_tables": len(wipe),
    }


def _pc_user(
    db,
    *,
    clerk_user_id: str,
    email: str,
    phone: str,
    role: str,
    workspace: str,
    profile: dict,
) -> PorterchainUser:
    user = PorterchainUser(
        clerk_user_id=clerk_user_id,
        email=email,
        phone=phone,
        role=role,
        status="active",
        onboarding_status="complete",
        default_workspace=workspace,
        profile=profile,
        last_synced_at=NOW,
    )
    db.add(user)
    db.flush()
    db.add(
        UserEmail(
            user_id=user.id,
            normalized_email=email.lower(),
            is_verified=True,
            is_primary=True,
            source="local_seed",
        )
    )
    db.add(
        IdentityLink(
            clerk_user_id=clerk_user_id,
            provider="clerk",
            issuer="https://clerk.porterchain.local",
            subject=clerk_user_id,
            is_current=True,
            is_legacy=False,
            linked_at=NOW,
            email=email,
            user_type=workspace,
            platform_user_id=user.id,
            platform_org_id=DEV_ORG if workspace == "merchant" else None,
            last_synced_at=NOW,
        )
    )
    return user


def seed_merchant(db, admin: AdminUser) -> tuple:
    merchant = create_onboarding_merchant(
        db,
        company_name="Maple Leaf Wholesale Inc.",
        legal_name="Maple Leaf Wholesale Incorporated",
        email=DEV_MERCHANT_EMAIL,
        phone="+1 416-555-2100",
        hst_number="876543210RT0001",
        business_number="876543210",
        billing_address=BILLING_ADDRESS,
        preferred_vehicles=["cargo_van", "sprinter_van"],
        status=MerchantStatus.ACTIVE.value,
        payment_terms="NET_30",
        clerk_org_id=DEV_ORG,
        activated_at=NOW - timedelta(days=14),
        pricing_config={
            "gta_rate": {"base_cents": 1800, "per_km_cents": 95},
            "surcharges": {"fuel_percent": 5.0, "after_hours_cents": 1500},
            "size_tiers": {"small": 0, "medium": 400, "large": 900},
        },
        profile={
            "vertical": "wholesale",
            "service_area": "Ontario — GTA",
            "source": "local_persona_reset",
            "enterprise": {"support_tier": "priority", "account_manager": "Ava Chen"},
            "settings": {
                "notifications": {
                    "order_booked": True,
                    "order_delivered": True,
                    "order_failed": True,
                    "invoice_generated": True,
                    "payment_received": True,
                    "claim_updates": True,
                    "support_replies": True,
                    "weekly_summary": True,
                    "channels": {"email": True, "in_app": True},
                },
                "branding": {
                    "logo_url": "https://storage.porterchain.local/seed/maple-leaf-logo.png",
                    "primary_color": "#1e3a5f",
                    "accent_color": "#f59e0b",
                    "tracking_page_message": "Maple Leaf Wholesale — on the way.",
                    "tracking_domain": "track.mapleleaf.example",
                    "white_label_enabled": False,
                },
                "billing_contacts": [
                    {
                        "id": _uuid(),
                        "name": "Anita Patel",
                        "email": "ap@mapleleaf.example",
                        "phone": "+1 416-555-2104",
                        "role": "accounts_payable",
                        "is_primary": True,
                    }
                ],
                "warehouses": [
                    {
                        "id": _uuid(),
                        "name": "Queen Street DC",
                        "formatted": WAREHOUSE["formatted"],
                        "lat": WAREHOUSE["lat"],
                        "lng": WAREHOUSE["lng"],
                        "postal": WAREHOUSE["postal"],
                        "is_default": True,
                    }
                ],
                "documents": [
                    {
                        "id": _uuid(),
                        "name": "WSIB clearance certificate",
                        "type": "insurance",
                        "reference": "WSIB-2026-4411",
                        "uploaded_at": NOW.isoformat(),
                        "uploaded_by": admin.id,
                    }
                ],
                "tax": {"tax_exempt": False, "tax_region": "ON"},
            },
            "privacy": {"status": "none"},
            "integrations": {"shopify": {"connected": False}},
        },
    )
    merchant.website = "https://mapleleaf.example"
    merchant.industry = "Wholesale / Distribution"
    merchant.billing_cycle = "MONTHLY"
    merchant.credit_limit_cents = 250_000_00
    merchant.stripe_connect_account_id = "acct_local_mapleleaf"
    merchant.cod_enabled = True
    merchant.delivery_zones = ["gta", "hamilton", "peel"]
    stamp_identity_meta(merchant, actor="admin", actor_id=admin.id)
    db.flush()

    owner = _pc_user(
        db,
        clerk_user_id=DEV_MERCHANT_SUBJECT,
        email=DEV_MERCHANT_EMAIL,
        phone="+1 416-555-2101",
        role="merchant_owner",
        workspace="merchant",
        profile={
            "first_name": "Jordan",
            "last_name": "Lee",
            "title": "Owner",
            "department": "Operations",
        },
    )
    seat = MerchantUser(
        merchant_id=merchant.id,
        clerk_user_id=DEV_MERCHANT_SUBJECT,
        porterchain_user_id=owner.id,
        email=DEV_MERCHANT_EMAIL,
        role=MerchantRole.OWNER.value,
        is_active=True,
    )
    db.add(seat)
    db.flush()

    warehouse_addr = persist_address(db, WAREHOUSE)
    db.add(
        SavedAddress(
            merchant_id=merchant.id,
            label="Queen Street DC",
            address_type="warehouse",
            formatted=WAREHOUSE["formatted"],
            place_id=WAREHOUSE["place_id"],
            lat=WAREHOUSE["lat"],
            lng=WAREHOUSE["lng"],
            postal=WAREHOUSE["postal"],
            address_id=warehouse_addr.id,
            is_default=True,
        )
    )
    drop_addr = persist_address(
        db,
        {
            "formatted": "250 Yonge St, Toronto, ON M5B 2L7",
            "line1": "250 Yonge St",
            "city": "Toronto",
            "region": "ON",
            "postal": "M5B 2L7",
            "country": "CA",
            "lat": 43.6544,
            "lng": -79.3807,
            "contact_name": "Store Receiver",
            "phone": "+1 416-555-8899",
        },
    )
    db.add(
        SavedAddress(
            merchant_id=merchant.id,
            label="Downtown store",
            address_type="dropoff",
            formatted="250 Yonge St, Toronto, ON M5B 2L7",
            lat=43.6544,
            lng=-79.3807,
            postal="M5B 2L7",
            address_id=drop_addr.id,
            is_default=False,
        )
    )
    db.add(
        MerchantRecipient(
            merchant_id=merchant.id,
            name="Alex Rivera",
            email="dock@mapleleaf.example",
            phone="+1 416-555-2103",
            company="Maple Leaf Wholesale Inc.",
            default_address={
                "formatted": WAREHOUSE["formatted"],
                "lat": WAREHOUSE["lat"],
                "lng": WAREHOUSE["lng"],
                "postal": WAREHOUSE["postal"],
                "contact_name": "Alex Rivera",
                "phone": "+1 416-555-2103",
            },
        )
    )
    raw_key = "pc_local_" + _uuid().replace("-", "")
    db.add(
        MerchantApiKey(
            merchant_id=merchant.id,
            name="Local sandbox key",
            key_prefix=raw_key[:12],
            key_hash=hashlib.sha256(raw_key.encode()).hexdigest(),
            scopes=["bookings:write", "webhooks:read", "tracking:read"],
            environment="sandbox",
            rate_limit_per_minute=120,
            is_active=True,
            last_used_at=NOW,
        )
    )

    company = project_merchant_company(db, merchant)
    company.operating_name = "Maple Leaf Wholesale"
    company.linkedin_url = "https://www.linkedin.com/company/maple-leaf-wholesale"
    company.logo_url = "https://storage.porterchain.local/seed/maple-leaf-logo.png"
    company.business_type = "corporation"
    company.branches = [
        {
            "name": "Queen Street DC",
            "formatted": WAREHOUSE["formatted"],
            "lat": WAREHOUSE["lat"],
            "lng": WAREHOUSE["lng"],
        }
    ]
    company.warehouse_locations = [WAREHOUSE]
    company.pickup_locations = [WAREHOUSE]
    company.billing_details = {
        "payment_terms": "NET_30",
        "billing_cycle": "MONTHLY",
        "credit_limit_cents": 250_000_00,
        "currency": "CAD",
        "ap_email": "ap@mapleleaf.example",
    }
    company.estimated_deliveries_per_month = 420
    company.estimated_monthly_revenue_cents = 85_000_00
    company.preferred_vehicle = "cargo_van"
    company.current_logistics_provider = "In-house + courier mix"
    company.merchant_status = CompanyMerchantStatus.ACTIVE_MERCHANT.value
    company.owner_id = admin.id
    company.tags = ["wholesale", "gta", "priority"]
    company.is_pinned = True
    company.is_favorite = True
    company.custom_fields = {"buyer": "Jordan Lee", "onboarding_completed": True}
    db.flush()

    contacts = [
        CrmContact(
            company_id=company.id,
            first_name="Jordan",
            last_name="Lee",
            designation="Owner",
            department="Operations",
            phone="+1 416-555-2100",
            mobile="+1 416-555-2101",
            email=DEV_MERCHANT_EMAIL,
            linkedin="https://www.linkedin.com/in/jordan-lee-mapleleaf",
            birthday=date(1986, 4, 12),
            roles=[TEAM_ROLE_TAG, MerchantRole.OWNER.value, "decision_maker"],
            is_primary=True,
        ),
        CrmContact(
            company_id=company.id,
            first_name="Anita",
            last_name="Patel",
            designation="Controller",
            department="Finance",
            phone="+1 416-555-2104",
            mobile="+1 416-555-2194",
            email="ap@mapleleaf.example",
            linkedin="https://www.linkedin.com/in/anita-patel-mapleleaf",
            birthday=date(1990, 9, 3),
            roles=["accounts_payable", "billing"],
            is_primary=False,
        ),
        CrmContact(
            company_id=company.id,
            first_name="Alex",
            last_name="Rivera",
            designation="Warehouse Manager",
            department="Warehouse",
            phone="+1 416-555-2103",
            mobile="+1 416-555-2183",
            email="dock@mapleleaf.example",
            linkedin="https://www.linkedin.com/in/alex-rivera-mapleleaf",
            birthday=date(1988, 1, 22),
            roles=["warehouse_manager", "receiver"],
            is_primary=False,
        ),
    ]
    for contact in contacts:
        db.add(contact)
    db.flush()

    crm_contract = CrmContract(
        contract_number="C-LOCAL-0001",
        company_id=company.id,
        status=ContractStatus.ACTIVE.value,
        net_terms="NET_30",
        sla={"on_time_pct": 96, "first_attempt_pct": 98, "pod_minutes": 15},
        service_areas=["GTA", "Hamilton", "Peel"],
        vehicles=["cargo_van", "sprinter_van"],
        insurance={"cargo_cents": 100_000_00, "liability_cents": 2_000_000_00},
        pricing_sheet_url="https://storage.porterchain.local/seed/maple-leaf-rates.pdf",
        signed_document_url="https://storage.porterchain.local/seed/maple-leaf-msa.pdf",
        documents=[{"name": "Master service agreement", "url": "https://storage.porterchain.local/seed/maple-leaf-msa.pdf"}],
        value_cents=240_000_00,
        effective_from=date.today() - timedelta(days=14),
        expiry_date=date.today() + timedelta(days=351),
        renewal_reminder_at=date.today() + timedelta(days=320),
        created_by=admin.id,
    )
    db.add(crm_contract)
    db.flush()
    db.add(
        MerchantContract(
            merchant_id=merchant.id,
            name="Maple Leaf GTA 2026",
            rules={
                "pricing_model": "distance",
                "base_cents": 1800,
                "per_km_cents": 95,
                "fuel_surcharge_percent": 5.0,
                "sla_on_time_pct": 96,
            },
            crm_contract_id=crm_contract.id,
            minimum_monthly_commitment_cents=15_000_00,
            is_active=True,
            effective_from=NOW - timedelta(days=14),
            effective_to=NOW + timedelta(days=351),
        )
    )
    db.add(
        CrmDocument(
            entity_type="company",
            entity_id=company.id,
            name="WSIB clearance certificate",
            category="insurance",
            url="https://storage.porterchain.local/seed/maple-leaf-wsib.pdf",
            size_bytes=184_320,
            version=1,
            uploaded_by=admin.id,
        )
    )
    db.add(
        CrmActivity(
            entity_type="company",
            entity_id=company.id,
            activity_type="note",
            subject="Local persona seeded",
            body="Complete merchant company file created for one-by-one local testing.",
            metadata_json={"source": "reset_local_personas"},
            actor_id=admin.id,
            occurred_at=NOW,
        )
    )
    db.flush()
    return merchant, seat, company, owner


def seed_driver(db, admin: AdminUser) -> Driver:
    expires = NOW + timedelta(days=365)
    docs_json = {
        "license_class": "G",
        "license_number": "R1234-56789-10111",
        "service_area": "GTA",
        "employment_type": "contractor",
        "address": {
            "street": "88 Harbour St",
            "city": "Toronto",
            "province": "ON",
            "postal_code": "M5J 0B6",
        },
        "emergency_contact": {
            "name": "Sofia Rossi",
            "phone": "+1 416-555-0199",
            "relationship": "spouse",
        },
        "license": {
            "status": "verified",
            "verified": True,
            "url": "https://storage.porterchain.local/seed/marco-license.pdf",
            "uploaded_at": NOW.isoformat(),
            "reference_number": "ON-DL-882211",
            "expires_at": expires.isoformat(),
        },
        "insurance": {
            "status": "verified",
            "verified": True,
            "url": "https://storage.porterchain.local/seed/marco-insurance.pdf",
            "uploaded_at": NOW.isoformat(),
            "reference_number": "INS-PC-44190",
            "expires_at": expires.isoformat(),
        },
        "vehicle_registration": {
            "status": "verified",
            "verified": True,
            "url": "https://storage.porterchain.local/seed/marco-registration.pdf",
            "uploaded_at": NOW.isoformat(),
            "reference_number": "CARGO1",
            "expires_at": expires.isoformat(),
        },
        "background_check": {
            "status": "verified",
            "verified": True,
            "url": "https://storage.porterchain.local/seed/marco-background.pdf",
            "uploaded_at": NOW.isoformat(),
            "reference_number": "BG-2026-0912",
        },
        "abstract": {
            "verified": True,
            "status": "complete",
            "license_class": "G",
            "demerits": 0,
            "url": "https://storage.porterchain.local/seed/marco-abstract.pdf",
        },
        "files": [
            {
                "id": _uuid(),
                "doc_type": "driver_license",
                "label": "Driver license",
                "file_url": "https://storage.porterchain.local/seed/marco-license.pdf",
                "reference_number": "ON-DL-882211",
                "expires_at": expires.isoformat(),
                "notes": "Ontario G class, no restrictions.",
                "status": "verified",
                "verified": True,
                "uploaded_at": NOW.isoformat(),
                "uploaded_by": admin.id,
            },
            {
                "id": _uuid(),
                "doc_type": "insurance",
                "label": "Insurance certificate",
                "file_url": "https://storage.porterchain.local/seed/marco-insurance.pdf",
                "reference_number": "INS-PC-44190",
                "expires_at": expires.isoformat(),
                "notes": "Commercial cargo $1M.",
                "status": "verified",
                "verified": True,
                "uploaded_at": NOW.isoformat(),
                "uploaded_by": admin.id,
            },
            {
                "id": _uuid(),
                "doc_type": "vehicle_registration",
                "label": "Vehicle registration",
                "file_url": "https://storage.porterchain.local/seed/marco-registration.pdf",
                "reference_number": "CARGO1",
                "expires_at": expires.isoformat(),
                "notes": "Ford Transit 2023.",
                "status": "verified",
                "verified": True,
                "uploaded_at": NOW.isoformat(),
                "uploaded_by": admin.id,
            },
            {
                "id": _uuid(),
                "doc_type": "background_check",
                "label": "Background check",
                "file_url": "https://storage.porterchain.local/seed/marco-background.pdf",
                "reference_number": "BG-2026-0912",
                "notes": "Cleared.",
                "status": "verified",
                "verified": True,
                "uploaded_at": NOW.isoformat(),
                "uploaded_by": admin.id,
            },
            {
                "id": _uuid(),
                "doc_type": "driver_abstract",
                "label": "MTO abstract",
                "file_url": "https://storage.porterchain.local/seed/marco-abstract.pdf",
                "reference_number": "MTO-ABS-0091",
                "notes": "Zero demerits.",
                "status": "verified",
                "verified": True,
                "uploaded_at": NOW.isoformat(),
                "uploaded_by": admin.id,
            },
        ],
    }
    driver = Driver(
        status=DriverStatus.APPROVED.value,
        email="marco@porterchain.com",
        phone="+1 416-555-0101",
        full_name="Marco Rossi",
        license_verified=True,
        medical_transport_certified=True,
        insurance_verified=True,
        vehicle_verified=True,
        background_check_status="cleared",
        rating=4.92,
        is_online=False,
        availability="offline",
        wallet_balance_cents=125_50,
        documents=docs_json,
        performance={"score": 96, "on_time_pct": 98, "completion_pct": 99, "jobs_30d": 0},
    )
    db.add(driver)
    db.flush()
    pc = _pc_user(
        db,
        clerk_user_id="dev_driver_marco",
        email="marco@porterchain.com",
        phone="+1 416-555-0101",
        role="driver",
        workspace="driver",
        profile={
            "first_name": "Marco",
            "last_name": "Rossi",
            "license_class": "G",
            "service_area": "GTA",
        },
    )
    driver.porterchain_user_id = pc.id
    db.add(
        Vehicle(
            driver_id=driver.id,
            vehicle_class="cargo_van",
            plate_number="CARGO1",
            make_model="Ford Transit 250",
            capacity_kg=1200.0,
            compliance_expires_at=expires,
            is_active=True,
        )
    )
    for spec in (
        ("license", "Driver license", "https://storage.porterchain.local/seed/marco-license.pdf", "ON-DL-882211"),
        ("insurance", "Insurance certificate", "https://storage.porterchain.local/seed/marco-insurance.pdf", "INS-PC-44190"),
        ("vehicle_registration", "Vehicle registration", "https://storage.porterchain.local/seed/marco-registration.pdf", "CARGO1"),
        ("background_check", "Background check", "https://storage.porterchain.local/seed/marco-background.pdf", "BG-2026-0912"),
        ("abstract", "MTO abstract", "https://storage.porterchain.local/seed/marco-abstract.pdf", "MTO-ABS-0091"),
    ):
        record_document(
            db,
            driver_id=driver.id,
            doc_type=spec[0],
            label=spec[1],
            file_url=spec[2],
            reference_number=spec[3],
            status="verified",
            verified=True,
            expires_at=expires if spec[0] != "background_check" else None,
            notes="Local complete persona seed.",
            uploaded_by=admin.id,
        )
    return driver


def seed_customer(db) -> Customer:
    persist_address(db, CUSTOMER_HOME)
    pc = _pc_user(
        db,
        clerk_user_id=DEV_CUSTOMER_SUBJECT,
        email=DEV_CUSTOMER_EMAIL,
        phone="+1 416-555-4401",
        role="customer",
        workspace="customer",
        profile={"first_name": "Priya", "last_name": "Sharma"},
    )
    customer = Customer(
        clerk_user_id=DEV_CUSTOMER_SUBJECT,
        porterchain_user_id=pc.id,
        email=DEV_CUSTOMER_EMAIL,
        phone="+1 416-555-4401",
        visitor_session_id="local-customer-session",
        full_name="Priya Sharma",
        customer_reference=generate_customer_reference(),
        stripe_customer_id="cus_local_priya",
        privacy_status="active",
        privacy_hold_reference=None,
        privacy_hold_at=None,
    )
    db.add(customer)
    db.flush()
    return customer


def _print_summary(db, wipe_stats: dict, merchant, company, driver: Driver, customer: Customer) -> None:
    admins = db.query(AdminUser).order_by(AdminUser.email).all()
    passkeys = db.query(StaffWebAuthnCredential).count()
    print("=== Local personas reset ===")
    print(f"  truncated_tables={wipe_stats['truncated_tables']}  removed_test_admins={wipe_stats['removed_admins']}")
    print()
    print("KEPT STAFF")
    for admin in admins:
        print(f"  • {admin.email}  role={admin.role}  id={admin.id}")
    print(f"  passkeys: {passkeys}")
    print()
    print("MERCHANT  (portal http://localhost:3001  — Bearer dev / merchant@porterchain.com)")
    print(f"  company:  {merchant.company_name}  ({merchant.legal_name})")
    print(f"  id:       {merchant.id}  status={merchant.status}")
    print(f"  crm:      {company.id}  contacts={db.query(CrmContact).filter(CrmContact.company_id == company.id).count()}")
    print(f"  email:    {merchant.email}  phone={merchant.phone}")
    print()
    print("DRIVER  (portal http://localhost:3003  — Bearer dev / marco@porterchain.com)")
    print(f"  {driver.full_name}  {driver.email}  id={driver.id}  status={driver.status}")
    print(f"  documents: {len((driver.documents or {}).get('files') or [])} files, all verified")
    print()
    print("CUSTOMER  (app http://localhost:3004  — Bearer dev / customer@porterchain.com)")
    print(f"  {customer.full_name}  {customer.email}  id={customer.id}  ref={customer.customer_reference}")
    print()
    print("No orders, tickets, or quotes were seeded — add those one by one.")


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        wipe_stats = wipe_except_staff(db)
        admin = (
            db.query(AdminUser)
            .filter(AdminUser.email == "admin@porterchain.com")
            .first()
        ) or db.query(AdminUser).order_by(AdminUser.created_at.asc()).first()
        if not admin:
            raise RuntimeError("No staff admin remained after wipe.")
        merchant, _seat, company, owner = seed_merchant(db, admin)
        driver = seed_driver(db, admin)
        customer = seed_customer(db)
        db.commit()
        db.refresh(merchant)
        db.refresh(driver)
        db.refresh(customer)
        _print_summary(db, wipe_stats, merchant, company, driver, customer)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
