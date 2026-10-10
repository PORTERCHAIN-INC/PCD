"""HTTP smoke for the round-2 Finance routes (Cash, Stripe, margin, tax, exports, Driver Pay)."""

from __future__ import annotations

from tests.test_cycle_invoice_no_order import _cycle_invoice, admin_client  # noqa: F401


def test_finance_round2_routes(admin_client, db) -> None:  # noqa: F811
    m, inv = _cycle_invoice(db)
    cash = admin_client.get("/v1/admin/finance/cash")
    assert cash.status_code == 200, cash.text
    body = cash.json()
    assert any(r["merchant_id"] == m.id for r in body["merchants"])
    assert set(body["bucket_order"]) == set(body["buckets"])
    for path in (
        "/v1/admin/finance/stripe",
        "/v1/admin/finance/margin?days=30",
        "/v1/admin/finance/tax-report",
        "/v1/admin/finance/reminders",
        "/v1/admin/finance/payout-runs",
    ):
        r = admin_client.get(path)
        assert r.status_code == 200, (path, r.text)
    for kind in ("hst", "quickbooks", "xero"):
        r = admin_client.get(f"/v1/admin/finance/exports/{kind}.csv")
        assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert admin_client.get("/v1/admin/finance/exports/nope.csv").status_code == 404
    assert admin_client.get("/v1/admin/finance/tax-report?start=bad").status_code == 400
    q = admin_client.post("/v1/admin/finance/reminders/queue")
    assert q.status_code == 200
    assert admin_client.post("/v1/admin/finance/payout-runs/none/explode").status_code == 404
