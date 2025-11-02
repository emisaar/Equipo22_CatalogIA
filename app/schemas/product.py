from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


class ProductBase(BaseModel):
    ean: str = Field(..., min_length=13, max_length=13)
    title: str
    brand: Optional[str] = None
    product_description: Optional[str] = None
    category: str
    price: Decimal = Field(..., gt=0)
    color: Optional[str] = None
    discount: Decimal = Field(default=0, ge=0, le=100)
    rating: Decimal = Field(default=0, ge=0, le=5)
    stock: int = Field(..., ge=0)
    sponsored: bool = False
    image_url: Optional[str] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    ean: Optional[str] = Field(None, min_length=13, max_length=13)
    title: Optional[str] = None
    brand: Optional[str] = None
    product_description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=0)
    color: Optional[str] = None
    discount: Optional[Decimal] = Field(None, ge=0, le=100)
    rating: Optional[Decimal] = Field(None, ge=0, le=5)
    stock: Optional[int] = Field(None, ge=0)
    sponsored: Optional[bool] = None
    image_url: Optional[str] = None


class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductList(BaseModel):
    products: List[ProductResponse]
    total: int
    skip: int
    limit: int


class ProductWithScore(ProductResponse):
    """Producto con score de similitud semántica."""
    similarity_score: float = Field(..., ge=0, le=1, description="Score de similitud (0-1, mayor es más similar)")


class SemanticSearchResult(BaseModel):
    """Resultado de búsqueda semántica con scores de similitud."""
    products: List[ProductWithScore]
    total: int
    skip: int
    limit: int
    min_similarity: Optional[float] = Field(None, description="Umbral mínimo de similitud aplicado")