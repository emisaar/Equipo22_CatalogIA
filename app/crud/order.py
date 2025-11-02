from typing import List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.crud.base import CRUDBase
from app.models.order import Order
from app.schemas.order import OrderCreate, OrderUpdate


class CRUDOrder(CRUDBase[Order, OrderCreate, OrderUpdate]):
    def get_by_user(
        self, db: Session, *, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Order]:
        return (
            db.query(Order)
            .filter(Order.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_by_user(self, db: Session, *, user_id: UUID) -> int:
        return db.query(func.count(Order.id)).filter(Order.user_id == user_id).scalar()

    def get_by_status(
        self, db: Session, *, status: str, skip: int = 0, limit: int = 100
    ) -> List[Order]:
        return (
            db.query(Order)
            .filter(Order.status == status)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_status(self, db: Session, *, order_id: UUID, status: str) -> Order:
        order = db.query(Order).filter(Order.id == order_id).first()
        if order:
            order.status = status
            db.add(order)
            db.commit()
            db.refresh(order)
        return order

    def create_with_total(
        self, db: Session, *, obj_in: OrderCreate, user_id: UUID, unit_price: float
    ) -> Order:
        total_amount = obj_in.quantity * unit_price
        db_obj = Order(
            user_id=user_id,
            product_id=obj_in.product_id,
            quantity=obj_in.quantity,
            total_amount=total_amount,
            status="pending"
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


order = CRUDOrder(Order)