"""EDI export for enterprise shippers (Ravi 2026-10-29, doc 84 Q7): X12 214 (shipment status) and
856 (ship notice / manifest) style files built from batch parcels and custody events.

Export only. No inbound EDI and no VAN connection; the file is downloaded and sent by the shipper's
own EDI tool. Status mapping follows common X12 AT7 codes (to verify with each trading partner).
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from porterchain_api.ops_rules.codes import canonical

#: Internal custody kind -> X12 AT701 shipment status code.
AT7_STATUS = {
    "pickup": "AF",          # picked up / departed pickup location
    "handover_out": "P1",    # departed terminal/transfer point
    "handover_in": "X4",     # arrived at transfer point
    "delivered": "D1",       # completed unloading / delivered
    "reattempt": "SD",       # shipment delayed (same-day re-attempt)
    "return": "A3",          # returned to shipper
    "return_to_depot": "A3",
    "exception": "SD",
    "missing": "AP",         # delivery not completed
}
#: Internal exception code -> X12 AT702 status reason code.
AT7_REASON = {"count_short": "AM", "parcel_damaged": "AH", "customer_unavailable": "A1",
              "wrong_address": "A2", "failed_delivery": "AP"}


def _reason(code: str | None) -> str:
    if not code:
        return "NS"
    try:
        return AT7_REASON.get(canonical(code), "NS")
    except ValueError:
        return "NS"
SEG, EL = "~", "*"


def _envelope(kind: str, sender: str, receiver: str, body: list[str], ctl: int, now: datetime) -> str:
    d, t = now.strftime("%y%m%d"), now.strftime("%H%M")
    isa = ["ISA", "00", " " * 10, "00", " " * 10, "ZZ", sender.ljust(15)[:15], "ZZ", receiver.ljust(15)[:15],
           d, t, "U", "00401", f"{ctl:09d}", "0", "P", ">"]
    gs_code = {"214": "QM", "856": "SH"}[kind]
    st = [f"ST{EL}{kind}{EL}{ctl % 10000:04d}", *body]
    st.append(f"SE{EL}{len(st) + 1}{EL}{ctl % 10000:04d}")
    segs = [EL.join(isa), EL.join(["GS", gs_code, sender, receiver, now.strftime("%Y%m%d"), t, str(ctl), "X", "004010"]),
            *st, EL.join(["GE", "1", str(ctl)]), EL.join(["IEA", "1", f"{ctl:09d}"])]
    return SEG.join(segs) + SEG


def x12_214(parcels: list[dict[str, Any]], events: list[dict[str, Any]], *, sender: str = "PORTERCHAIN",
            receiver: str = "PARTNER", ctl: int = 1, scac: str = "PCHN", now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    by_parcel: dict[str, list[dict[str, Any]]] = {}
    for e in events:
        by_parcel.setdefault(e["parcel_id"], []).append(e)
    body: list[str] = []
    for p in parcels:
        refs = [p["barcode"], *(p.get("client_labels") or [])[:1]]
        body.append(EL.join(["B10", refs[-1], p["barcode"], scac]))
        for i, e in enumerate(sorted(by_parcel.get(p["id"], []), key=lambda e: e["at"]), start=1):
            code = AT7_STATUS.get(e["kind"])
            if not code:
                continue
            reason = _reason(e.get("exception"))
            at = e["at"]
            body.append(EL.join(["LX", str(i)]))
            body.append(EL.join(["AT7", code, reason, "", "", at.strftime("%Y%m%d"), at.strftime("%H%M"), "LT"]))
    return _envelope("214", sender, receiver, body, ctl, now)


def x12_856(batch: dict[str, Any], parcels: list[dict[str, Any]], *, sender: str = "PORTERCHAIN",
            receiver: str = "PARTNER", ctl: int = 1, now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    body = [EL.join(["BSN", "00", batch["id"][:30], now.strftime("%Y%m%d"), now.strftime("%H%M")]),
            EL.join(["HL", "1", "", "S"]), EL.join(["TD1", "CTN", str(len(parcels))])]
    for n, p in enumerate(parcels, start=2):
        body.append(EL.join(["HL", str(n), "1", "P"]))
        body.append(EL.join(["MAN", "GM", p["barcode"]]))
        for lab in (p.get("client_labels") or [])[:3]:
            body.append(EL.join(["REF", "CR", str(lab)[:30]]))
        body.append(EL.join(["N1", "ST", str(p.get("recipient") or "")[:60]]))
        body.append(EL.join(["N3", str(p.get("address") or "")[:55]]))
    body.append(EL.join(["CTT", str(len(parcels) + 1)]))
    return _envelope("856", sender, receiver, body, ctl, now)
