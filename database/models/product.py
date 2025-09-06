from sqlalchemy import Integer, Column, String, Text, Float, Boolean, DateTime, func
from sqlalchemy.orm import relationship

from database.connection import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)  # price in dollars
    category = Column(String(100))
    in_stock = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    order_items = relationship("OrderItem", back_populates="product")