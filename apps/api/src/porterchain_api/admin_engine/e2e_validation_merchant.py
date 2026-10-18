"""E2E validation — phase 3 merchant bulk scenario."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.e2e_validation_catalog import E2E_MARKER
from porterchain_api.admin_engine.e2e_validation_helpers import PICKUP, DROPOFF, StepResult
from porterchain_api.booking_engine.order_transitions import transition_order_state, transition_to_dispatch_ready
from porterchain_api.config import Settings
from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_engine.bulk_service import MerchantBulkService
from porterchain_api.merchant_engine.booking_service import MerchantBookingService
from porterchain_api.booking_models import Order
from porterchain_api.schemas_merchant import AddressInput as MerchantAddressInput
from porterchain_api.schemas_merchant import MerchantBookDeliveryRequest


class E2EValidationMerchantMixin:
    def phase_3_merchant(self, db: Session, settings: Settings, *, order_count: int) -> dict[str, Any]:
        steps: list[StepResult] = []
        merchant_ctx = self._resolve_merchant_context(db)
        if not merchant_ctx:
            return {
                "phase": 3,
                "name": "Merchant Scenario",
                "overall": "BLOCKER",
                "steps": [
                    StepResult(
                        step="Merchant Login",
                        status="BLOCKER",
                        layer="merchant_engine",
                        root_cause="No active merchant user in database",
                        recommended_fix="Run pnpm db:seed or provision a merchant user",
                        priority="P0",
                    ).as_dict()
                ],
            }

        def record(name: str, fn, *, layer: str = "merchant_engine") -> None:
            t0 = time.monotonic()
            try:
                status = fn()
                steps.append(
                    StepResult(
                        step=name,
                        status=status if isinstance(status, str) else "PASS",
                        layer=layer,
                        duration_ms=(time.monotonic() - t0) * 1000,
                        details=status if isinstance(status, dict) else {},
                    )
                )
            except Exception as exc:  # noqa: BLE001
                steps.append(
                    StepResult(
                        step=name,
                        status="FAIL",
                        layer=layer,
                        root_cause=str(exc)[:300],
                        priority="P1",
                        duration_ms=(time.monotonic() - t0) * 1000,
                    )
                )

        record("Merchant Login", lambda: "PASS")
        order_ids: list[str] = []

        def do_csv():
            bulk = MerchantBulkService()
            rows = []
            base_time = datetime.now(UTC) + timedelta(hours=3)
            for i in range(order_count):
                rows.append(
                    f"{PICKUP.formatted},{DROPOFF.formatted},{(base_time + timedelta(minutes=i)).isoformat()},e2e-bulk-{i}"
                )
            csv_content = "pickup,dropoff,scheduled_at,internal_reference\n" + "\n".join(rows)
            job = bulk.upload_csv(
                db,
                merchant_ctx,
                filename="e2e-validation.csv",
                content=csv_content,
            )
            return {"job_id": job.id, "valid_rows": job.valid_rows, "total_rows": job.total_rows}

        def do_contract_pricing():
            from porterchain_api.merchant_engine.billing_service import MerchantBillingService

            if not merchant_ctx.merchant:
                return "WARNING"
            payload = MerchantBillingService().contract_pricing(db, merchant_ctx)
            if not isinstance(payload, dict):
                return "FAIL"
            # Pricing model on merchant is what Quote≡Book uses; contract optional.
            model = getattr(merchant_ctx.merchant, "pricing_model", None) or "distance"
            return {
                "pricing_model": model,
                "has_contract": bool(payload.get("has_contract")),
                "has_pricing_config": isinstance(payload.get("pricing_config"), dict),
            }

        record("CSV Upload", do_csv)


        def do_orders():
            booking = MerchantBookingService()
            base_time = datetime.now(UTC) + timedelta(hours=3)
            created = 0
            for i in range(order_count):
                body = MerchantBookDeliveryRequest(
                    pickup=MerchantAddressInput(**PICKUP.model_dump()),
                    dropoff=MerchantAddressInput(**DROPOFF.model_dump()),
                    scheduled_at=base_time + timedelta(minutes=i),
                    internal_reference=f"{E2E_MARKER}-bulk-{i}",
                )
                try:
                    order = booking.create_shipment(
                        db, settings, merchant_ctx, body, sandbox=True
                    )
                    order.internal_reference = E2E_MARKER
                    order_ids.append(order.id)
                    created += 1
                except Exception as exc:
                    db.rollback()
                    if created == 0 and i == 0:
                        raise RuntimeError(f"merchant_book_failed: {exc}") from exc
            db.commit()
            if created < order_count:
                return "WARNING" if created > 0 else "FAIL"
            return {"orders_created": created}

        record("100 Orders" if order_count == 100 else f"{order_count} Orders", do_orders)
        record("Contract Pricing", do_contract_pricing, layer="pricing_engine")
        record("Operations Queue", lambda: self._verify_ops_queue(db, order_ids[0]) if order_ids else "FAIL")

        if order_ids:
            o = db.get(Order, order_ids[0])
            transition_to_dispatch_ready(db, o, payload={"e2e_merchant": True})
            for state, ev in [
                (OrderState.DRIVER_ASSIGNED, "order.driver_assigned"),
                (OrderState.DRIVER_ACCEPTED, "order.driver_accepted"),
                (OrderState.DRIVER_EN_ROUTE, "order.en_route"),
                (OrderState.AT_PICKUP, "order.arrived_pickup"),
                (OrderState.PICKED_UP, "order.pickup_completed"),
                (OrderState.IN_TRANSIT, "order.in_transit"),
                (OrderState.AT_DESTINATION, "order.near_delivery"),
                (OrderState.DELIVERED, "order.delivered"),
            ]:
                transition_order_state(db, o, state, event_type=ev, payload={"e2e": True})
                db.refresh(o)

        def do_dispatch_assert():
            if not order_ids:
                return "FAIL"
            o = db.get(Order, order_ids[0])
            if not o:
                return "FAIL"
            # After transitions above, order must be past assignment into active dispatch.
            ok_states = {
                OrderState.DRIVER_ASSIGNED.value,
                OrderState.DRIVER_ACCEPTED.value,
                OrderState.DRIVER_EN_ROUTE.value,
                OrderState.AT_PICKUP.value,
                OrderState.PICKED_UP.value,
                OrderState.IN_TRANSIT.value,
                OrderState.AT_DESTINATION.value,
                OrderState.DELIVERED.value,
                OrderState.POD_COMPLETED.value,
                OrderState.INVOICED.value,
            }
            if o.state not in ok_states:
                return "FAIL"
            return {"order_id": o.id, "state": o.state}

        def do_delivery_assert():
            if not order_ids:
                return "FAIL"
            o = db.get(Order, order_ids[0])
            if not o:
                return "FAIL"
            if o.state not in (
                OrderState.DELIVERED.value,
                OrderState.POD_COMPLETED.value,
                OrderState.INVOICED.value,
            ):
                return "FAIL"
            return {"order_id": o.id, "state": o.state}

        record("Dispatch", do_dispatch_assert)
        record("Delivery", do_delivery_assert)
        # The billing run invoices *every* uninvoiced delivered order of the merchant it
        # picks (the first active one), so it must never run against live data.
        live_env = str(getattr(settings, "app_env", "") or "").lower() == "production"
        billing_skip = {"skipped": "production: billing run would invoice a real merchant"}

        def do_billing_run():
            if not order_ids:
                return "FAIL"
            if live_env:
                return billing_skip
            from porterchain_api.admin_engine.merchant_ar_service import MerchantArService

            admin_ctx = self._resolve_admin_context(db)
            if not admin_ctx:
                return "WARNING"
            start = datetime.now(UTC) - timedelta(days=1)
            end = datetime.now(UTC) + timedelta(days=1)
            result = MerchantArService().generate(
                db,
                admin_ctx,
                merchant_id=merchant_ctx.merchant.id,
                period_start=start,
                period_end=end,
            )
            created = int(result.get("created_count") or 0)
            has_inv = _invoice_for_order(order_ids[0]) is not None
            if created > 0 or has_inv:
                return {"created_count": created, "invoiced": has_inv}
            return "FAIL"

        def _invoice_for_order(order_id: str):
            from porterchain_api.platform.invoice_lines import invoice_for_order

            return invoice_for_order(db, order_id)

        def do_invoice_assert():
            from porterchain_api.booking_models import Order
            from porterchain_api.merchant_engine.billing_service import MerchantBillingService
            from porterchain_api.platform.invoice_lines import ensure_invoice_line, invoice_lines_for

            if not order_ids:
                return "FAIL"
            if live_env:
                return billing_skip
            order = db.query(Order).filter(Order.id == order_ids[0]).first()
            inv = _invoice_for_order(order_ids[0])
            if not inv or not order:
                return "FAIL"

            def fail(reason: str, **extra: Any):
                # Raise so the step records why (record() keeps str(exc) as root_cause).
                raise AssertionError(f"{reason}: {extra}" if extra else reason)

            cycle = (getattr(inv, "billing_kind", None) or "order") == "cycle"
            if not cycle:
                # Legacy 1:1 invoice: persist its single line if an older row lacks one.
                ensure_invoice_line(db, inv, order)
                db.flush()
            try:
                detail = MerchantBillingService().invoice_detail(db, merchant_ctx, inv.id)
            except Exception as exc:  # noqa: BLE001
                fail("invoice_detail_error", error=str(exc)[:120])
            if not detail.get("lines"):
                fail("no_lines")
            amount = int(inv.amount_cents or 0)
            tax = int(inv.tax_cents or 0)
            if int(detail.get("amount_cents") or 0) != amount:
                fail("detail_amount_vs_invoice", detail=detail.get("amount_cents"), invoice=amount)
            rows = invoice_lines_for(db, inv.id)
            if cycle:
                # Cycle (Interac) invoice: lines are pre-tax + their own tax, invoice is the
                # gross total of all lines (deliveries + waiting/failed-delivery fees).
                from porterchain_api.platform.merchant_billing import order_tax_split

                line_gross = sum(int(r.amount_cents or 0) + int(r.tax_cents or 0) for r in rows)
                line_tax = sum(int(r.tax_cents or 0) for r in rows)
                if line_gross != amount:
                    fail("lines_plus_tax_vs_invoice", lines=line_gross, invoice=amount)
                if line_tax != tax:
                    fail("line_tax_vs_invoice_tax", lines=line_tax, invoice=tax)
                mine = [
                    r for r in rows
                    if r.order_id == order.id and (r.description or "").startswith("Delivery")
                ]
                if len(mine) != 1:
                    fail("delivery_line_count", count=len(mine))
                split = order_tax_split(db, order)
                if (int(mine[0].amount_cents or 0), int(mine[0].tax_cents or 0)) != (split.pretax_cents, split.tax_cents):
                    fail(
                        "delivery_line_vs_tax_split",
                        line=(mine[0].amount_cents, mine[0].tax_cents),
                        expected=(split.pretax_cents, split.tax_cents),
                    )
            else:
                if amount != int(order.amount_cents or 0):
                    fail("invoice_vs_order", invoice=amount, order=order.amount_cents)
                if int(detail.get("lines_total_cents") or 0) != amount:
                    fail("lines_total_vs_invoice", lines=detail.get("lines_total_cents"), invoice=amount)
            channel = (detail["lines"][0] or {}).get("channel")
            if not channel:
                fail("no_channel")
            return {
                "invoice_id": inv.id,
                "billing_kind": "cycle" if cycle else "order",
                "amount_cents": amount,
                "tax_cents": tax,
                "channel": channel,
                "ar_ok": True,
            }

        def do_reports_channel():
            from porterchain_api.merchant_engine.reporting_metrics import spend_by_channel

            rows = spend_by_channel(db, merchant_ctx.merchant.id)
            attributed = sum(int(r.get("orders") or 0) for r in rows)
            if attributed <= 0 and order_ids:
                return "FAIL"
            return {
                "channels": rows,
                "orders": attributed,
                "spend_cents": sum(int(r.get("spend_cents") or 0) for r in rows),
            }

        def do_statement_ar():
            from porterchain_api.merchant_engine.billing_service import MerchantBillingService

            svc = MerchantBillingService()
            summary = svc.statement_summary(db, merchant_ctx)
            bal = svc.outstanding_balance(db, merchant_ctx)
            ar = svc._ar(db, merchant_ctx)
            # One balance: statement KPI ≡ outstanding_balance ≡ merchant_ar SSOT
            if int(summary.get("outstanding_balance_cents") or 0) != int(bal):
                return "FAIL"
            if int(bal) != int(ar.outstanding_cents):
                return "FAIL"
            if int(summary.get("outstanding_invoices_cents") or 0) != int(ar.invoiced_cents):
                return "FAIL"
            if int(summary.get("uninvoiced_orders_cents") or 0) != int(ar.uninvoiced_cents):
                return "FAIL"
            if int(summary.get("credit_notes_cents") or 0) != int(ar.credits_cents):
                return "FAIL"
            return {
                "outstanding_balance_cents": bal,
                "invoiced_cents": ar.invoiced_cents,
                "uninvoiced_cents": ar.uninvoiced_cents,
                "credits_cents": ar.credits_cents,
            }

        record("Billing Run", do_billing_run, layer="billing_engine")
        record("Invoice", do_invoice_assert, layer="finance_engine")
        record("Statement", do_statement_ar, layer="finance_engine")
        record("Reports", do_reports_channel, layer="merchant_engine.reporting_metrics")

        return self._phase_result(3, "Merchant Scenario", steps, extra={"order_ids": order_ids[:5], "order_count": len(order_ids)})
