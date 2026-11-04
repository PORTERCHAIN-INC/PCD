"""Client labels are kept exactly as printed (RB-1), matched normalized; EDI control numbers
are unique and increment per trading partner."""
from __future__ import annotations

import uuid

from porterchain_api.batch_engine import service as svc
from porterchain_api.batch_engine.models import BatchParcel
from porterchain_api.ops_rules import edi_service

CSV = "address,client_label,lat,lng\n\"100 Queen St W, Toronto\",RB-1,43.6525,-79.3832\n\"1 Yonge St, Toronto\",#1001,43.6426,-79.3753\n"


def _batch(db):
    return svc.create_batch(db, str(uuid.uuid4()), CSV, pickup_point={"lat": 43.65, "lng": -79.38})


def test_client_label_preserved_and_still_matches(db):
    b = _batch(db)
    labels = sorted(lab for p in db.query(BatchParcel).filter(BatchParcel.batch_id == b.id) for lab in p.client_labels)
    assert labels == ["#1001", "RB-1"]
    assert svc.find_parcel(db, b.id, "rb1") is not None
    assert svc.find_parcel(db, b.id, "1001") is not None


def _isa13(text: str) -> str:
    return text.split("~")[0].split("*")[13]


def test_edi_control_numbers_unique_per_partner(db):
    b = _batch(db)
    p1 = f"P{uuid.uuid4().hex[:8]}".upper()
    p2 = f"Q{uuid.uuid4().hex[:8]}".upper()
    a = _isa13(edi_service.export_batch(db, b.id, "856", receiver=p1).body.decode())
    c = _isa13(edi_service.export_batch(db, b.id, "214", receiver=p1).body.decode())
    other = _isa13(edi_service.export_batch(db, b.id, "856", receiver=p2).body.decode())
    assert (a, c) == ("000000001", "000000002")
    assert other == "000000001"
    text = edi_service.export_batch(db, b.id, "214", receiver=p1).body.decode()
    assert _isa13(text) == "000000003"
    assert "GE*1*3~" in text and "IEA*1*000000003" in text
