"""Receiver / customer delivery emails: one premium layout, English and French.

Used for every email a parcel *recipient* (booker or consignee) gets about a delivery.
Merchant/admin copies of the same events keep the business layout.

CASL: these are transactional (s.6(6)): about a delivery already under way to this
person. No promotion, sender always identified, no unsubscribe needed (and none offered,
so nobody mistakes it for marketing). PIPEDA: only the tracking number, the merchant
name and the delivery window appear; never the address, phone or the driver's surname.
Proof photos sit behind a signed, expiring link, never inline.
"""

from __future__ import annotations

import html
from typing import Any
from urllib.parse import quote

NAVY = "#0b1220"
ACCENT = "#2563eb"  # 5.2:1 on white (website #3b82f6 is 3.7:1, too light for text)
ACCENT_SOFT = "#eff6ff"
INK = "#0f172a"
BODY = "#334155"
MUTED = "#475569"  # 7.2:1 on white, 6.6:1 on canvas
LINE = "#e2e8f0"
CANVAS = "#f1f5f9"
WARN = "#b45309"
WARN_SOFT = "#fffbeb"
OK = "#047857"
OK_SOFT = "#ecfdf5"
FONT = "Inter, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

LEGAL_ENTITY = "PorterChain Logistics Inc."
LEGAL_ADDRESS = "Toronto, ON, Canada"

#: template -> (kind, tone, progress step or None)
RECEIVER_TEMPLATES: dict[str, tuple[str, str, int | None]] = {
    "cx_out_for_delivery": ("out_for_delivery", "info", 2),
    "cx_next_stop": ("next_stop", "info", 2),
    "cx_eta_20": ("eta", "info", 2),
    "cx_delivered": ("delivered", "ok", 3),
    "cx_attempted": ("attempted", "warn", None),
    "cx_rescheduled": ("rescheduled", "info", None),
    "cx_schedule_request": ("schedule_request", "info", 0),
    "order_booked": ("booked", "info", 0),
    "parcel_picked_up": ("picked_up", "info", 1),
    "delivered": ("delivered", "ok", 3),
    "delivery_failed": ("attempted", "warn", None),
    "order_cancelled": ("cancelled", "warn", None),
}

