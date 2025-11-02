from typing import List
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from .product import ProductResponse


class WishlistBase(BaseModel):
    product_id: int


class WishlistCreate(WishlistBase):
    pass


class WishlistResponse(WishlistBase):
    id: int
    user_id: int
    added_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WishlistWithProduct(WishlistResponse):
    product: ProductResponse


class WishlistList(BaseModel):
    items: List[WishlistWithProduct]
    total: int