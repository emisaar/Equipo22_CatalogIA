from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
from .product import ProductResponse
from .user import UserResponse


class OrderBase(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)


class OrderCreate(OrderBase):
    pass


class OrderUpdate(BaseModel):
    quantity: Optional[int] = Field(None, gt=0)
    status: Optional[str] = None


class OrderStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(pending|completed|cancelled)$")


class OrderResponse(OrderBase):
    id: int
    user_id: int
    total_amount: Decimal
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderWithDetails(OrderResponse):
    product: ProductResponse
    user: UserResponse


class OrderList(BaseModel):
    orders: List[OrderResponse]
    total: int
    skip: int
    limit: int