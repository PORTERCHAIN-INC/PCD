"""Reply drafts (email + WhatsApp) — template engine first, LLM polish optional.

A draft only fills the admin composer. Nothing here sends anything.
"""

from __future__ import annotations

from typing import Any

from porterchain_api.lead_desk.fit_score import TARGET_INDUSTRIES, industry_fit

# One line per vertical: what they care about, in their words.
_HOOKS: dict[str, str] = {
    "Shopify / e-commerce": "same-day delivery for your Shopify orders, booked straight from your store",
    "Pharmacy": "same-day prescription and OTC deliveries with signature and photo proof",
    "Labs / medical": "time-critical specimen and supply runs with chain-of-custody proof",
    "Warehouse / 3PL": "same-day overflow and last-mile runs out of your warehouse",
    "Traders / wholesale": "same-day wholesale drops to your customers across the GTA",
    "Construction": "jobsite deliveries of materials and tools, on the day you need them",
    "Plumbing / electrical": "fast parts runs to job sites so your crews keep working",
}
_DEFAULT_HOOK = (
    "same-day local delivery across the GTA, with live tracking and proof of delivery"
)


def _first_name(lead: Any) -> str:
    name = (getattr(lead, "primary_contact_name", None) or "").strip()
    return name.split()[0] if name else "there"


def _vertical(lead: Any) -> str | None:
    pts, label = industry_fit(lead)
    if pts >= 30:
        return label.split(": ", 1)[1]
    return None


def build_draft(
    lead: Any,
    *,
    channel: str,
    quote: dict[str, Any] | None = None,
    sender: str = "PorterChain",
) -> dict[str, Any]:
    ch = "whatsapp" if channel == "whatsapp" else "email"
    vertical = _vertical(lead)
    hook = _HOOKS.get(vertical or "", _DEFAULT_HOOK)
    hi = f"Hi {_first_name(lead)}"
    company = (getattr(lead, "company_name", None) or "").strip()
    price = ""
    if quote:
        price = (
            f"A {quote['vehicle_label']} from {quote['pickup_fsa']} to {quote['dropoff_fsa']} is "
            f"{quote['amount_display']} CAD incl. HST (postal-area estimate). "
            f"Book it here: {quote['booking_url']}"
        )
    if ch == "whatsapp":
        parts = [f"{hi}, thanks for reaching out to PorterChain!", f"We do {hook}."]
        if price:
            parts.append(price)
        parts.append("Want me to lock in a pickup time today?")
        text = " ".join(parts)
        subject = None
    else:
        subject = (
            f"Your PorterChain delivery quote: {quote['amount_display']}"
            if quote
            else f"Same-day delivery for {company or 'your business'}"
        )
        lines = [
            f"{hi},",
            "",
            f"Thanks for getting in touch. PorterChain does {hook}.",
        ]
        if price:
            lines += ["", price]
        lines += [
            "",
            "If you send me your usual pickup address and how many runs a week you need, "
            "I'll set up your account and the first delivery today.",
            "",
            "Best,",
            sender,
        ]
        text = "\n".join(lines)
    out = {
        "channel": ch,
        "subject": subject,
        "body": text,
        "template": vertical or "general",
        "with_quote": bool(quote),
        "source": "template",
    }
    polished = _llm_polish(text, ch)
    if (
        polished
        and quote
        and (
            quote["amount_display"] not in polished
            or quote["booking_url"] not in polished
        )
    ):
        polished = None  # the AI must not change or drop the price / link
    if polished:
        out.update(body=polished, source="template+ai")
    return out


def _llm_polish(text: str, channel: str) -> str | None:
    from porterchain_api.lead_desk.ai import complete_text

    limit = "under 400 characters" if channel == "whatsapp" else "under 120 words"
    return complete_text(
        "Rewrite this sales reply to be warm, concise and specific, "
        f"{limit}. Keep every price, link and fact exactly as written:\n\n{text}",
        max_tokens=400,
    )


__all__ = ["TARGET_INDUSTRIES", "build_draft"]
