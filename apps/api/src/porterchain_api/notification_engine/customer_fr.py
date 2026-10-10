"""French (fr-CA) copy for customer emails outside the receiver delivery set.

Receiver delivery moments live in receiver_emails (full EN/FR layouts). These are the
other emails a customer can get (booking, payment, invoice, claims, support). Same
business layout, French words. Used when audience=receiver and lang=fr.
"""

from __future__ import annotations

from typing import Any

from porterchain_api.notification_engine.email_layout import build_transactional_html

#: template -> (eyebrow, subject/headline, lead, CTA label)
FR: dict[str, tuple[str, str, str, str]] = {
    "booking_draft_created": ("Brouillon", "Votre réservation est enregistrée", "Terminez la réservation quand vous serez prêt.", "Reprendre"),
    "booking_confirmed": ("Réservation confirmée", "Votre capacité est réservée", "Merci d'avoir réservé avec PorterChain. Nous vous écrirons quand un chauffeur sera assigné.", "Suivre"),
    "consignee_tracking": ("Envoi", "Suivez votre livraison", "Une livraison a été réservée pour vous. Ce lien ouvre la page de suivi publique, sans connexion.", "Suivre cet envoi"),
    "checkout_recovery": ("Réservation", "Votre soumission vous attend", "Terminez le paiement pour réserver la capacité.", "Reprendre le paiement"),
    "order_created": ("Commande", "Commande créée", "Votre commande a été créée.", "Voir"),
    "driver_assigned": ("Chauffeur assigné", "Un chauffeur est assigné", "Un chauffeur s'occupe de votre livraison.", "Suivre"),
    "in_transit": ("En route", "Votre livraison est en route", "Votre colis est en transit.", "Suivre"),
    "near_delivery": ("Presque arrivé", "Votre chauffeur approche", "Votre chauffeur est près de l'adresse de livraison.", "Suivre"),
    "order_delayed": ("Retard", "Votre livraison a du retard", "Nous sommes désolés : votre livraison arrivera plus tard que prévu.", "Suivre"),
    "exception_opened": ("Problème", "Un problème touche cette livraison", "Notre équipe s'en occupe et vous tiendra au courant.", "Suivre"),
    "exception_resolved": ("Réglé", "Le problème est réglé", "Le problème touchant votre livraison est réglé.", "Suivre"),
    "payment_started": ("Paiement", "Paiement en cours", "Nous traitons votre paiement.", ""),
    "payment_receipt": ("Paiement confirmé", "Votre paiement a été reçu", "Merci. Conservez ce courriel pour vos dossiers.", "Voir le reçu"),
    "payment_failed": ("Paiement refusé", "Nous n'avons pas pu traiter votre paiement", "Réessayez ou utilisez une autre carte. Votre soumission est peut-être encore valide.", "Réessayer"),
    "invoice_ready": ("Facture", "Votre facture est prête", "Une facture pour votre livraison est prête.", "Voir la facture"),
    "refund_processed": ("Remboursement", "Votre remboursement est traité", "Le remboursement apparaîtra sur votre relevé d'ici quelques jours.", ""),
    "claim_opened": ("Réclamation", "Votre réclamation est ouverte", "Nous l'examinons et vous répondrons rapidement.", "Voir"),
    "claim_updated": ("Réclamation", "Votre réclamation a été mise à jour", "Consultez la mise à jour.", "Voir"),
    "support_ticket_created": ("Soutien", "Nous avons reçu votre demande", "Notre équipe vous répondra rapidement.", "Voir"),
    "support_reply": ("Soutien", "Nouvelle réponse à votre demande", "Notre équipe a répondu à votre demande.", "Voir"),
}

LABELS = {"Order": "Commande", "Tracking": "Suivi", "Amount": "Montant", "Invoice": "Facture", "Receipt #": "Reçu no"}
FOOTER = "Message de service de PorterChain Logistics Inc., Toronto (Ontario), Canada. Ce n'est pas un message publicitaire."


def _g(ctx: dict[str, Any], *keys: str) -> str:
    for key in keys:
        val = ctx.get(key)
        if val not in (None, ""):
            return str(val)
    return ""


def has_french(template: str) -> bool:
    return template in FR


def render_customer_fr(template: str, ctx: dict[str, Any]) -> tuple[str, str, str]:
    eyebrow, headline, lead, cta = FR[template]
    order = _g(ctx, "order_number")
    tracking = _g(ctx, "tracking_number")
    rows = [
        (LABELS["Order"], order),
        (LABELS["Tracking"], tracking),
        (LABELS["Amount"], _g(ctx, "amount_display")),
        (LABELS["Invoice"], _g(ctx, "invoice_number")),
        (LABELS["Receipt #"], _g(ctx, "receipt_number")),
    ]
    url = _g(ctx, "pay_url", "receipt_url", "recovery_url", "signed_track_url", "public_track_url", "customer_deep_link")
    if url and not url.startswith("http"):
        url = ""
    subject = f"{headline}" + (f" · {tracking or order}" if (tracking or order) else "")
    text = "\n".join(
        [headline, "", lead, ""]
        + [f"{k} : {v}" for k, v in rows if v]
        + ([f"\n{cta} : {url}"] if cta and url else [])
        + ["", "--", FOOTER]
    )
    html = build_transactional_html(
        eyebrow=eyebrow,
        headline=headline,
        lead=lead,
        rows=rows,
        cta_label=cta if url else "",
        cta_url=url,
        note=FOOTER,
        preheader=lead,
        lang="fr-CA",
    )
    return subject, text, html
