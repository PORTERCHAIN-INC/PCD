"""Route view: box counts come from one grouped query (no lazy o.packages per stop = no N+1)."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from porterchain_api.dispatch_engine import driver_route as m


class _NoPackages(SimpleNamespace):
    @property
    def packages(self):  # touching this would lazy-load one SELECT per order
        raise AssertionError("N+1: view must not read order.packages")


def test_view_counts_boxes_without_lazy_loading():
    orders = [
        _NoPackages(id=f"o{i}", order_number=f"N{i}", pickup={"formatted": "P"}, dropoff={"formatted": "D"},
                    special_instructions=None, compliance_metadata={})
        for i in range(3)
    ]
    route = SimpleNamespace(id="r1", vehicle_class="van", stops=[
        {"key": f"o{i}:{k}", "order_id": f"o{i}", "kind": k} for i in range(3) for k in ("pickup", "drop")
    ])
    db = MagicMock()
    db.query.return_value.filter.return_value = orders
    svc = m.DriverRouteService() if hasattr(m, "DriverRouteService") else None
    cls = type(svc) if svc else next(v for v in vars(m).values() if isinstance(v, type) and hasattr(v, "view") and hasattr(v, "_package_counts"))
    inst = cls()
    groups = [{"keys": [s["key"]], "order_id": s["order_id"], "kind": s["kind"]} for s in route.stops]
    with patch.object(cls, "current_route", return_value=route), patch.object(cls, "_events", return_value={}), \
            patch.object(cls, "_package_counts", return_value={"o0": 2, "o1": 1, "o2": 4}) as pc, \
            patch.object(m, "group", return_value=groups):
        out = inst.view(db, "d1")["route"]
    pc.assert_called_once()
    assert [s["boxes"] for s in out["stops"]] == [2, 2, 1, 1, 4, 4]
    assert out["total"] == 6
