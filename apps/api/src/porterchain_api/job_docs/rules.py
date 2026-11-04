"""Pickup document requirements (doc 70 §2.2 matrix after C-triggers, doc 80/81 rules)."""
from __future__ import annotations

from typing import Any

#: doc -> (label, needs: media|scan, needs seal no., blocks pickup when missing)
PICKUP_DOCS: dict[str, dict[str, Any]] = {
    "bol": {"label": "Bill of lading", "seal": False, "blocking": True},
    "packing_list": {"label": "Packing list", "seal": False, "blocking": False},
    "commercial_invoice": {"label": "Commercial invoice", "seal": False, "blocking": True},
    "cbsa_release": {"label": "CBSA release", "seal": False, "blocking": True},
    "pharmacy_custody": {"label": "Pharmacy custody form", "seal": False, "blocking": True},
    "dg_declaration": {"label": "Dangerous goods declaration", "seal": False, "blocking": True},
    "seal_number": {"label": "Seal number", "seal": True, "blocking": True},
    "signed_handover": {"label": "Signed handover", "seal": False, "blocking": True},
}


def required_pickup_docs(documents: set[str] | list[str], flags: dict[str, Any]) -> list[str]:
    """`documents` = active docs for the order (packs.documents_for + C-trigger evaluation)."""
    d = set(documents)
    out = []
    if "bol" in d:  # C1
        out.append("bol")
    if "packing_slip" in d or "pallet_manifest" in d:
        out.append("packing_list")
    if "customs_docs" in d and flags.get("customs_released"):
        out += ["commercial_invoice", "cbsa_release"]
    if "rx_custody_log" in d or flags.get("rx"):
        out.append("pharmacy_custody")
    if "tdg" in d and flags.get("dangerous_goods"):
        out.append("dg_declaration")
    if flags.get("sealed") or "rx_custody_log" in d or flags.get("rx"):
        out.append("seal_number")
    if out or flags.get("signed_handover"):
        out.append("signed_handover")  # any professional pickup ends with a signed handover
    return out


def validate_capture(doc_type: str, body: dict[str, Any]) -> None:
    spec = PICKUP_DOCS.get(doc_type)
    if not spec:
        raise ValueError("unknown_document")
    if not (body.get("media_key") or body.get("scan_code")):
        raise ValueError("photo_or_scan_required")
    if not (body.get("shipper_name") or "").strip():
        raise ValueError("shipper_name_required")
    if not body.get("shipper_signature_key"):
        raise ValueError("shipper_signature_required")
    if spec["seal"] and not (body.get("seal_no") or "").strip():
        raise ValueError("seal_no_required")


def gate(required: list[str], captured: dict[str, str]) -> list[str]:
    """Blockers: blocking docs not captured; non-blocking docs neither captured nor reported missing."""
    out = []
    for d in required:
        st = captured.get(d)
        if st == "captured":
            continue
        if st == "missing" and not PICKUP_DOCS[d]["blocking"]:
            continue
        out.append(d)
    return out


def reminders(required: list[str], captured: dict[str, str], phase: str, lang: str = "en") -> list[str]:
    todo = [d for d in required if captured.get(d) != "captured"]
    if not todo:
        return []
    names = ", ".join(PICKUP_DOCS[d]["label"] for d in todo)
    if phase == "before_arrival":
        return [f"Before you arrive: have the shipper ready {names}." if lang == "en"
                else f"Avant d'arriver : demandez à l'expéditeur de préparer {names}."]
    return [f"At pickup: capture {names} with the shipper's name and signature before confirming." if lang == "en"
            else f"À la collecte : saisissez {names} avec le nom et la signature de l'expéditeur avant de confirmer."]
