"""EN / FR copy for the retail customer emails (Quebec-ready French, plain words)."""

from __future__ import annotations

from typing import Any

COPY: dict[str, dict[str, str]] = {
    "en": {
        "confirmed.subject": "You're booked: {tracking_number}",
        "confirmed.eyebrow": "Booking confirmed",
        "confirmed.headline": "You're booked.",
        "confirmed.lead": "We're matching a driver now. Track live, get your receipt, or cancel free before pickup.",
        "confirmed.cta": "Track & manage",
        "confirmed.account": "Your account, no password needed",
        "confirmed.prefs": "Email preferences",
        "confirmed.foot": "Your account was created from this email. You can ask us to delete it any time from Email preferences.",
        "confirmed.body": "You're booked.\n\nTracking: {tracking_number}\nAmount: {amount_display}\n\nTrack, receipt and cancel: {manage_track_url}",
        "again.subject": "Send it again? Same route, one tap",
        "again.eyebrow": "Delivered",
        "again.headline": "Send it again?",
        "again.lead": "Same pickup, same drop-off, fresh price. One tap and you are booked.",
        "nudge.subject": "Same as last time?",
        "nudge.eyebrow": "Your usual delivery",
        "nudge.headline": "Same as last time?",
        "nudge.lead": "It's about time for your usual delivery. Same route, fresh price, one tap.",
        "again.cta": "Send again",
        "again.row": "Last delivery",
        "again.sender": "Sent by PorterChain Logistics Inc., Toronto, ON.",
        "again.stop": "Stop these reminders",
        "again.body": "{lead}\n\nBook it in one tap: {send_again_url}\n\nStop these reminders: {unsubscribe_url}\nPorterChain Logistics Inc., Toronto, ON",
        "row.tracking": "Tracking",
        "row.order": "Order",
        "row.invoice": "Invoice",
        "row.amount": "Amount",
    },
    "fr": {
        "confirmed.subject": "C'est réservé : {tracking_number}",
        "confirmed.eyebrow": "Réservation confirmée",
        "confirmed.headline": "C'est réservé.",
        "confirmed.lead": "Nous trouvons un chauffeur. Suivez en direct, obtenez votre reçu ou annulez sans frais avant la collecte.",
        "confirmed.cta": "Suivre et gérer",
        "confirmed.account": "Accéder à votre compte (sans mot de passe)",
        "confirmed.prefs": "Préférences courriel",
        "confirmed.foot": "Votre compte a été créé à partir de ce courriel. Vous pouvez demander sa suppression en tout temps dans Préférences courriel.",
        "confirmed.body": "C'est réservé.\n\nSuivi : {tracking_number}\nMontant : {amount_display}\n\nSuivi, reçu et annulation : {manage_track_url}",
        "again.subject": "On recommence? Même trajet, un seul clic",
        "again.eyebrow": "Livré",
        "again.headline": "On recommence?",
        "again.lead": "Même collecte, même livraison, nouveau prix. Un clic et c'est réservé.",
        "nudge.subject": "Comme la dernière fois?",
        "nudge.eyebrow": "Votre livraison habituelle",
        "nudge.headline": "Comme la dernière fois?",
        "nudge.lead": "C'est bientôt le moment de votre livraison habituelle. Même trajet, nouveau prix, un clic.",
        "again.cta": "Réserver à nouveau",
        "again.row": "Dernière livraison",
        "again.sender": "Envoyé par PorterChain Logistics Inc., Toronto (Ontario).",
        "again.stop": "Arrêter ces rappels",
        "again.body": "{lead}\n\nRéservez en un clic : {send_again_url}\n\nArrêter ces rappels : {unsubscribe_url}\nPorterChain Logistics Inc., Toronto (Ontario)",
        "row.tracking": "Suivi",
        "row.order": "Commande",
        "row.invoice": "Facture",
        "row.amount": "Montant",
    },
}


def lang(ctx: dict[str, Any]) -> str:
    return "fr" if str(ctx.get("locale") or "").lower().startswith("fr") else "en"


def t(ctx: dict[str, Any], key: str) -> str:
    return COPY[lang(ctx)].get(key) or COPY["en"][key]


class _Blank(dict):
    def __missing__(self, key: str) -> str:
        return ""


def _fmt(text: str, ctx: dict[str, Any]) -> str:
    return text.format_map(_Blank({k: ("" if v is None else str(v)) for k, v in ctx.items()}))


def localize_email(template: str, ctx: dict[str, Any], subject: str, body: str) -> tuple[str, str]:
    """Subject + plain text for the retail emails. Other templates pass through."""
    if template == "booking_confirmed" and ctx.get("manage_track_url"):
        body = _fmt(t(ctx, "confirmed.body"), ctx)
        if ctx.get("account_url"):
            body += f"\n{t(ctx, 'confirmed.account')}: {ctx['account_url']}"
        return _fmt(t(ctx, "confirmed.subject"), ctx), body
    if template == "fast_send_again":
        kind = "nudge" if ctx.get("nudge") else "again"
        lead = t(ctx, f"{kind}.lead")
        return _fmt(t(ctx, f"{kind}.subject"), ctx), _fmt(t(ctx, "again.body"), {**ctx, "lead": lead})
    return subject, body