COPY: dict[str, dict[str, Any]] = {
    "en": {
        "steps": ("Booked", "Picked up", "On the way", "Delivered"),
        "tracking": "Tracking",
        "from": "From",
        "window": "Delivery window",
        "eta": "Arriving in",
        "minutes": "about {n} min",
        "report": "Report a problem",
        "track": "Track your delivery",
        "manage": "Add delivery instructions",
        "pod": "View proof of delivery",
        "reschedule": "Choose a new time",
        "pick": "Pick a delivery time",
        "footer_service": (
            "This is a service message about a delivery to you from {merchant}, delivered by "
            "{entity}, {address}. It is not marketing."
        ),
        "footer_help": "Questions? {help}",
        "footer_privacy": "Privacy",
        "privacy_path": "/en/privacy",
        "kinds": {
            "booked": (
                "Booked",
                "Your delivery is booked",
                "{merchant} booked a delivery to you. We'll email you when it's on the way.",
            ),
            "picked_up": (
                "Picked up",
                "Your parcel is with us",
                "We picked up your {merchant} parcel. Next stop: you.",
            ),
            "out_for_delivery": (
                "Out for delivery",
                "Arriving today",
                "Your {merchant} delivery is on the road and will arrive today.{window_sentence}",
            ),
            "next_stop": (
                "Almost there",
                "{stops_line}",
                "Your driver is heading to you with your {merchant} delivery.",
            ),
            "eta": (
                "Arriving soon",
                "About {eta_minutes} minutes away",
                "Your {merchant} delivery is close.{id_sentence}",
            ),
            "delivered": (
                "Delivered",
                "Your delivery has arrived",
                "Your {merchant} parcel was delivered. Photo and signature proof are one tap away.",
            ),
            "attempted": (
                "Missed delivery",
                "We couldn't deliver today",
                "We tried to deliver your {merchant} parcel but couldn't complete it. {attempt_sentence}",
            ),
            "rescheduled": (
                "Rescheduled",
                "Your new delivery time is set",
                "Your {merchant} delivery is now booked for {window_label}.",
            ),
            "schedule_request": (
                "Action needed",
                "Choose your delivery time",
                "{merchant} needs you to pick a delivery window before we dispatch your parcel.",
            ),
            "cancelled": (
                "Cancelled",
                "This delivery was cancelled",
                "Your {merchant} delivery was cancelled. If this is unexpected, contact {merchant}.",
            ),
        },
        "attempt_reschedule": "Choose a new time below. It takes ten seconds.",
        "attempt_contact": "We'll contact you to arrange another attempt.",
        "attempt_return": "After repeated attempts this parcel is going back to the sender.",
        "id_sentence": " Please have photo ID ready.",
        "window_sentence": " Expected {label}.",
        "next": "You're next!",
        "stops_away": "You're {n} stops away",
        "stop_away": "You're 1 stop away",
        "sender_fallback": "Your sender",
    },
    "fr": {
        "steps": ("Réservée", "Ramassée", "En route", "Livrée"),
        "tracking": "Suivi",
        "from": "De",
        "window": "Plage de livraison",
        "eta": "Arrivée dans",
        "minutes": "environ {n} min",
        "report": "Signaler un problème",
        "track": "Suivre ma livraison",
        "manage": "Ajouter des instructions",
        "pod": "Voir la preuve de livraison",
        "reschedule": "Choisir un nouveau moment",
        "pick": "Choisir un moment de livraison",
        "footer_service": (
            "Ceci est un message de service concernant une livraison qui vous est destinée de la part de "
            "{merchant}, effectuée par {entity}, {address}. Ce n'est pas un message publicitaire."
        ),
        "footer_help": "Des questions? {help}",
        "footer_privacy": "Confidentialité",
        "privacy_path": "/fr/privacy",
        "kinds": {
            "booked": (
                "Réservée",
                "Votre livraison est réservée",
                "{merchant} a réservé une livraison pour vous. Nous vous écrirons quand elle sera en route.",
            ),
            "picked_up": (
                "Ramassée",
                "Votre colis est entre nos mains",
                "Nous avons ramassé votre colis {merchant}. Prochain arrêt : chez vous.",
            ),
            "out_for_delivery": (
                "En livraison",
                "Arrivée aujourd'hui",
                "Votre livraison {merchant} est en route et arrivera aujourd'hui.{window_sentence}",
            ),
            "next_stop": (
                "Presque arrivé",
                "{stops_line}",
                "Votre chauffeur se dirige vers vous avec votre livraison {merchant}.",
            ),
            "eta": (
                "Arrivée imminente",
                "Environ {eta_minutes} minutes",
                "Votre livraison {merchant} approche.{id_sentence}",
            ),
            "delivered": (
                "Livrée",
                "Votre livraison est arrivée",
                "Votre colis {merchant} a été livré. La photo et la signature sont à portée de clic.",
            ),
            "attempted": (
                "Livraison manquée",
                "Nous n'avons pas pu livrer aujourd'hui",
                "Nous avons tenté de livrer votre colis {merchant}, sans succès. {attempt_sentence}",
            ),
            "rescheduled": (
                "Reportée",
                "Votre nouveau moment de livraison est confirmé",
                "Votre livraison {merchant} est maintenant prévue {window_label}.",
            ),
            "schedule_request": (
                "Action requise",
                "Choisissez votre moment de livraison",
                "{merchant} vous demande de choisir une plage de livraison avant l'envoi de votre colis.",
            ),
            "cancelled": (
                "Annulée",
                "Cette livraison a été annulée",
                "Votre livraison {merchant} a été annulée. Si c'est inattendu, communiquez avec {merchant}.",
            ),
        },
        "attempt_reschedule": "Choisissez un nouveau moment ci-dessous. Cela prend dix secondes.",
        "attempt_contact": "Nous vous contacterons pour planifier une nouvelle tentative.",
        "attempt_return": "Après plusieurs tentatives, ce colis retourne à l'expéditeur.",
        "id_sentence": " Veuillez avoir une pièce d'identité avec photo.",
        "window_sentence": " Prévue {label}.",
        "next": "Vous êtes le prochain arrêt!",
        "stops_away": "Plus que {n} arrêts avant vous",
        "stop_away": "Plus qu'un arrêt avant vous",
        "sender_fallback": "Votre expéditeur",
    },
}


