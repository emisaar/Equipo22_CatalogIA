from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.crud.base import CRUDBase
from app.models.wishlist import Wishlist
from app.schemas.wishlist import WishlistCreate, WishlistCreate as WishlistUpdate


class CRUDWishlist(CRUDBase[Wishlist, WishlistCreate, WishlistUpdate]):
    def get_by_user(self, db: Session, *, user_id: UUID) -> List[Wishlist]:
        return (
            db.query(Wishlist)
            .options(joinedload(Wishlist.product))
            .filter(Wishlist.user_id == user_id)
            .all()
        )

    def count_by_user(self, db: Session, *, user_id: UUID) -> int:
        return db.query(func.count(Wishlist.id)).filter(Wishlist.user_id == user_id).scalar()

    def check_exists(self, db: Session, *, user_id: UUID, product_id: UUID) -> Optional[Wishlist]:
        return (
            db.query(Wishlist)
            .filter(Wishlist.user_id == user_id, Wishlist.product_id == product_id)
            .first()
        )

    def create_user_wishlist(
        self, db: Session, *, user_id: UUID, product_id: UUID
    ) -> Wishlist:
        existing = self.check_exists(db, user_id=user_id, product_id=product_id)
        if existing:
            return existing
        
        db_obj = Wishlist(user_id=user_id, product_id=product_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove_from_wishlist(
        self, db: Session, *, user_id: UUID, product_id: UUID
    ) -> bool:
        wishlist_item = self.check_exists(db, user_id=user_id, product_id=product_id)
        if wishlist_item:
            db.delete(wishlist_item)
            db.commit()
            return True
        return False


wishlist = CRUDWishlist(Wishlist)