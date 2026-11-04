"""Quote PDF: Porterchain Inc. + GST/HST no. from the registration record, one HST line, CAD, EN/FR."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest

from porterchain_api.admin_models import TaxRegistration
from porterchain_api.platform import tax_registration as reg

NUMBER = "743402620 RT0001"
ITEMS = [{"code": "base", "label": "Base", "amount_cents": 1500}, {"code": "distance", "amount_cents": 300},
         {"code": "hst", "label": "HST", "amount_cents": 234}]


@pytest.fixture()
def registered(db):
    db.query(TaxRegistration).delete()
    db.commit()
    reg.clear_cache(db)
    reg.record_registration(db, gst_hst_number="743402620RT0001", legal_name="Porterchain Inc.",
                            effective_from=date(2026, 9, 28), actor_id=None)
    db.commit()
    yield db
    db.rollback()
    db.query(TaxRegistration).delete()
    db.commit()
    reg.clear_cache(db)


@pytest.fixture()
def client(db):
    from fastapi.testclient import TestClient

    from porterchain_api.db import get_db
    from porterchain_api.main import app

    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)


def _render(db, lang="en", items=ITEMS, at=datetime(2026, 10, 29, 12, tzinfo=UTC)):
    from porterchain_api.reporting.quote_pdf import render_quote_pdf

    return render_quote_pdf(
        db, quote_number="Q-TEST0001", issued_at=at, valid_until=at + timedelta(days=3),
        party_lines=["Acme Ltd", "ops@acme.test"], pickup="1 King St W, Toronto", dropoff="200 Bay St, Toronto",
        shipment_lines=["Parcels 1: small, weight 2 kg"], items=items, total_cents=2034, lang=lang,
    ).decode("latin-1")


def test_quote_pdf_en_has_identity_single_hst_and_cad(registered) -> None:
    pdf = _render(registered)
    assert pdf.startswith("%PDF")
    for s in ("Porterchain Inc.", f"GST/HST Reg. No.: {NUMBER}", "Q-TEST0001", "2026-10-29", "2026-11-01",
              "Acme Ltd", "1 King St W", "200 Bay St", "Parcels 1: small", "Currency: CAD",
              "$18.00 CAD", "$2.34 CAD", "$20.34 CAD"):
        assert s in pdf, s
    assert pdf.count("(HST)") == 1  # one HST row, never also among pre-tax lines
    assert "$15.00 CAD" in pdf and "$3.00 CAD" in pdf


def test_quote_pdf_fr(registered) -> None:
    pdf = _render(registered, lang="fr")
    assert "SOUMISSION" in pdf and "TPS/TVH" in pdf and NUMBER in pdf
    assert "20,34 $ CAD" in pdf and pdf.count("(TVH)") == 1


def test_quote_pdf_before_registration_has_no_number(registered) -> None:
    pdf = _render(registered, at=datetime(2026, 9, 1, tzinfo=UTC))
    assert NUMBER not in pdf and "Reg. No." not in pdf


def test_stored_quote_pdf_endpoint(client, registered) -> None:
    from porterchain_api.booking_models import Quote

    now = datetime.now(UTC)
    q = Quote(id=str(uuid.uuid4()), pickup={"formatted": "1 King St W"}, dropoff={"formatted": "200 Bay St"},
              vehicle_class="cargo_van", package_type="whole_vehicle", weight_kg=2, scheduled_at=now,
              amount_cents=2034, currency="cad", pricing_breakdown={"items": ITEMS, "tax_cents": 234},
              email="c@example.test", expires_at=now + timedelta(hours=72))
    registered.add(q)
    registered.commit()
    try:
        res = client.get(f"/v1/quotes/{q.id}/pdf")
        assert res.status_code == 200, res.text
        assert res.headers["content-type"] == "application/pdf"
        text = res.content.decode("latin-1")
        assert NUMBER in text and "$20.34 CAD" in text and text.count("(HST)") == 1
        assert "Vehicle: cargo van" in text
        assert client.get(f"/v1/quotes/{uuid.uuid4()}/pdf").status_code == 404
    finally:
        registered.delete(q)
        registered.commit()


def test_shipment_lines_parcels_and_vehicle() -> None:
    from porterchain_api.reporting.quote_pdf import LABELS, _shipment_lines

    rows = _shipment_lines(LABELS["en"], vehicle_class="cargo_van", package_type=None, dimensions=None,
                           weight_kg=2.722, parcels=[{"preset_label": "Other", "length_cm": 30.48, "width_cm": 25.4,
                                     "height_cm": 20.32, "weight_kg": 2.722}])
    assert rows == ["Parcels 1: Other, weight 2.7 kg, dimensions 30.5 x 25.4 x 20.3 cm"]
    assert _shipment_lines(LABELS["en"], vehicle_class="cargo_van", package_type="looseParcel", weight_kg=2,
                           dimensions=None, parcels=None) == ["Parcels: package looseParcel, weight 2 kg"]
    assert _shipment_lines(LABELS["en"], vehicle_class="cargo_van", package_type="whole_vehicle", weight_kg=None,
                           dimensions=None, parcels=None) == ["Vehicle: cargo van"]
