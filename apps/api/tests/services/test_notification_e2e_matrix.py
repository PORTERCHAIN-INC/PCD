"""Round 3: end-to-end test of every event in the admin matrix.

For each event: trigger it through the real router (handle_domain_event: hydrate ->
CX hooks -> route table -> matrix -> staff fan-out -> engine), then check every persona
the matrix promises got its email and its bell item, in the right language, with deep
links, and that firing the same event again (and delivering twice) sends nothing new.

No real sends: the SMTP/ZeptoMail senders capture instead of sending.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from uuid import uuid4

import porterchain_api.main  # noqa: F401
import pytest
from porterchain_api.admin_models import AdminUser
from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.booking_models import Order
from porterchain_api.notification_engine import center
from porterchain_api.notification_engine.deep_links import FALLBACK
from porterchain_api.notification_engine.engine import get_notification_engine
from porterchain_api.notification_engine.event_router import handle_domain_event
from porterchain_api.notification_engine.models import NotificationRecord

FRENCH_HINTS = ("livraison", "colis", "commande", "Votre", "votre", "Livr", "facture", "paiement", "réclamation", "demande")
#: CX row -> (event that drives it, extra payload). schedule_request is merchant-initiated (no domain event).
CX_TRIGGERS = {
    "out_for_delivery": ("order.in_transit", {"status": "IN_TRANSIT"}),
    "next_stop": ("order.stop_completed", {"remaining_stops_before": 1}),
    "eta_20": ("order.near_delivery", {"eta_minutes": 18}),
    "delivered": ("order.delivered", {}),
    "attempted": ("order.failed", {"reason": "no_answer"}),
    "rescheduled": ("order.rescheduled", {"window_code": "w1", "window_label": "Sat 10:00-12:00"}),
}


@pytest.fixture
def captured(monkeypatch):
    from porterchain_api.notification_engine import delivery_service as ds

    sent: list[dict] = []

    def _capture(self, recipient, template, context):  # noqa: ARG001
        sent.append({"to": recipient, "template": template, "id": context.get("notification_id")})

    def _boom(*_a, **_k):
        raise AssertionError("real send attempted")

    monkeypatch.setattr(ds.DeliveryService, "_send_email", _capture)
    for name in ("_send_sms", "_send_push", "_send_sms_twilio"):
        monkeypatch.setattr(ds.DeliveryService, name, _boom)
    return sent


@pytest.fixture
def staff(db, monkeypatch):
    user = AdminUser(
        id=str(uuid4()), clerk_user_id=f"e2e-{uuid4().hex[:6]}", email=f"ops-{uuid4().hex[:6]}@porterchain.com",
        role="super_admin", is_active=True,
    )
    db.add(user)
    db.commit()
    # Staff email goes only to the ops watch list; put this staff member on it.
    monkeypatch.setattr(
        "porterchain_api.notification_engine.staff_fanout.ops_watch_emails", lambda: {user.email.lower()}
    )
    yield user
    db.rollback()
    db.delete(db.get(AdminUser, user.id))
    db.commit()


def _order(db, merchant_ctx, driver, *, quebec: bool) -> Order:
    drop = (
        {"formatted": "1000 Rue Sherbrooke O, Montréal, QC", "postal": "H3A 3G4", "province": "QC"}
        if quebec
        else {"formatted": "9 Main St, Toronto, ON", "postal": "M4E 2V5", "province": "ON"}
    )
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state="IN_TRANSIT",
        merchant_id=merchant_ctx.merchant.id,
        amount_cents=2500,
        currency="cad",
        pickup={"formatted": "1 Front St, Toronto", "postal": "M5J 1E6"},
        dropoff=drop,
        scheduled_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
        assigned_driver_id=driver.id,
        compliance_metadata={"consignee": {"email": f"rcv-{uuid4().hex[:8]}@example.test", "name": "Ana"}},
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def _payload(order: Order, driver) -> dict:
    return {
        **center._SAMPLE_PAYLOAD,
        "order_id": order.id,
        "merchant_id": order.merchant_id,
        "driver_id": driver.id,
        "customer_id": f"cust-{order.id[:8]}",
        "email": f"cust-{order.id[:8]}@example.test",
        "receiver_email": order.compliance_metadata["consignee"]["email"],
        "merchant_email": f"m-{order.id[:8]}@example.test",
        "order_number": order.order_number,
        "tracking_number": order.tracking_number,
    }


def _fire(event: str, payload: dict, corr: str) -> None:
    handle_domain_event(
        {"event_type": event, "aggregate_type": "order", "aggregate_id": payload["order_id"],
         "correlation_id": corr, "payload": dict(payload)}
    )


def _rows_for(db, order: Order) -> list[NotificationRecord]:
    db.expire_all()
    rows = db.query(NotificationRecord).filter(NotificationRecord.created_at.isnot(None)).all()
    oid = order.id
    return [
        r for r in rows
        if oid in (r.idempotency_key or "") or r.recipient_id == oid or oid in json.dumps(r.context or {}, default=str)
    ]


def _persona(r: NotificationRecord) -> str:
    return "receiver" if r.recipient_type == "consignee" else r.recipient_type


def _deliver_all(rows: list[NotificationRecord]) -> None:
    from porterchain_api.notification_engine.delivery_service import DeliveryService

    for r in rows:
        if r.channel != "email" or r.status not in ("queued", "failed"):
            continue
        DeliveryService().deliver(
            {"notification_id": r.id, "channel": "email", "template": r.template_key,
             "recipient_type": r.recipient_type, "recipient_id": r.recipient_id,
             "recipient": r.recipient_address or "", "context": {**(r.context or {}), "notification_id": r.id}}
        )


@pytest.mark.parametrize("quebec", [False, True], ids=["toronto-en", "montreal-fr"])
def test_every_matrix_event_end_to_end(db, merchant_ctx, driver, staff, captured, quebec) -> None:  # noqa: ARG001
    mx = center.matrix(db)
    report: list[dict] = []
    problems: list[str] = []
    for row in mx["rows"]:
        event = row["event"]
        order = _order(db, merchant_ctx, driver, quebec=quebec)
        payload = _payload(order, driver)
        if event.startswith("cx."):
            kind = event[3:]
            if kind not in CX_TRIGGERS:
                continue
            trigger, extra = CX_TRIGGERS[kind]
            payload.update(extra)
            if kind == "delivered":
                order.state = "DELIVERED"
                db.commit()
        else:
            trigger = event
        corr = str(uuid4())
        _fire(trigger, payload, corr)
        first = _rows_for(db, order)
        _fire(trigger, payload, corr)  # same event again: must be a no-op
        second = _rows_for(db, order)

        got = {(_persona(r), r.channel) for r in first}
        for persona, cell in row["cells"].items():
            if not cell["on"]:
                continue
            for ch in cell["channels"]:
                if ch not in ("email", "in_app"):
                    continue
                if (persona, ch) not in got:
                    problems.append(f"{event}: {persona}/{ch} missing")
        if len(second) != len(first):
            problems.append(f"{event}: refire created {len(second) - len(first)} extra rows")
        dupes = [k for k, n in Counter((r.recipient_type, r.recipient_address or r.recipient_id, r.channel, r.template_key) for r in first).items() if n > 1]
        if dupes:
            problems.append(f"{event}: duplicates {dupes}")
        # language: receiver/customer emails follow the dropoff; business copies stay English
        for r in first:
            if r.channel != "email":
                continue
            lang = (r.context or {}).get("lang") or "en"
            if _persona(r) in ("receiver", "customer") and quebec and r.template_key.startswith("cx_"):
                if not lang.startswith("fr") or not any(h in (r.title + r.body) for h in FRENCH_HINTS):
                    problems.append(f"{event}: {r.template_key} to {_persona(r)} not French")
            if _persona(r) in ("merchant", "admin", "driver") and lang.startswith("fr"):
                problems.append(f"{event}: business copy {r.template_key} in French")
        # bell: the item is in the persona's inbox with a deep link
        for r in first:
            if r.channel != "in_app":
                continue
            box = get_notification_engine().inbox_payload(db, user_role=r.recipient_type, user_id=r.recipient_id, limit=200)
            item = next((i for i in box["items"] if i["id"] == r.id), None)
            if item is None:
                problems.append(f"{event}: bell item missing for {r.recipient_type}")
            elif item["href"] == FALLBACK.get(_persona(r)) and r.recipient_type != "admin":
                problems.append(f"{event}: {r.recipient_type} bell item has no deep link")
        # deliver twice: one provider call per email row
        before = len(captured)
        _deliver_all(first)
        _deliver_all(_rows_for(db, order))
        emails = [r for r in first if r.channel == "email" and r.recipient_address]
        delivered = len(captured) - before
        ids = Counter(c["id"] for c in captured[before:])
        if any(n > 1 for n in ids.values()):
            problems.append(f"{event}: an email was sent twice")
        order.assigned_driver_id = None  # keep the driver's run to one stop per event
        db.commit()
        report.append(
            {"event": event, "trigger": trigger, "rows": len(first), "emails_sent": delivered,
             "email_rows": len(emails), "bell": sum(1 for r in first if r.channel == "in_app"),
             "personas": sorted({f"{p}/{c}" for p, c in got})}
        )
    out = os.environ.get("NOTIF_E2E_REPORT")
    if out:
        with open(f"{out}-{'fr' if quebec else 'en'}.json", "w") as fh:
            json.dump({"report": report, "problems": problems}, fh, indent=1)
    assert not problems, "\n".join(problems)
    assert len(report) >= 30