def is_receiver_email(template: str, context: dict[str, Any]) -> bool:
    return template in RECEIVER_TEMPLATES and context.get("audience") == "receiver"


def language(context: dict[str, Any]) -> str:
    lang = str(context.get("lang") or "en").lower()[:2]
    return lang if lang in COPY else "en"


def _e(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _g(ctx: dict[str, Any], *keys: str) -> str:
    for key in keys:
        val = ctx.get(key)
        if val not in (None, ""):
            return str(val)
    return ""


class _Safe(dict):
    def __missing__(self, key: str) -> str:
        return ""


def _fmt(text: str, values: dict[str, Any]) -> str:
    return text.format_map(_Safe(values))


def _stops_line(c: dict[str, Any], ctx: dict[str, Any]) -> str:
    raw = ctx.get("stops_away")
    try:
        n = int(raw) if raw not in (None, "") else 0
    except (TypeError, ValueError):
        n = 0
    if n <= 0:
        return c["next"]
    return c["stop_away"] if n == 1 else _fmt(c["stops_away"], {"n": n})


def _attempt_sentence(c: dict[str, Any], ctx: dict[str, Any]) -> str:
    if ctx.get("returning_to_sender"):
        return c["attempt_return"]
    if _g(ctx, "reschedule_url"):
        return c["attempt_reschedule"]
    return c["attempt_contact"]


def report_problem_url(ctx: dict[str, Any], lang: str) -> str:
    explicit = _g(ctx, "report_problem_url")
    if explicit:
        return explicit
    support = _g(ctx, "support_email") or "support@porterchain.com"
    tracking = _g(ctx, "tracking_number")
    subject = ("Problème de livraison " if lang == "fr" else "Problem with delivery ") + tracking
    return f"mailto:{support}?subject={quote(subject.strip())}"


def _actions(
    kind: str, c: dict[str, Any], ctx: dict[str, Any], lang: str
) -> tuple[tuple[str, str], list[tuple[str, str]]]:
    """(primary (label,url), secondary links)."""
    track = _g(ctx, "signed_track_url", "public_track_url")
    manage = _g(ctx, "manage_url_signed")
    resched = _g(ctx, "reschedule_url")
    pod = _g(ctx, "pod_url_signed", "signed_track_url", "public_track_url")
    report = report_problem_url(ctx, lang)
    if kind == "delivered":
        return (c["pod"], pod), [(c["report"], report)]
    if kind == "attempted":
        primary = (c["reschedule"], resched) if resched else (c["track"], track)
        extra = [(c["track"], track)] if resched and track else []
        return primary, [*extra, (c["report"], report)]
    if kind == "schedule_request":
        return (c["pick"], resched or manage or track), []
    if kind in ("out_for_delivery", "next_stop", "eta"):
        return (c["track"], track), [(c["manage"], manage)] if manage else []
    if kind == "cancelled":
        return ("", ""), [(c["report"], report)]
    return (c["track"], track), []


def _progress(step: int | None, c: dict[str, Any]) -> str:
    if step is None:
        return ""
    cells = []
    for i, label in enumerate(c["steps"]):
        done = i <= step
        bar = ACCENT if done else LINE
        color = INK if i == step else (BODY if done else MUTED)
        weight = "700" if i == step else "500"
        cells.append(
            f'<td width="25%" style="padding:0 3px;vertical-align:top;">'
            f'<div style="height:4px;border-radius:4px;background:{bar};font-size:0;line-height:0;">&nbsp;</div>'
            f'<p style="margin:8px 0 0;font-family:{FONT};font-size:11px;color:{color};font-weight:{weight};">{_e(label)}</p></td>'
        )
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:4px 0 24px;"><tr>'
        + "".join(cells)
        + "</tr></table>"
    )


def _pill(text: str, tone: str) -> str:
    fg, bg = {"ok": (OK, OK_SOFT), "warn": (WARN, WARN_SOFT)}.get(tone, (ACCENT, ACCENT_SOFT))
    return (
        f'<span style="display:inline-block;padding:5px 10px;border-radius:999px;background:{bg};color:{fg};'
        f'font-family:{FONT};font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;">{_e(text)}</span>'
    )


