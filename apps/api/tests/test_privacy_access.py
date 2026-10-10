import uuid
from datetime import UTC, datetime

import pytest
from porterchain_api.booking_models import Order
from porterchain_api.platform.privacy_access import subject_access_export


def test_requires_identifier(db):
    with pytest.raises(ValueError):
        subject_access_export(db)
    with pytest.raises(ValueError):
        subject_access_export(db, email="nope")


def test_finds_recipient_by_email_and_phone(db):
    tag = uuid.uuid4().hex[:8]
    email = f"pipeda-{tag}@example.com"
    o = Order(
        order_number=f"PA{tag}", tracking_number=f"PT{tag}", amount_cents=1000,
        pickup={"formatted": "Milton"}, dropoff={"formatted": "Toronto", "contact_email": email, "contact_phone": "+1 (416) 555-0199"},
        scheduled_at=datetime.now(UTC),
    )
    db.add(o)
    db.flush()
    by_mail = subject_access_export(db, email=email.upper())
    assert [r["order_number"] for r in by_mail["orders"]] == [f"PA{tag}"]
    assert by_mail["orders"][0]["role"] == "recipient" and by_mail["orders"][0]["pickup"] is None
    by_phone = subject_access_export(db, phone="416-555-0199")
    assert f"PA{tag}" in [r["order_number"] for r in by_phone["orders"]]
