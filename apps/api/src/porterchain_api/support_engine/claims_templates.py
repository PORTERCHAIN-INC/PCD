"""Claim letters for admin review (Ravi 2026-11-04). Drafts only: nothing here is sent automatically.

Wording rules: acknowledge receipt without admitting liability, cite the Terms of Service and the
Uniform Conditions of Carriage, state limits as ceilings, never mention charging the deductible.
"""
from __future__ import annotations

from typing import Any

from porterchain_api.support_engine import claims_policy as CP
from porterchain_pricing import insurance_policy as POLICY

SIGN_OFF = "PorterChain Claims\nPorterchain Inc., 91 Breton Ave E, Unit 0, Mississauga ON L4Z 4K5\nops@porterchain.com"
WITHOUT_PREJUDICE = (
    "This message is sent without prejudice and is not an admission of liability. "
    "Our liability is governed by our Terms of Service and the Ontario Uniform Conditions of Carriage "
    "(O. Reg. 643/05, Sch. 1)."
)


def _money(cents: int | None) -> str:
    return f"${(int(cents or 0)) / 100:,.2f}"


def acknowledgement(ref: str, order_number: str, a: dict[str, Any]) -> dict[str, str]:
    missing = [i["label"] for i in a["evidence"]["items"] if not i["received"]]
    need = ("\n\nTo assess your claim we still need:\n- " + "\n- ".join(missing)) if missing else ""
    body = (
        f"Hello,\n\nThank you for contacting us. We have received your claim {ref} for order {order_number} "
        "and opened an investigation. Please keep the goods and all packaging until we have finished, as we may "
        f"need to inspect them.{need}\n\nWe will reply within one business day and aim to give you a decision "
        "within 30 days of receiving a complete claim.\n\n" + WITHOUT_PREJUDICE + "\n\n" + SIGN_OFF
    )
    return {"subject": f"Claim {ref} received – order {order_number}", "body": body}


def decision_approved(ref: str, order_number: str, amount_cents: int, a: dict[str, Any],
                      basis: str | None = None) -> dict[str, str]:
    cap = a["liability"]
    body = (
        f"Hello,\n\nWe have completed our investigation of claim {ref} for order {order_number}. "
        f"We will pay {_money(amount_cents)} in settlement of this claim.\n\n"
        f"How this was worked out: {basis or 'the value of the goods lost or damaged, as shown by the proof of value'}, "
        f"within the limit that applies to this shipment ({_money(cap['cap_cents'])}). Under our Terms of Service "
        "our liability is $4.41 per kg of the goods affected unless declared-value cover was bought "
        f"(up to $2,500 per parcel), and never more than {_money(cap['limit_cents'])} per shipment.\n\n"
        "No deductible or other charge is passed on to you.\n\n"
        "This payment is in full and final settlement of this claim. If you believe something has been missed, "
        "reply within 30 days with the details.\n\n" + SIGN_OFF
    )
    return {"subject": f"Claim {ref} – decision", "body": body}


def decision_denied(ref: str, order_number: str, reason_key: str, details: str | None = None) -> dict[str, str]:
    reason = CP.DENIAL_REASONS.get(reason_key)
    if not reason:
        raise ValueError("unknown_denial_reason")
    body = (
        f"Hello,\n\nWe have completed our investigation of claim {ref} for order {order_number}. "
        "We are sorry to tell you that we cannot pay this claim.\n\n"
        f"Reason: {reason}" + (f"\n\nWhat we found: {details.strip()}" if details and details.strip() else "")
        + "\n\nIf you have information we have not seen, reply with it within 30 days and we will review the "
        "decision. You may also have other rights under Ontario law.\n\n" + WITHOUT_PREJUDICE + "\n\n" + SIGN_OFF
    )
    return {"subject": f"Claim {ref} – decision", "body": body}


def broker_notice(ref: str, order_number: str, a: dict[str, Any], *, claimed_cents: int | None,
                  loss_date: str | None, description: str | None) -> dict[str, str]:
    """Notice of a possible cargo loss to the broker. Admin reviews and sends it from their own mailbox."""
    body = (
        f"Hello,\n\nPlease note a possible motor truck cargo claim for Porterchain Inc. (client ID PORT1), "
        f"policy {POLICY.POLICY_REF} with {POLICY.INSURER}.\n\n"
        f"- Our claim reference: {ref} (order {order_number})\n"
        f"- Date of loss or damage: {loss_date or 'to be confirmed'}\n"
        f"- Amount claimed by our customer: {_money(claimed_cents)} (not yet verified)\n"
        f"- What happened: {(description or 'under investigation').strip()}\n"
        f"- Evidence on file: {', '.join(i['label'] for i in a['evidence']['items'] if i['received']) or 'none yet'}\n\n"
        f"The amount may exceed our {_money(POLICY.DEDUCTIBLE_CENTS)} deductible. We have not admitted liability "
        "to the claimant. Please advise on next steps and whether an adjuster will be appointed.\n\n" + SIGN_OFF
    )
    return {"to": "Able Insurance Brokers Ltd. (905) 629-2253 – email to be confirmed by Ravi",
            "subject": f"Notice of possible cargo claim – Porterchain Inc. – {ref}", "body": body}