def _rows(rows: list[tuple[str, str]]) -> str:
    parts = [
        f'<tr><td style="padding:12px 0;border-top:1px solid {LINE};font-family:{FONT};font-size:13px;color:{MUTED};">{_e(k)}</td>'
        f'<td style="padding:12px 0;border-top:1px solid {LINE};font-family:{FONT};font-size:14px;color:{INK};font-weight:600;text-align:right;">{_e(v)}</td></tr>'
        for k, v in rows
        if v
    ]
    if not parts:
        return ""
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:24px 0 0;border-bottom:1px solid {LINE};">{"".join(parts)}</table>'


def _button(label: str, url: str, colour: str = NAVY) -> str:
    if not (label and url):
        return ""
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" style="margin:28px 0 0;"><tr>'
        f'<td class="pc-btn" bgcolor="{colour}" style="border-radius:12px;background:{colour};">'
        f'<a href="{_e(url)}" style="display:inline-block;padding:15px 26px;font-family:{FONT};font-size:15px;font-weight:700;'
        f'color:#ffffff;text-decoration:none;">{_e(label)} &rarr;</a></td></tr></table>'
    )


def _links(links: list[tuple[str, str]]) -> str:
    items = [
        f'<a href="{_e(u)}" style="color:{ACCENT};text-decoration:none;font-weight:600;">{_e(lbl)}</a>'
        for lbl, u in links
        if lbl and u
    ]
    if not items:
        return ""
    sep = f'<span style="color:{LINE};">&nbsp;&nbsp;|&nbsp;&nbsp;</span>'
    return f'<p style="margin:18px 0 0;font-family:{FONT};font-size:14px;">{sep.join(items)}</p>'


#: Dark-mode safe: clients that honour prefers-color-scheme get a navy canvas with
#: light text; the rest (Gmail app, Outlook) keep the light design, whose colours
#: all pass AA on white so auto-inversion stays readable.
DARK_CSS = (
    "@media (prefers-color-scheme: dark){"
    ".pc-canvas{background:#0b1220!important}"
    ".pc-card{background:#111a2e!important;border-color:#1e293b!important}"
    ".pc-ink{color:#f8fafc!important}.pc-body{color:#cbd5e1!important}.pc-muted{color:#94a3b8!important}"
    ".pc-card td,.pc-card p{color:#e2e8f0!important}.pc-card a{color:#93c5fd!important}"
    ".pc-btn{background:#2563eb!important}.pc-card .pc-btn a{color:#ffffff!important}"
    "}"
    "@media only screen and (max-width:420px){.pc-card{padding:28px 20px!important}h1{font-size:24px!important}}"
)


def preheader(text: str) -> str:
    """Inbox preview line; the zero-width filler stops body text leaking into the preview."""
    filler = "&#847;&zwnj;&nbsp;" * 60
    return (
        '<div style="display:none;max-height:0;max-width:0;overflow:hidden;opacity:0;mso-hide:all;'
        f'font-size:1px;line-height:1px;color:transparent;">{_e(text)}{filler}</div>'
    )


def _brand_mark(ctx: dict[str, Any], merchant: str) -> str:
    logo = _g(ctx, "logo_url")
    if logo.startswith("https://"):
        return (
            f'<img src="{_e(logo)}" alt="{_e(merchant)}" height="28" '
            f'style="display:block;height:28px;width:auto;max-width:140px;border:0;margin-left:auto;" />'
        )
    return _e(merchant)


