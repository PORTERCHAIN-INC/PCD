"""Autonomous email discovery for phone-only leads (no cold WA blast)."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from porterchain_api.crm_models import CrmLead

logger = logging.getLogger(__name__)

_MAILTO_RE = re.compile(r"mailto:([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})", re.I)
_EMAIL_RE = re.compile(r"\b([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})\b")
_SKIP_DOMAINS = frozenset(
    {
        "example.com",
        "example.org",
        "sentry.io",
        "wixpress.com",
        "schema.org",
        "googleapis.com",
        "gstatic.com",
        "w3.org",
        "facebook.com",
        "twitter.com",
        "instagram.com",
        "linkedin.com",
    }
)
_SKIP_LOCAL = frozenset({"noreply", "no-reply", "donotreply", "mailer-daemon", "postmaster"})


def _normalize_website(raw: str | None) -> str | None:
    if not raw:
        return None
    u = raw.strip()
    if not u:
        return None
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    try:
        parsed = urlparse(u)
        if not parsed.netloc:
            return None
        return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        return None


def _score_email(email: str, company: str) -> int:
    local, _, domain = email.lower().partition("@")
    if domain in _SKIP_DOMAINS or local in _SKIP_LOCAL:
        return -100
    score = 10
    # Prefer generic inboxes over role mailboxes when scores otherwise tie.
    if local in ("info", "contact", "hello"):
        score += 30
    elif local in ("sales", "office", "admin"):
        score += 20
    slug = re.sub(r"[^a-z0-9]", "", (company or "").lower())[:12]
    if slug and slug in domain.replace(".", ""):
        score += 30
    if domain.endswith(".ca") or domain.endswith(".com"):
        score += 5
    return score


def extract_emails_from_html(html: str, *, company: str) -> list[str]:
    found: list[str] = []
    for m in _MAILTO_RE.findall(html or ""):
        found.append(m.lower())
    for m in _EMAIL_RE.findall(html or ""):
        found.append(m.lower())
    ranked = sorted({e for e in found}, key=lambda e: _score_email(e, company), reverse=True)
    return [e for e in ranked if _score_email(e, company) > 0][:5]


def discover_email_from_website(website: str, *, company: str = "") -> dict[str, Any]:
    base = _normalize_website(website)
    if not base:
        return {"status": "skipped", "reason": "no_website"}
    paths = ["", "/contact", "/contact-us", "/about", "/about-us"]
    emails: list[str] = []
    try:
        with httpx.Client(timeout=12.0, follow_redirects=True) as client:
            for path in paths:
                try:
                    resp = client.get(base + path, headers={"User-Agent": "PorterChainLeadBot/1.0"})
                    if resp.status_code >= 400:
                        continue
                    emails.extend(extract_emails_from_html(resp.text, company=company))
                    if emails:
                        break
                except Exception:
                    continue
    except Exception as exc:
        return {"status": "error", "reason": "fetch_failed", "detail": str(exc)[:200]}
    if not emails:
        return {"status": "not_found", "reason": "no_email_on_site", "website": base}
    return {
        "status": "found",
        "email": emails[0],
        "candidates": emails,
        "website": base,
    }


def enrich_lead_email(db: Session, lead: CrmLead) -> dict[str, Any]:
    """Find public email; store on lead. Does NOT set marketing consent."""
    if (lead.email or "").strip() and "@" in (lead.email or ""):
        return {"status": "skipped", "reason": "already_has_email", "email": lead.email}

    website = lead.website
    if not website and isinstance(lead.custom_fields, dict):
        website = lead.custom_fields.get("website") or lead.custom_fields.get("url")
    if not website and isinstance(lead.address, dict):
        website = lead.address.get("website")

    result = discover_email_from_website(str(website or ""), company=lead.company_name or "")
    bag = dict(lead.custom_fields) if isinstance(lead.custom_fields, dict) else {}
    enrich_log = {
        "at": datetime.now(UTC).isoformat(),
        "result": result.get("status"),
        "reason": result.get("reason"),
        "website": result.get("website"),
    }
    if result.get("status") == "found" and result.get("email"):
        lead.email = str(result["email"]).strip().lower()[:320]
        if not lead.website and result.get("website"):
            lead.website = str(result["website"])[:512]
        enrich_log["email"] = lead.email
        # Discovery ≠ consent — stamp legal_basis only for RoPA; marketing stays off
        consent = dict(lead.consent) if isinstance(lead.consent, dict) else {}
        consent.setdefault("legal_basis", "legitimate_interest")
        consent.setdefault("enrichment_source", "website_scrape")
        consent.setdefault("enrichment_at", enrich_log["at"])
        lead.consent = consent
        tags = list(lead.tags or [])
        if "email_enriched" not in tags:
            tags.append("email_enriched")
        # clear needs_enrich agent status via custom_fields
        agent = dict(bag.get("lead_agent") or {}) if isinstance(bag.get("lead_agent"), dict) else {}
        agent["status"] = "enriched"
        agent["enriched_email"] = lead.email
        bag["lead_agent"] = agent
        bag["enrich"] = enrich_log
        lead.custom_fields = bag
        db.flush()
        return {"status": "found", "email": lead.email, "website": result.get("website")}

    agent = dict(bag.get("lead_agent") or {}) if isinstance(bag.get("lead_agent"), dict) else {}
    agent["status"] = "enrich_failed"
    agent["enrich_reason"] = result.get("reason")
    bag["lead_agent"] = agent
    bag["enrich"] = enrich_log
    lead.custom_fields = bag
    tags = list(lead.tags or [])
    if "needs_enrich" not in tags:
        tags.append("needs_enrich")
    lead.tags = tags
    db.flush()
    return result


def process_lead_enrich_batch(db: Session, *, limit: int = 20) -> dict[str, int]:
    """Worker: enrich vendor/phone-only leads marked needs_enrich or missing email+has phone."""
    from porterchain_api.collaboration_engine.lead_agent import run_lead_agent
    from porterchain_api.config import get_settings
    from porterchain_api.domain.crm_states import LeadStatus

    # Prefer explicit needs_enrich / agent status, else vendor without email with website
    q = (
        db.query(CrmLead)
        .filter(
            CrmLead.status == LeadStatus.NEW.value,
            CrmLead.phone.isnot(None),
            CrmLead.phone != "",
            (CrmLead.email.is_(None)) | (CrmLead.email == ""),
        )
        .order_by(CrmLead.updated_at.asc())
        .limit(limit * 3)
        .all()
    )
    found = failed = skipped = 0
    website_url = getattr(get_settings(), "website_url", "") or ""
    processed = 0
    for lead in q:
        if processed >= limit:
            break
        # Skip if no website to scrape (can't invent emails)
        has_site = bool(lead.website) or (
            isinstance(lead.custom_fields, dict)
            and (lead.custom_fields.get("website") or lead.custom_fields.get("url"))
        )
        agent = {}
        if isinstance(lead.custom_fields, dict) and isinstance(
            lead.custom_fields.get("lead_agent"), dict
        ):
            agent = lead.custom_fields["lead_agent"]
        needs = agent.get("status") == "needs_enrich" or "needs_enrich" in (lead.tags or [])
        if not has_site and not needs:
            skipped += 1
            continue
        if not has_site:
            skipped += 1
            continue
        processed += 1
        result = enrich_lead_email(db, lead)
        if result.get("status") == "found":
            found += 1
            # Do not auto-mail without marketing — LI enrich only stores email
            # If marketing already true (unlikely), agent can welcome
            consent = lead.consent if isinstance(lead.consent, dict) else {}
            if consent.get("marketing"):
                run_lead_agent(db, lead, trigger="enrich", website_url=website_url)
        elif result.get("status") == "skipped":
            skipped += 1
        else:
            failed += 1
    if found or failed:
        db.commit()
    return {"scanned": processed, "found": found, "failed": failed, "skipped": skipped}


__all__ = [
    "discover_email_from_website",
    "enrich_lead_email",
    "extract_emails_from_html",
    "process_lead_enrich_batch",
]
