"""Bulk CSV/Excel import per MODULE_BREAKDOWN.md."""

import csv
import hashlib
import io
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_engine._core import emit_event
from porterchain_api.config import Settings
from porterchain_api.domain.merchant_states import BulkImportStatus
from porterchain_api.merchant_engine import events as E
from porterchain_api.merchant_engine.booking_service import MerchantBookingService
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import BulkImportJob
from porterchain_api.schemas import AddressInput
from porterchain_api.schemas_merchant import MerchantBookDeliveryRequest
from datetime import UTC, datetime


REQUIRED_COLUMNS = {"pickup", "dropoff", "scheduled_at"}


class MerchantBulkService:
    def __init__(self) -> None:
        self._booking = MerchantBookingService()

    def upload_csv(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        filename: str,
        content: str,
    ) -> BulkImportJob:
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        preview: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        seen_hashes: set[str] = set()
        duplicates = 0

        for i, row in enumerate(rows, start=2):
            missing = REQUIRED_COLUMNS - set(row.keys())
            if missing:
                errors.append({"row": i, "error": f"missing_columns:{','.join(missing)}"})
                continue
            row_hash = hashlib.sha256(f"{row['pickup']}|{row['dropoff']}|{row['scheduled_at']}".encode()).hexdigest()
            if row_hash in seen_hashes:
                duplicates += 1
                errors.append({"row": i, "error": "duplicate"})
                continue
            seen_hashes.add(row_hash)
            preview.append({"row": i, **row})

        job = BulkImportJob(
            merchant_id=ctx.merchant.id,
            status=BulkImportStatus.PREVIEW.value,
            filename=filename,
            total_rows=len(rows),
            valid_rows=len(preview),
            error_rows=len(errors) - duplicates,
            duplicate_rows=duplicates,
            preview=preview[:50],
            errors=errors[:100],
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    def confirm_bulk(
        self,
        db: Session,
        settings: Settings,
        ctx: MerchantContext,
        job_id: str,
    ) -> BulkImportJob:
        job = db.query(BulkImportJob).filter(BulkImportJob.id == job_id, BulkImportJob.merchant_id == ctx.merchant.id).first()
        if not job:
            raise LookupError("bulk_job_not_found")
        if job.status == BulkImportStatus.CONFIRMED.value:
            return job

        order_ids: list[str] = []
        for row in job.preview:
            try:
                scheduled = datetime.fromisoformat(row["scheduled_at"].replace("Z", "+00:00"))
            except ValueError:
                scheduled = datetime.now(UTC)
            body = MerchantBookDeliveryRequest(
                pickup=AddressInput(formatted=row["pickup"]),
                dropoff=AddressInput(formatted=row["dropoff"]),
                scheduled_at=scheduled,
                internal_reference=row.get("internal_reference"),
                purchase_order_number=row.get("purchase_order_number"),
                cost_centre=row.get("cost_centre"),
            )
            order = self._booking.create_shipment(db, settings, ctx, body)
            order_ids.append(order.id)

        job.status = BulkImportStatus.CONFIRMED.value
        job.order_ids = order_ids
        db.commit()

        emit_event(
            db,
            event_type=E.MERCHANT_BULK_BOOKING_CREATED,
            aggregate_type="bulk_import",
            aggregate_id=job.id,
            correlation_id=ctx.merchant.id,
            actor_type="merchant",
            actor_id=ctx.user.id,
            payload={"order_count": len(order_ids)},
        )
        db.commit()
        db.refresh(job)
        return job