def render_receiver_email(template: str, ctx: dict[str, Any]) -> tuple[str, str, str]:
    """Return (subject, text, html) for a receiver delivery email."""
    kind, tone, step = RECEIVER_TEMPLATES[template]
    lang = language(ctx)
    c = COPY[lang]
    merchant = _g(ctx, "merchant_name") or c["sender_fallback"]
    window_label = _g(ctx, "window_label")
    values = {
        "merchant": merchant,
        "eta_minutes": _g(ctx, "eta_minutes") or "20",
        "stops_line": _stops_line(c, ctx),
        "window_label": window_label,
        "window_sentence": _fmt(c["window_sentence"], {"label": window_label}) if window_label else "",
        "id_sentence": c["id_sentence"] if ctx.get("id_required") else "",
        "attempt_sentence": _attempt_sentence(c, ctx),
    }
    eyebrow, headline, lead = (_fmt(x, values) for x in c["kinds"][kind])
    # Admin-edited copy (template manager): subject and intro only; layout stays fixed.
    if _g(ctx, "copy_intro"):
        lead = _fmt(_g(ctx, "copy_intro"), {**values, "tracking": _g(ctx, "tracking_number")})
    tracking = _g(ctx, "tracking_number")
    subject = f"{headline} · {merchant}" + (f" · {tracking}" if tracking else "")
    if _g(ctx, "copy_subject"):
        subject = _fmt(_g(ctx, "copy_subject"), {**values, "tracking": tracking})
    (cta_label, cta_url), secondary = _actions(kind, c, ctx, lang)
    rows = [(c["tracking"], tracking), (c["from"], merchant), (c["window"], window_label)]
    if kind == "eta":
        rows.append((c["eta"], _fmt(c["minutes"], {"n": values["eta_minutes"]})))

    help_line = _g(ctx, "help_line") or _g(ctx, "support_email") or "support@porterchain.com"
    site = (_g(ctx, "website_url") or "https://porterchain.com").rstrip("/")
    footer = _fmt(c["footer_service"], {"merchant": merchant, "entity": LEGAL_ENTITY, "address": LEGAL_ADDRESS})
    help_txt = _fmt(c["footer_help"], {"help": help_line})
    privacy_url = site + c["privacy_path"]

    text_lines = [headline, "", lead, ""]
    text_lines += [f"{k}: {v}" for k, v in rows if v]
    if cta_label and cta_url:
        text_lines += ["", f"{cta_label}: {cta_url}"]
    text_lines += [f"{lbl}: {u}" for lbl, u in secondary if lbl and u]
    text_lines += ["", "--", footer, help_txt, f"{c['footer_privacy']}: {privacy_url}"]
    text = "\n".join(text_lines)

    doc = f"""<!DOCTYPE html>
<html lang="{"fr-CA" if lang == "fr" else "en-CA"}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="color-scheme" content="light dark" />
  <meta name="supported-color-schemes" content="light dark" />
  <title>{_e(headline)}</title>
  <style>{DARK_CSS}</style>
</head>
<body class="pc-canvas" style="margin:0;padding:0;background:{CANVAS};">
  {preheader(lead)}
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" class="pc-canvas" style="background:{CANVAS};padding:40px 12px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;">
        <tr><td style="padding:0 4px 16px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
            <td class="pc-ink" style="font-family:{FONT};font-size:15px;font-weight:800;letter-spacing:-0.01em;color:{NAVY};">PorterChain</td>
            <td align="right" class="pc-muted" style="font-family:{FONT};font-size:12px;color:{MUTED};">{_brand_mark(ctx, merchant)}</td>
          </tr></table>
        </td></tr>
        <tr><td class="pc-card" bgcolor="#ffffff" style="background:#ffffff;border:1px solid {LINE};border-radius:20px;padding:36px 28px 32px;">
          {_progress(step, c)}
          {_pill(eyebrow, tone)}
          <h1 class="pc-ink" style="margin:16px 0 10px;font-family:{FONT};font-size:28px;line-height:1.15;font-weight:800;letter-spacing:-0.025em;color:{NAVY};">{_e(headline)}</h1>
          <p class="pc-body" style="margin:0;font-family:{FONT};font-size:16px;line-height:1.6;color:{BODY};">{_e(lead)}</p>
          {_rows(rows)}
          {_button(cta_label, cta_url, _g(ctx, "brand_color") or NAVY)}
          {_links(secondary)}
        </td></tr>
        <tr><td style="padding:22px 8px 0;">
          <p class="pc-muted" style="margin:0;font-family:{FONT};font-size:12px;line-height:1.6;color:{MUTED};">{_e(footer)}</p>
          <p class="pc-muted" style="margin:8px 0 0;font-family:{FONT};font-size:12px;line-height:1.6;color:{MUTED};">{_e(help_txt)}
            &nbsp;·&nbsp;<a href="{_e(privacy_url)}" style="color:{MUTED};">{_e(c["footer_privacy"])}</a></p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""
    return subject, text, doc
