"""Driver finance — earnings, statements, payouts (Finance Engine, masterrule §11).

All driver earnings aggregation lives here. Driver portal and mobile apps
must never compute totals locally — they consume this service only.
"""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime, time, timedelta
from typing import Any, Literal

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.driver_models import DriverBonus, DriverWalletTransaction
from porterchain_api.booking_models import Order
from porterchain_api.driver_engine.wallet_ledger import wallet_balance_cents

Period = Literal["today", "week", "month"]

COMPLETED_STATES = frozenset({"DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED"})

TX_DELIVERY = frozenset({"delivery"})
TX_ADJUSTMENT = frozenset({"adjustment", "correction", "credit"})
TX_INCENTIVE = frozenset({"incentive"})
TX_DEDUCTION = frozenset({"deduction", "fee", "tax"})

DEFAULT_TAX_RATE_PERCENT = 13.0  # fallback when SystemConfig finance row is missing
DEFAULT_PAYMENT_SCHEDULE = {
    "frequency": "weekly",
    "day_of_week": "friday",
    "cutoff_description": "Sunday 11:59 PM local",
    "deposit_delay_business_days": 2,
    "currency": "cad",
}


class DriverFinanceService:
    def driver_earnings_snapshot(self, db: Session, driver: Any) -> dict[str, Any]:
        today_start, week_start, month_start, now = self._period_bounds()
        txs = self._all_transactions(db, driver.id)

        return {
            "today_cents": self._net_earnings(txs, today_start, now),
            "week_cents": self._net_earnings(txs, week_start, now),
            "month_cents": self._net_earnings(txs, month_start, now),
            "completed_deliveries_today": self._completed_deliveries(db, driver.id, today_start, now),
            "completed_deliveries_week": self._completed_deliveries(db, driver.id, week_start, now),
            "completed_deliveries_month": self._completed_deliveries(db, driver.id, month_start, now),
            "wallet_balance_cents": wallet_balance_cents(
                db, driver.id, cached_cents=int(driver.wallet_balance_cents or 0)
            ),
            "bonuses": self._list_bonuses(db, driver.id),
            "adjustments": self._filter_transactions(txs, TX_ADJUSTMENT, limit=30),
            "incentives": self._filter_transactions(txs, TX_INCENTIVE, limit=30),
            "deductions": self._filter_deductions(txs, limit=30),
            "payout_history": self._payout_history(db, driver.id),
            "taxes": self._tax_summary(db, driver.id, txs, month_start, now),
            "payment_schedule": self._payment_schedule(driver),
            "last_updated": now.isoformat(),
        }

    def period_earnings_cents(self, db: Session, driver_id: str, period: Period) -> int:
        today_start, week_start, month_start, now = self._period_bounds()
        start = {"today": today_start, "week": week_start, "month": month_start}[period]
        txs = self._all_transactions(db, driver_id)
        return self._net_earnings(txs, start, now)

    def route_earnings_cents(self, db: Session, driver_id: str, route_id: str) -> int:
        """Sum credited delivery earnings for orders on the route (wallet truth)."""
        order_ids = self._order_ids_for_route(db, driver_id, route_id)
        if not order_ids:
            return 0
        rows = (
            db.query(DriverWalletTransaction)
            .filter(
                DriverWalletTransaction.driver_id == driver_id,
                DriverWalletTransaction.tx_type.in_(tuple(TX_DELIVERY)),
                DriverWalletTransaction.reference_id.in_(order_ids),
            )
            .all()
        )
        return sum(r.amount_cents for r in rows)

    def list_statements(self, db: Session, driver_id: str, *, months: int = 12) -> list[dict[str, Any]]:
        now = datetime.now(UTC)
        statements: list[dict[str, Any]] = []
        year, month = now.year, now.month
        for _ in range(months):
            start = datetime(year, month, 1, tzinfo=UTC)
            if month == 12:
                end = datetime(year + 1, 1, 1, tzinfo=UTC)
            else:
                end = datetime(year, month + 1, 1, tzinfo=UTC)
            stmt_id = f"{year:04d}-{month:02d}"
            txs = self._transactions_between(db, driver_id, start, end)
            gross = sum(t.amount_cents for t in txs if t.amount_cents > 0)
            deductions = abs(sum(t.amount_cents for t in txs if t.amount_cents < 0))
            statements.append(
                {
                    "id": stmt_id,
                    "period_label": start.strftime("%B %Y"),
                    "period_start": start.date().isoformat(),
                    "period_end": (end - timedelta(days=1)).date().isoformat(),
                    "gross_cents": gross,
                    "deductions_cents": deductions,
                    "net_cents": gross - deductions,
                    "deliveries": self._completed_deliveries(db, driver_id, start, end),
                }
            )
            month -= 1
            if month == 0:
                month = 12
                year -= 1
        return statements

    def statement_detail(self, db: Session, driver_id: str, statement_id: str) -> dict[str, Any]:
        start, end = self._parse_statement_period(statement_id)
        txs = self._transactions_between(db, driver_id, start, end)
        return {
            "id": statement_id,
            "period_start": start.date().isoformat(),
            "period_end": (end - timedelta(days=1)).date().isoformat(),
            "gross_cents": sum(t.amount_cents for t in txs if t.amount_cents > 0),
            "deductions_cents": abs(sum(t.amount_cents for t in txs if t.amount_cents < 0)),
            "net_cents": sum(t.amount_cents for t in txs),
            "deliveries": self._completed_deliveries(db, driver_id, start, end),
            "line_items": [self._serialize_tx(t) for t in txs],
            "payouts": [
                p
                for p in self._payout_history(db, driver_id)
                if p.get("created_at")
                and start <= datetime.fromisoformat(p["created_at"].replace("Z", "+00:00")) < end
            ],
        }

    def statement_csv(self, db: Session, driver_id: str, statement_id: str) -> tuple[bytes, str]:
        detail = self.statement_detail(db, driver_id, statement_id)
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["Porterchain Driver Earnings Statement"])
        from porterchain_api.admin_engine.platform_settings import platform_company_name

        writer.writerow(["Company", platform_company_name(db)])
        writer.writerow(["Statement ID", statement_id])
        writer.writerow(["Period", f"{detail['period_start']} to {detail['period_end']}"])
        writer.writerow(["Gross", detail["gross_cents"] / 100])
        writer.writerow(["Deductions", detail["deductions_cents"] / 100])
        writer.writerow(["Net", detail["net_cents"] / 100])
        writer.writerow(["Deliveries", detail["deliveries"]])
        writer.writerow([])
        writer.writerow(["Date", "Type", "Description", "Amount", "Reference"])
        for row in detail["line_items"]:
            writer.writerow(
                [
                    row["created_at"],
                    row["type"],
                    row["description"],
                    row["amount_cents"] / 100,
                    row.get("reference_id") or "",
                ]
            )
        filename = f"porterchain-driver-statement-{statement_id}.csv"
        return buf.getvalue().encode("utf-8"), filename

    def _period_bounds(self) -> tuple[datetime, datetime, datetime, datetime]:
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)
        month_start = datetime(now.year, now.month, 1, tzinfo=UTC)
        return today_start, week_start, month_start, now

    def _all_transactions(self, db: Session, driver_id: str) -> list[DriverWalletTransaction]:
        return (
            db.query(DriverWalletTransaction)
            .filter(DriverWalletTransaction.driver_id == driver_id)
            .order_by(DriverWalletTransaction.created_at.desc())
            .all()
        )

    def _transactions_between(
        self, db: Session, driver_id: str, start: datetime, end: datetime
    ) -> list[DriverWalletTransaction]:
        return (
            db.query(DriverWalletTransaction)
            .filter(
                DriverWalletTransaction.driver_id == driver_id,
                DriverWalletTransaction.created_at >= start,
                DriverWalletTransaction.created_at < end,
            )
            .order_by(DriverWalletTransaction.created_at.asc())
            .all()
        )

    def _net_earnings(self, txs: list[DriverWalletTransaction], start: datetime, end: datetime) -> int:
        total = 0
        for t in txs:
            if not t.created_at:
                continue
            created = t.created_at if t.created_at.tzinfo else t.created_at.replace(tzinfo=UTC)
            if start <= created <= end:
                total += t.amount_cents
        return total

    def _completed_deliveries(
        self, db: Session, driver_id: str, start: datetime, end: datetime
    ) -> int:
        return (
            db.query(func.count(Order.id))
            .filter(
                Order.assigned_driver_id == driver_id,
                Order.state.in_(tuple(COMPLETED_STATES)),
                Order.updated_at >= start,
                Order.updated_at < end,
            )
            .scalar()
            or 0
        )

    def _list_bonuses(self, db: Session, driver_id: str) -> list[dict[str, Any]]:
        rows = (
            db.query(DriverBonus)
            .filter(DriverBonus.driver_id == driver_id)
            .order_by(DriverBonus.created_at.desc())
            .limit(50)
            .all()
        )
        return [
            {
                "id": b.id,
                "title": b.title,
                "amount_cents": b.amount_cents,
                "status": b.status,
                "criteria": b.criteria,
                "expires_at": b.expires_at.isoformat() if b.expires_at else None,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
            for b in rows
        ]

    def _filter_transactions(
        self, txs: list[DriverWalletTransaction], types: frozenset[str], *, limit: int
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for t in txs:
            if t.tx_type in types:
                out.append(self._serialize_tx(t))
            if len(out) >= limit:
                break
        return out

    def _filter_deductions(self, txs: list[DriverWalletTransaction], *, limit: int) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for t in txs:
            if t.tx_type in TX_DEDUCTION or t.amount_cents < 0:
                row = self._serialize_tx(t)
                row["amount_cents"] = abs(t.amount_cents)
                out.append(row)
            if len(out) >= limit:
                break
        return out

    def _payout_history(self, db: Session, driver_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        from porterchain_api.admin_engine.driver_service import AdminDriverService

        rows = AdminDriverService().list_payouts(db, driver_id, limit=limit)
        return [
            {
                "id": p.id,
                "amount_cents": p.amount_cents,
                "currency": p.currency,
                "status": p.status,
                "reference": p.reference,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in rows
        ]

    def create_payout(
        self,
        db: Session,
        driver_id: str,
        *,
        amount_cents: int | None = None,
        reference: str | None = None,
        currency: str = "cad",
    ) -> Any:
        """Create a pending payout and debit wallet (D-24)."""
        from porterchain_api.admin_engine.driver_service import AdminDriverService

        payout = AdminDriverService().create_payout(
            db,
            driver_id,
            amount_cents=amount_cents,
            reference=reference,
            currency=currency,
            commit=False,
        )
        from porterchain_api.admin_engine.driver_lookups import get_driver
        from porterchain_api.driver_engine.wallet_ledger import record_transaction, wallet_balance_cents

        driver = get_driver(db, driver_id)
        remaining = wallet_balance_cents(
            db, driver_id, cached_cents=int((driver.wallet_balance_cents if driver else 0) or 0)
        ) - payout.amount_cents
        record_transaction(
            db,
            driver_id=driver_id,
            tx_type="payout",
            amount_cents=-payout.amount_cents,
            balance_after_cents=remaining,
            reference_id=payout.id,
            description="Payout reserved",
            flush=False,
        )
        db.commit()
        db.refresh(payout)
        return payout

    def mark_payout_paid(
        self, db: Session, payout_id: str, *, driver_id: str | None = None
    ) -> Any:
        from porterchain_api.admin_engine.driver_service import AdminDriverService

        return AdminDriverService().mark_payout_paid(db, payout_id, driver_id=driver_id)

    @staticmethod
    def payout_payload(payout: Any) -> dict[str, Any]:
        return {
            "id": payout.id,
            "amount_cents": payout.amount_cents,
            "currency": payout.currency,
            "status": payout.status,
            "reference": payout.reference,
            "created_at": payout.created_at.isoformat() if payout.created_at else None,
        }

    def _tax_summary(
        self,
        db: Session,
        driver_id: str,
        txs: list[DriverWalletTransaction],
        month_start: datetime,
        now: datetime,
    ) -> dict[str, Any]:
        ytd_start = datetime(now.year, 1, 1, tzinfo=UTC)
        ytd_gross = sum(
            t.amount_cents
            for t in txs
            if t.created_at and t.created_at >= ytd_start and t.amount_cents > 0
        )
        withheld = sum(
            abs(t.amount_cents)
            for t in txs
            if t.created_at and t.created_at >= ytd_start and (t.tx_type in TX_DEDUCTION or t.amount_cents < 0)
        )
        month_gross = sum(
            t.amount_cents
            for t in txs
            if t.created_at and month_start <= t.created_at <= now and t.amount_cents > 0
        )
        from porterchain_api.admin_engine.platform_settings import default_tax_percent

        try:
            rate = float(default_tax_percent(db))
        except Exception:  # noqa: BLE001
            rate = DEFAULT_TAX_RATE_PERCENT
        return {
            "ytd_gross_cents": ytd_gross,
            "month_gross_cents": month_gross,
            "withheld_cents": withheld,
            "estimated_tax_cents": int(ytd_gross * rate / 100),
            "tax_rate_percent": rate,
            "note": "Tax estimates are for planning only. Consult a tax professional for filing.",
        }

    def _payment_schedule(self, driver: Any) -> dict[str, Any]:
        perf = driver.performance or {}
        custom = perf.get("payment_schedule")
        if isinstance(custom, dict):
            return {**DEFAULT_PAYMENT_SCHEDULE, **custom, "next_payout_date": self._next_payout_date().isoformat()}
        schedule = {**DEFAULT_PAYMENT_SCHEDULE}
        schedule["next_payout_date"] = self._next_payout_date().isoformat()
        return schedule

    def _next_payout_date(self) -> datetime.date:
        now = datetime.now(UTC).date()
        # Next Friday on or after today
        days_ahead = (4 - now.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        return now + timedelta(days=days_ahead)

    def _order_ids_for_route(self, db: Session, driver_id: str, route_id: str) -> list[str]:
        sod = datetime.combine(datetime.now(UTC).date(), time.min, tzinfo=UTC)
        if route_id.startswith("route-"):
            orders = (
                db.query(Order)
                .filter(Order.assigned_driver_id == driver_id, Order.created_at >= sod)
                .all()
            )
        else:
            orders = db.query(Order).filter(Order.assigned_driver_id == driver_id).all()
        return [o.id for o in orders]

    def _parse_statement_period(self, statement_id: str) -> tuple[datetime, datetime]:
        try:
            year_s, month_s = statement_id.split("-", 1)
            year, month = int(year_s), int(month_s)
        except (ValueError, AttributeError) as exc:
            raise LookupError("statement_not_found") from exc
        start = datetime(year, month, 1, tzinfo=UTC)
        if month == 12:
            end = datetime(year + 1, 1, 1, tzinfo=UTC)
        else:
            end = datetime(year, month + 1, 1, tzinfo=UTC)
        return start, end

    @staticmethod
    def _serialize_tx(t: DriverWalletTransaction) -> dict[str, Any]:
        return {
            "id": t.id,
            "type": t.tx_type,
            "amount_cents": t.amount_cents,
            "description": t.description or "",
            "reference_id": t.reference_id,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
