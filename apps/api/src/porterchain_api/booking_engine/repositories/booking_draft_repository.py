"""Booking draft persistence — repository pattern."""

from sqlalchemy.orm import Session

from porterchain_api.booking_draft_models import BookingDraft


class BookingDraftRepository:
    def get_by_id(self, db: Session, draft_id: str) -> BookingDraft | None:
        return db.query(BookingDraft).filter(BookingDraft.id == draft_id).first()

    def get_by_quote_id(self, db: Session, quote_id: str) -> BookingDraft | None:
        return db.query(BookingDraft).filter(BookingDraft.quote_id == quote_id).first()
