from sqlalchemy import Column, String, Text, Integer, DateTime, Boolean, func, DECIMAL
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ean = Column(String(13), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    product_description = Column(Text)
    category = Column(String(100), nullable=False, index=True)
    subcategory = Column(String(100), index=True)
    price = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(3), default="MXN")
    discount = Column(DECIMAL(5, 2), default=0)
    rating = Column(DECIMAL(3, 2), default=0)
    stock = Column(Integer, nullable=False, default=0)
    feature = Column(Text)
    sponsored = Column(Boolean, default=False)
    image_url = Column(Text)
    product_embedding = Column(Vector(384))  # Cambiado de 768 a 384 (MiniLM model)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())