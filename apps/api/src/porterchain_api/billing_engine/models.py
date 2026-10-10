"""Billing ledger — durable record of settlement events."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from porterchain_api.db import Base


def _uuid() -> str:
    return str(uuid4())


class BillingLedgerEntry(Base):
    __tablename__ = "billing_ledger_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    kind: Mapped[str] = mapped_column(String(64), index=True)
    payment_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    invoice_id: Mapped[str | None] = mapped_column(ForeignKey("invoices.id"), nullable=True, index=True)
    order_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    merchant_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    amount_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="cad")
    status: Mapped[str] = mapped_column(String(32), default="recorded")
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"), index=True)
    order_id: Mapped[str | None] = mapped_column(ForeignKey("orders.id"), nullable=True, index=True)
    package_id: Mapped[str | None] = mapped_column(ForeignKey("packages.id"), nullable=True, index=True)
    description: Mapped[str] = mapped_column(String(255), default="Delivery")
    amount_cents: Mapped[int] = mapped_column(Integer, default=0)
    tax_cents: Mapped[int] = mapped_column(Integer, default=0)
    tax_province: Mapped[str | None] = mapped_column(String(2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CreditNote(Base):
    __tablename__ = "credit_notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    merchant_id: Mapped[str | None] = mapped_column(ForeignKey("merchants.id"), nullable=True, index=True)
    invoice_id: Mapped[str | None] = mapped_column(ForeignKey("invoices.id"), nullable=True, index=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InvoiceNumberSequence(Base):
    """Gap-free invoice counter per prefix+year. Row-locked inside the invoice transaction."""

    __tablename__ = "invoice_number_sequences"

    scope: Mapped[str] = mapped_column(String(32), primary_key=True)
    last_value: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class InteracTransfer(Base):
    """One inbound Interac e-Transfer notification, parsed from the billing inbox.

    Never applied automatically: an admin approves each proposed match. Stores only the
    fields needed to reconcile (PIPEDA data minimisation) — no raw message body.
    """

    __tablename__ = "interac_transfers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    message_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(32), default="notification")  # notification | autodeposit
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sender_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sender_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(8), default="cad")
    memo: Mapped[str | None] = mapped_column(String(512), nullable=True)
    interac_reference: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    auth_ok: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    auth_detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    invoice_id: Mapped[str | None] = mapped_column(ForeignKey("invoices.id"), nullable=True, index=True)
    merchant_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    match_method: Mapped[str | None] = mapped_column(String(32), nullable=True)  # reference | sender_amount
    match_note: Mapped[str | None] = mapped_column(String(255), nullable=True)  # exact | partial | over | unmatched
    status: Mapped[str] = mapped_column(String(32), default="needs_review", index=True)
    payment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FinanceReminderDraft(Base):
    """One queued payment reminder per merchant. Nothing is sent until an admin approves."""

    __tablename__ = "finance_reminder_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    merchant_id: Mapped[str] = mapped_column(String(36), index=True)
    invoice_ids: Mapped[list] = mapped_column(JSON, default=list)
    to_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    subject: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    amount_cents: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    oldest_days: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(16), default="draft", server_default="draft", index=True)
    decided_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StripePayout(Base):
    """A Stripe payout to the bank, reconciled against its balance transactions."""

    __tablename__ = "stripe_payouts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    stripe_payout_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32))
    amount_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(8), default="cad", server_default="cad")
    arrival_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    gross_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fee_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    refund_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dispute_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    other_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    matched_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unmatched_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    difference_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DriverPayoutRun(Base):
    """A pay period: draft (review) -> approved (payouts reserved) -> paid (bank file sent)."""

    __tablename__ = "driver_payout_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), default="draft", server_default="draft", index=True)
    lines: Mapped[list] = mapped_column(JSON, default=list)
    total_cents: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    driver_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
