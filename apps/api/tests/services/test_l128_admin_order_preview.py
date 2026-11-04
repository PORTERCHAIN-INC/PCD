"""L128: admin New order prices parcels by size/weight before creating (no order saved)."""
from porterchain_api.admin_engine.order_builder_service import OrderBuilderService
from porterchain_api.booking_models import Order
from porterchain_api.schemas_admin import AdminCreateOrderRequest


def _body(mid, **kw):
    base = dict(
        merchant_id=mid, order_kind="single", vehicle_class="cargo_van", scheduled_at="2026-11-02T15:00:00Z",
        stops=[
            {"type": "pickup", "sequence": 0, "formatted": "100 King St W, Toronto", "lat": 43.6486, "lng": -79.3817, "postal": "M5X 1C7"},
            {"type": "dropoff", "sequence": 1, "formatted": "200 Bay St, Toronto", "lat": 43.6465, "lng": -79.3790, "postal": "M5J 2J5"},
        ],
    )
    base.update(kw)
    return AdminCreateOrderRequest(**base)


def test_preview_small_van_tier_and_custom(db, admin_ctx, merchant_ctx):
    mid = merchant_ctx.merchant.id
    svc = OrderBuilderService()
    n = db.query(Order).count()
    small = svc.create(db, None, admin_ctx, _body(mid, length_in=12, width_in=10, height_in=8, weight_lb=5), dry_run=True)
    assert small["subtotal_cents"] == 600 and small["custom_quote"] is None
    two_van = svc.create(db, None, admin_ctx, _body(mid, length_in=24, width_in=16, height_in=16, weight_lb=20, parcel_count=2), dry_run=True)
    assert two_van["subtotal_cents"] == 1800
    tier = svc.create(db, None, admin_ctx, _body(mid, length_in=24, width_in=16, height_in=16, weight_lb=110), dry_run=True)
    assert tier["subtotal_cents"] == 3900
    over = svc.create(db, None, admin_ctx, _body(mid, length_in=24, width_in=16, height_in=16, weight_lb=160), dry_run=True)
    assert over["custom_quote"] and "custom quote" in over["custom_quote"]
    hourly = svc.create(db, None, admin_ctx, _body(mid, booking_mode="vehicle", dedicated_hours=3, help_stops=1), dry_run=True)
    assert hourly["subtotal_cents"] == 21000
    assert db.query(Order).count() == n
