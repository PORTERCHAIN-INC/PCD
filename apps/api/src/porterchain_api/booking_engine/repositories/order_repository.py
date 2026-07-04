"""Order persistence — repository pattern."""

from sqlalchemy.orm import Session

from porterchain_api.models import Order


class OrderRepository:
    def get_by_id(self, db: Session, order_id: str) -> Order | None:
        return db.query(Order).filter(Order.id == order_id).first()

    def get_by_quote_id(self, db: Session, quote_id: str) -> Order | None:
        return db.query(Order).filter(Order.quote_id == quote_id).first()

    def get_by_tracking(self, db: Session, tracking_number: str) -> Order | None:
        return db.query(Order).filter(Order.tracking_number == tracking_number).first()
