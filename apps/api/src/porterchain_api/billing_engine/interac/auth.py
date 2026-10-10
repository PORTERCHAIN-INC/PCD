"""Is this email genuinely from Interac? Trust only our own MTA's verdict.

Senders can paste fake ``Authentication-Results`` headers, so we read only the
headers stamped by our receiving server (``authserv-id`` = INTERAC_AUTHSERV_ID,
e.g. ``mx.zohomail.com``) and require:

* the visible From domain is an Interac sending domain, and
* DKIM passed for an Interac domain (``header.d``/``header.i``), or DMARC passed for
  an Interac ``header.from``. SPF alone is not enough (it does not cover From).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from email.message import Message
from email.utils import parseaddr

INTERAC_DOMAINS = frozenset({"payments.interac.ca", "interac.ca"})


@dataclass
class AuthVerdict:
    ok: bool
    detail: str


def _domain_ok(domain: str | None) -> bool:
    d = (domain or "").lower().strip().strip(".").lstrip("@")
    if "@" in d:
        d = d.split("@", 1)[1]
    return any(d == base or d.endswith("." + base) for base in INTERAC_DOMAINS)


def verify_interac_sender(msg: Message, *, authserv_id: str) -> AuthVerdict:
    from_addr = parseaddr(str(msg.get("From", "")))[1].lower()
    if not _domain_ok(from_addr):
        return AuthVerdict(False, f"from_not_interac:{from_addr or '-'}")
    want = (authserv_id or "").lower().strip()
    ours = [
        str(h)
        for h in (msg.get_all("Authentication-Results") or [])
        if str(h).strip().lower().split(";", 1)[0].strip().split()[0:1] == [want]
    ]
    if not ours:
        return AuthVerdict(False, "no_trusted_auth_results")
    # The topmost header is the one our server added last.
    res = ours[0].lower()
    dkim_pass = [
        m.group(1)
        for m in re.finditer(r"dkim=pass[^;]*?header\.[di]=@?([a-z0-9.\-]+)", res)
    ]
    dmarc_pass = re.search(r"dmarc=pass[^;]*?header\.from=([a-z0-9.\-]+)", res)
    spf_pass = "spf=pass" in res
    if any(_domain_ok(d) for d in dkim_pass):
        return AuthVerdict(True, f"dkim=pass{' spf=pass' if spf_pass else ''}")
    if dmarc_pass and _domain_ok(dmarc_pass.group(1)):
        return AuthVerdict(True, "dmarc=pass")
    if re.search(r"dkim=(fail|neutral|none|temperror|permerror)", res):
        return AuthVerdict(False, "dkim_not_pass")
    return AuthVerdict(False, "no_interac_dkim_or_dmarc")
