"""HTML for customer fast-book emails (text + catalog entry live in notification_engine.templates).

``fast_send_again`` is a commercial electronic message under CASL (implied consent from a
purchase in the last 2 years): it identifies the sender and carries a working unsubscribe link.
"""

from __future__ import annotations

from typing import Any


def fast_html(template: str, ctx: dict[str, Any], *, subject: str, body: str) -> str | None:
    import html as _h

    from porterchain_api.customer_fast.i18n import t
    from porterchain_api.notification_engine.email_layout import (
        FONT,
        MUTED,
        _cta,
        _detail_rows,
        wrap_email,
    )

    if template != "fast_send_again":
        return None
    kind = "nudge" if ctx.get("nudge") else "again"
    unsub = str(ctx.get("unsubscribe_url") or "")
    foot = (
        f'<p style="margin:20px 0 0;font-family:{FONT};font-size:12px;line-height:1.5;color:{MUTED};">'
        f"{_h.escape(t(ctx, 'again.sender'))}"
        + (
            f' <a href="{_h.escape(unsub, quote=True)}" style="color:#334155;text-decoration:underline;">'
            f"{_h.escape(t(ctx, 'again.stop'))}</a>"
            if unsub
            else ""
        )
        + "</p>"
    )
    return _lang(ctx, wrap_email(
        preheader=t(ctx, f"{kind}.lead"),
        eyebrow=t(ctx, f"{kind}.eyebrow"),
        headline=t(ctx, f"{kind}.headline"),
        lead=t(ctx, f"{kind}.lead"),
        details_html=_detail_rows([(t(ctx, "again.row"), str(ctx.get("tracking_number") or ""))])
        + _cta(t(ctx, "again.cta"), str(ctx.get("send_again_url") or ""))
        + foot,
    ))


def booking_confirmed_fast_html(ctx: dict[str, Any], rows: list[tuple[str, str]]) -> str:
    """Retail booking-confirmed email: one CTA, then real links (no raw URLs in the copy)."""
    import html as _h

    from porterchain_api.customer_fast.i18n import t
    from porterchain_api.notification_engine.email_layout import (
        FONT,
        MUTED,
        _cta,
        _detail_rows,
        wrap_email,
    )

    row_keys = {"Tracking": "row.tracking", "Order": "row.order", "Invoice": "row.invoice", "Amount": "row.amount"}
    track = str(ctx.get("manage_track_url") or "")
    links = [
        (t(ctx, "confirmed.account"), str(ctx.get("account_url") or "")),
        (t(ctx, "confirmed.prefs"), str(ctx.get("preferences_url") or "")),
    ]
    link_html = "".join(
        f'<p style="margin:10px 0 0;font-family:{FONT};font-size:14px;">'
        f'<a href="{_h.escape(url, quote=True)}" style="color:#1d4ed8;text-decoration:underline;">'
        f"{_h.escape(label)}</a></p>"
        for label, url in links
        if url
    )
    tracking = next((v for k, v in rows if k == "Tracking"), "")
    foot = (
        f'<p style="margin:16px 0 0;font-family:{FONT};font-size:12px;line-height:1.5;color:{MUTED};">'
        f"{_h.escape(t(ctx, 'confirmed.foot'))}</p>"
    )
    shown = [(t(ctx, row_keys[k]) if k in row_keys else k, v) for k, v in rows if v]
    return _lang(ctx, wrap_email(
        preheader=f"{t(ctx, 'confirmed.headline')} {tracking}".strip(),
        eyebrow=t(ctx, "confirmed.eyebrow"),
        headline=t(ctx, "confirmed.headline"),
        lead=t(ctx, "confirmed.lead"),
        details_html=_detail_rows(shown) + _cta(t(ctx, "confirmed.cta"), track) + link_html + foot,
    ))


def _lang(ctx: dict[str, Any], html_doc: str) -> str:
    from porterchain_api.customer_fast.i18n import lang

    return html_doc.replace('<html lang="en">', '<html lang="fr">', 1) if lang(ctx) == "fr" else html_doc
