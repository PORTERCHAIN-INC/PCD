"""Driver payout runs: pick a period → review per driver → approve → mark paid.

* Draft: per driver, the net wallet movement in the period (deliveries + incentives +
  adjustments − deductions), capped at the current wallet balance so nobody is paid
  twice. Nothing moves yet.
* Approve: one pending payout per driver is reserved (the existing D-24 payout path:
  wallet debited, payout row created). Audited.
* Paid: after the bank transfer is sent, mark every payout in the run paid. Audited.
* The bank file is a CSV for bulk Interac e-Transfer / EFT upload.
"""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.billing_engine.models import DriverPayoutRun
from porterchain_api.driver_models import DriverWalletTransaction

EARNING_TYPES = frozenset({"delivery", "incentive", "adjustment", "correction", "credit", "bonus", "tip"})
DEDUCTION_TYPES = frozenset({"deduction", "fee", "tax"})


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def build_lines(db: Session, start: datetime, end: datetime) -> list[dict[str, Any]]:
    from porterchain_api.admin_models import Driver
    from porterchain_api.driver_engine.wallet_ledger import wallet_balance_cents

    net: dict[str, int] = defaultdict(int)
    deliveries: dict[str, int] = defaultdict(int)
    for t in (
        db.query(DriverWalletTransaction)
        .filter(DriverWalletTransaction.created_at >= start, DriverWalletTransaction.created_at < end)
        .all()
    ):
        if t.tx_type in EARNING_TYPES or t.tx_type in DEDUCTION_TYPES:
            net[t.driver_id] += int(t.amount_cents or 0)
        if t.tx_type == "delivery":
            deliveries[t.driver_id] += 1
    lines = []
    for driver_id, cents in net.items():
        if cents <= 0:
            continue
        driver = db.get(Driver, driver_id)
        if driver is None:
            continue
        balance = wallet_balance_cents(db, driver_id, cached_cents=driver.wallet_balance_cents)
        pay = min(cents, balance)
        if pay <= 0:
            continue
        lines.append(
            {
                "driver_id": driver_id,
                "name": driver.full_name,
                "email": driver.email,
                "deliveries": deliveries.get(driver_id, 0),
                "earned_cents": cents,
                "wallet_cents": balance,
                "amount_cents": pay,
                "payout_id": None,
            }
        )
    lines.sort(key=lambda r: -r["amount_cents"])
    return lines


def create_run(db: Session, ctx: Any, start: datetime, end: datetime) -> DriverPayoutRun:
    from porterchain_api.platform.admin_audit import log_admin_audit

    start, end = _aware(start), _aware(end)
    if end <= start:
        raise ValueError("period_invalid")
    open_run = db.query(DriverPayoutRun).filter(DriverPayoutRun.status == "draft").first()
    if open_run is not None:
        raise ValueError(f"draft_run_exists:{open_run.id}")
    lines = build_lines(db, start, end)
    if not lines:
        raise ValueError("nothing_to_pay")
    run = DriverPayoutRun(
        period_start=start,
        period_end=end,
        lines=lines,
        total_cents=sum(r["amount_cents"] for r in lines),
        driver_count=len(lines),
        created_by=ctx.user.id,
    )
    db.add(run)
    db.flush()
    log_admin_audit(db, ctx, action="finance.payout_run.create", resource_type="driver_payout_run",
                    resource_id=run.id, payload={"drivers": run.driver_count, "total_cents": run.total_cents})
    db.commit()
    return run


def _get(db: Session, run_id: str) -> DriverPayoutRun:
    run = db.query(DriverPayoutRun).filter(DriverPayoutRun.id == run_id).with_for_update().first()
    if run is None:
        raise LookupError("run_not_found")
    return run


def approve_run(db: Session, ctx: Any, run_id: str) -> DriverPayoutRun:
    from porterchain_api.billing_engine.driver_finance_service import DriverFinanceService
    from porterchain_api.platform.admin_audit import log_admin_audit

    run = _get(db, run_id)
    if run.status != "draft":
        raise ValueError(f"not_approvable:{run.status}")
    svc = DriverFinanceService()
    lines = []
    ref = f"RUN-{run.period_end.date().isoformat()}-{run.id[:6]}"
    for line in run.lines or []:
        row = dict(line)
        try:
            payout = svc.create_payout(db, row["driver_id"], amount_cents=int(row["amount_cents"]), reference=ref)
            row["payout_id"] = payout.id
        except (LookupError, ValueError) as exc:
            row["error"] = str(exc)
        lines.append(row)
    run = _get(db, run_id)
    run.lines = lines
    run.total_cents = sum(r["amount_cents"] for r in lines if r.get("payout_id"))
    run.status = "approved"
    run.approved_by = ctx.user.id
    run.approved_at = datetime.now(UTC)
    log_admin_audit(db, ctx, action="finance.payout_run.approve", resource_type="driver_payout_run",
                    resource_id=run.id, payload={"payouts": sum(1 for r in lines if r.get("payout_id")),
                                                 "total_cents": run.total_cents})
    db.commit()
    return run


def mark_run_paid(db: Session, ctx: Any, run_id: str) -> DriverPayoutRun:
    from porterchain_api.billing_engine.driver_finance_service import DriverFinanceService
    from porterchain_api.platform.admin_audit import log_admin_audit

    run = _get(db, run_id)
    if run.status != "approved":
        raise ValueError(f"not_payable:{run.status}")
    svc = DriverFinanceService()
    for line in run.lines or []:
        if line.get("payout_id"):
            svc.mark_payout_paid(db, line["payout_id"], driver_id=line["driver_id"])
    run = _get(db, run_id)
    run.status = "paid"
    run.paid_by = ctx.user.id
    run.paid_at = datetime.now(UTC)
    log_admin_audit(db, ctx, action="finance.payout_run.paid", resource_type="driver_payout_run",
                    resource_id=run.id, payload={"total_cents": run.total_cents})
    db.commit()
    return run


def discard_run(db: Session, ctx: Any, run_id: str) -> DriverPayoutRun:
    run = _get(db, run_id)
    if run.status != "draft":
        raise ValueError(f"not_discardable:{run.status}")
    run.status = "discarded"
    db.commit()
    return run


def run_payload(run: DriverPayoutRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "period_start": run.period_start,
        "period_end": run.period_end,
        "status": run.status,
        "total_cents": run.total_cents,
        "driver_count": run.driver_count,
        "lines": run.lines or [],
        "approved_at": run.approved_at,
        "paid_at": run.paid_at,
        "created_at": run.created_at,
    }


def list_runs(db: Session, *, limit: int = 20) -> list[dict[str, Any]]:
    rows = db.query(DriverPayoutRun).order_by(DriverPayoutRun.created_at.desc()).limit(limit).all()
    return [run_payload(r) for r in rows]


def bank_csv(db: Session, run_id: str) -> tuple[str, str]:
    """Bulk-payment CSV: one row per driver with a reserved payout."""
    run = db.get(DriverPayoutRun, run_id)
    if run is None:
        raise LookupError("run_not_found")
    if run.status not in ("approved", "paid"):
        raise ValueError("approve_first")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Recipient name", "Recipient email", "Amount (CAD)", "Reference", "Memo"])
    for line in run.lines or []:
        if not line.get("payout_id"):
            continue
        w.writerow(
            [line["name"], line["email"], f"{int(line['amount_cents']) / 100:.2f}", line["payout_id"][:12],
             f"PorterChain pay {run.period_start.date()} to {run.period_end.date()}"]
        )
    return buf.getvalue(), f"driver-payouts-{run.period_end.date()}.csv"
