"""Merchant entity resolution: is this new signup/install an existing company?

Deterministic keys first (shop domain, admin-intended install, BN/HST, company
email domain, phone, website), then fuzzy name + postal code. Returns a decision:
  link    -> attach to the existing merchant (strong key match)
  suggest -> create, but flag for admin review / "Is this your company?" after
             verification (never reveal the other account to an unverified user)
  new     -> no plausible match
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Iterable

FREE_MAIL = {
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.ca", "hotmail.com", "hotmail.ca",
    "outlook.com", "live.com", "live.ca", "msn.com", "icloud.com", "me.com", "mac.com",
    "aol.com", "proton.me", "protonmail.com", "gmx.com", "rogers.com", "bell.net",
    "sympatico.ca", "shaw.ca", "telus.net", "videotron.ca", "cogeco.ca",
}
LEGAL_SUFFIX = re.compile(
    r"\b(inc|incorporated|ltd|limited|corp|corporation|co|company|llc|lp|llp|ltee|ltée|enterprises?|group|canada|the)\b\.?"
)
LINK_AT = 0.90
SUGGEST_AT = 0.60


def norm_name(value: str | None) -> str:
    s = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode().lower()
    s = s.replace("&", " and ")
    s = LEGAL_SUFFIX.sub(" ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def email_domain(email: str | None) -> str | None:
    if not email or "@" not in email:
        return None
    d = email.strip().lower().rsplit("@", 1)[1]
    if d in FREE_MAIL or d.endswith(".invalid"):
        return None
    return d


def web_domain(url: str | None) -> str | None:
    if not url:
        return None
    d = re.sub(r"^[a-z]+://", "", url.strip().lower()).split("/", 1)[0]
    d = d.removeprefix("www.")
    return d or None


def norm_phone(phone: str | None) -> str | None:
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 10:
        digits = "1" + digits
    return "+" + digits if len(digits) == 11 else None


def norm_bn(value: str | None) -> str | None:
    digits = re.sub(r"\D", "", value or "")
    return digits[:9] if len(digits) >= 9 else None  # 9-digit BN root of an HST/BN number


def norm_postal(value: str | None) -> str | None:
    s = re.sub(r"\s", "", (value or "").upper())
    return s if re.fullmatch(r"[A-Z]\d[A-Z]\d[A-Z]\d", s) else None


def name_similarity(a: str | None, b: str | None) -> float:
    x, y = norm_name(a), norm_name(b)
    if not x or not y:
        return 0.0
    if x == y or x.replace(" ", "") == y.replace(" ", ""):
        return 1.0
    return SequenceMatcher(None, x, y).ratio()


@dataclass
class Candidate:
    id: str
    company_name: str | None = None
    legal_name: str | None = None
    emails: list[str] = field(default_factory=list)
    phone: str | None = None
    website: str | None = None
    hst_number: str | None = None
    business_number: str | None = None
    postal_code: str | None = None
    shop_domains: list[str] = field(default_factory=list)
    pending_install_shops: list[str] = field(default_factory=list)


@dataclass
class Probe:
    company_name: str | None = None
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    hst_number: str | None = None
    business_number: str | None = None
    postal_code: str | None = None
    shop_domain: str | None = None


@dataclass
class Match:
    decision: str  # link | suggest | new
    merchant_id: str | None
    score: float
    reasons: list[str]


def score(probe: Probe, c: Candidate) -> tuple[float, list[str]]:
    reasons: list[str] = []
    s = 0.0
    shop = (probe.shop_domain or "").lower()
    if shop and shop in [d.lower() for d in c.pending_install_shops]:
        return 1.0, ["admin_issued_install_url"]
    if shop and shop in [d.lower() for d in c.shop_domains]:
        return 1.0, ["shop_domain"]
    pb = norm_bn(probe.business_number) or norm_bn(probe.hst_number)
    if pb and pb in {norm_bn(c.business_number), norm_bn(c.hst_number)}:
        return 0.99, ["business_number"]
    pd = email_domain(probe.email)
    cdoms = {email_domain(e) for e in c.emails} | {web_domain(c.website)}
    cdoms.discard(None)
    if pd and pd in cdoms:
        s += 0.6; reasons.append("email_domain")
    pw = web_domain(probe.website)
    if pw and pw in cdoms and "email_domain" not in reasons:
        s += 0.6; reasons.append("website_domain")
    pp = norm_phone(probe.phone)
    if pp and pp == norm_phone(c.phone):
        s += 0.35; reasons.append("phone")
    ns = max(name_similarity(probe.company_name, c.company_name), name_similarity(probe.company_name, c.legal_name))
    if ns >= 0.85:
        s += 0.4 * ns; reasons.append(f"name~{ns:.2f}")
    # A company-domain email whose root matches the name (hello@kaylulu.ca vs "KAYLULU").
    if pd and norm_name(pd.split(".")[0]).replace(" ", "") == norm_name(c.company_name).replace(" ", ""):
        s += 0.3; reasons.append("email_domain_is_name")
    pc = norm_postal(probe.postal_code)
    if pc and pc == norm_postal(c.postal_code):
        s += 0.15; reasons.append("postal_code")
    return min(s, 0.98), reasons


def resolve(probe: Probe, candidates: Iterable[Candidate]) -> Match:
    best: Match = Match("new", None, 0.0, [])
    for c in candidates:
        sc, why = score(probe, c)
        if sc > best.score:
            best = Match("new", c.id, sc, why)
    if best.score >= LINK_AT:
        best.decision = "link"
    elif best.score >= SUGGEST_AT:
        best.decision = "suggest"
    else:
        best = Match("new", None, best.score, best.reasons)
    return best


def candidates_from_db(db: Any, probe: Probe, limit: int = 50) -> list[Candidate]:
    """Cheap blocking query; swap the name filter for pg_trgm `%` once the extension is on."""
    from sqlalchemy import func, or_

    from porterchain_api.merchant_models import Merchant, MerchantUser, ShopifyShop

    filters = []
    nn = norm_name(probe.company_name)
    if nn:
        filters.append(func.lower(Merchant.company_name).contains(nn.split(" ")[0]))
    pd = email_domain(probe.email)
    if pd:
        filters.append(func.lower(Merchant.email).like(f"%@{pd}"))
        filters.append(func.lower(Merchant.company_name).contains(pd.split(".")[0]))
    if probe.shop_domain:
        filters.append(Merchant.profile["pending_shopify_install"].astext == probe.shop_domain)
    if not filters:
        return []
    out: list[Candidate] = []
    rows = db.query(Merchant).filter(Merchant.deleted_at.is_(None), or_(*filters)).limit(limit).all()
    for m in rows:
        prof = m.profile or {}
        seats = db.query(MerchantUser.email).filter(MerchantUser.merchant_id == m.id).all()
        shops = db.query(ShopifyShop.shop_domain).filter(ShopifyShop.merchant_id == m.id).all()
        addr = m.billing_address or {}
        pending = prof.get("pending_shopify_install")
        out.append(Candidate(
            id=str(m.id), company_name=m.company_name, legal_name=m.legal_name,
            emails=[m.email or ""] + [e for (e,) in seats if e],
            phone=m.phone, website=prof.get("website"), hst_number=m.hst_number,
            business_number=m.business_number,
            postal_code=addr.get("postal_code") if isinstance(addr, dict) else None,
            shop_domains=[d for (d,) in shops], pending_install_shops=[pending] if pending else [],
        ))
    return out
