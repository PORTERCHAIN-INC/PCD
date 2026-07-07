"""Quote persistence — repository pattern."""

from sqlalchemy.orm import Session

from porterchain_api.models import Quote


class QuoteRepository:
    def get_by_id(self, db: Session, quote_id: str) -> Quote | None:
        return db.query(Quote).filter(Quote.id == quote_id).first()
