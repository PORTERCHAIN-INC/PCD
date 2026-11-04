"""COD / Stripe Connect columns are gone from the models and the migrated DB (dm4nocod0004)."""

from __future__ import annotations

from sqlalchemy import inspect

from porterchain_api.booking_models import Order
from porterchain_api.merchant_models import Merchant

DROPPED = {
    "orders": {"cod_amount_cents", "cod_status", "cod_stripe_session_id"},
    "merchants": {"cod_enabled", "stripe_connect_account_id"},
}


def test_models_do_not_map_cod_columns():
    assert not DROPPED["orders"] & set(Order.__table__.columns.keys())
    assert not DROPPED["merchants"] & set(Merchant.__table__.columns.keys())


def test_db_has_no_cod_columns(db):
    insp = inspect(db.get_bind())
    for table, cols in DROPPED.items():
        assert not cols & {c["name"] for c in insp.get_columns(table)}
