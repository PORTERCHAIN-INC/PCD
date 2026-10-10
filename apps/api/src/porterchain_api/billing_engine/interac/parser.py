"""Parse Interac e-Transfer notification / autodeposit emails (English + French)."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import datetime
from email.message import Message
from email.utils import parseaddr, parsedate_to_datetime


@dataclass
class ParsedTransfer:
    message_id: str
    kind: str  # "autodeposit" | "notification" | "deposited"
    sender_name: str | None
    sender_email: str | None
    amount_cents: int
    currency: str
    memo: str | None
    interac_reference: str | None
    received_at: datetime | None
    from_address: str


class NotInteracEmail(ValueError):
    """The message is not an Interac money-received notification."""


_SUBJECT_EN = re.compile(r"INTERAC\s*e-?Transfer", re.I)
_SUBJECT_FR = re.compile(r"Virement\s+INTERAC", re.I)

# "ACME INC. sent you $1,130.00 (CAD)" / "ACME vous a envoyé 1 130,00 $ (CAD)"
_SENT_EN = re.compile(
    r"(?P<name>[^\n]+?)\s+sent you\s+\$\s?(?P<amt>[\d,]+\.\d{2})\s*\(?(?P<cur>CAD|USD)?\)?",
    re.I,
)
_SENT_FR = re.compile(
    r"(?P<name>[^\n]+?)\s+vous a envoy[ée]\s+(?P<amt>[\d\s\u00a0\u202f.]+,\d{2})\s*\$\s*\(?(?P<cur>CAD|USD)?\)?",
    re.I,
)
_AUTODEP = re.compile(r"automatically deposited|d[ée]pos[ée] automatiquement|automatiquement d[ée]pos", re.I)
_DEPOSITED = re.compile(r"has been deposited|a [ée]t[ée] d[ée]pos[ée]", re.I)
_MESSAGE = re.compile(r"^\s*(?:Message|Message de l'exp[ée]diteur)\s*:\s*(?P<memo>.+?)\s*$", re.I | re.M)
_REFERENCE = re.compile(
    r"(?:Reference Number|Reference number|Num[ée]ro de r[ée]f[ée]rence)\s*:\s*(?P<ref>[A-Za-z0-9]{6,40})",
    re.I,
)
_SENDER_EMAIL = re.compile(r"(?:Sender'?s? email|Courriel de l'exp[ée]diteur)\s*:\s*(?P<em>[^\s<>]+@[^\s<>]+)", re.I)
_HI_PREFIX = re.compile(r"^(?:Hi|Hello|Bonjour)\s+[^,]{1,120},\s*", re.I)


def _text_of(msg: Message) -> str:
    """Prefer text/plain; fall back to stripped HTML."""
    plain: list[str] = []
    htmls: list[str] = []
    parts = msg.walk() if msg.is_multipart() else [msg]
    for part in parts:
        if part.get_content_maintype() == "multipart":
            continue
        if part.get_filename():
            continue  # never read attachments
        ctype = part.get_content_type()
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        charset = part.get_content_charset() or "utf-8"
        try:
            text = payload.decode(charset, errors="replace")
        except LookupError:
            text = payload.decode("utf-8", errors="replace")
        if ctype == "text/plain":
            plain.append(text)
        elif ctype == "text/html":
            htmls.append(text)
    if plain:
        return "\n".join(plain)
    joined = "\n".join(htmls)
    joined = re.sub(r"(?is)<(script|style).*?</\1>", " ", joined)
    joined = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>|</h\d>", "\n", joined)
    joined = re.sub(r"<[^>]+>", " ", joined)
    return html.unescape(joined)


def _amount_en(raw: str) -> int:
    return int(round(float(raw.replace(",", "")) * 100))


def _amount_fr(raw: str) -> int:
    cleaned = re.sub(r"[\s\u00a0\u202f.]", "", raw).replace(",", ".")
    return int(round(float(cleaned) * 100))


def _clean_name(name: str) -> str:
    name = _HI_PREFIX.sub("", name.strip())
    return re.sub(r"\s+", " ", name).strip(" ,.:") or name.strip()


def _decoded_subject(msg: Message) -> str:
    from email.header import decode_header, make_header

    raw = msg.get("Subject", "") or ""
    try:
        return str(make_header(decode_header(str(raw))))
    except (UnicodeDecodeError, LookupError, ValueError):
        return str(raw)


def parse_interac_email(msg: Message) -> ParsedTransfer:
    subject = _decoded_subject(msg)
    if not (_SUBJECT_EN.search(subject) or _SUBJECT_FR.search(subject)):
        raise NotInteracEmail("subject")
    body = _text_of(msg)
    body_flat = re.sub(r"[ \t]+", " ", body)

    m = _SENT_EN.search(body_flat)
    if m:
        amount = _amount_en(m.group("amt"))
    else:
        m = _SENT_FR.search(body_flat)
        if not m:
            raise NotInteracEmail("no_amount")
        amount = _amount_fr(m.group("amt"))
    if amount <= 0:
        raise NotInteracEmail("zero_amount")
    currency = (m.group("cur") or "CAD").lower()

    if _AUTODEP.search(body_flat) or _AUTODEP.search(subject):
        kind = "autodeposit"
    elif _DEPOSITED.search(body_flat) or _DEPOSITED.search(subject):
        kind = "deposited"
    else:
        kind = "notification"

    memo_m = _MESSAGE.search(body)
    ref_m = _REFERENCE.search(body_flat)
    sender_email_m = _SENDER_EMAIL.search(body_flat)
    received = None
    try:
        if msg.get("Date"):
            received = parsedate_to_datetime(str(msg.get("Date")))
    except (TypeError, ValueError):
        received = None
    message_id = str(msg.get("Message-ID") or msg.get("Message-Id") or "").strip()
    if not message_id:
        raise NotInteracEmail("no_message_id")
    return ParsedTransfer(
        message_id=message_id[:255],
        kind=kind,
        sender_name=_clean_name(m.group("name"))[:255] or None,
        sender_email=(sender_email_m.group("em").strip(".").lower()[:255] if sender_email_m else None),
        amount_cents=amount,
        currency=currency,
        memo=(memo_m.group("memo").strip()[:512] if memo_m else None),
        interac_reference=(ref_m.group("ref") if ref_m else None),
        received_at=received,
        from_address=parseaddr(str(msg.get("From", "")))[1].lower(),
    )
