from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Region(Base):
    __tablename__ = 'region'

    id = Column(Integer, primary_key=True)
    province = Column(String(50), nullable=False)
    city = Column(String(50), nullable=False)
    town = Column(String(50))
    code = Column(String(100), unique=True, nullable=False)

    # 관계
    stores = relationship("Store", back_populates="region")

    def __repr__(self):
        return f"<Region({self.province} {self.city} {self.town})>"


class Category(Base):
    __tablename__ = 'category'

    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)

    # 관계
    stores = relationship("Store", back_populates="category")

    def __repr__(self):
        return f"<Category({self.name})>"


class Store(Base):
    __tablename__ = 'store'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    address = Column(Text, nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)
    is_franchise = Column(Boolean, default=True)
    opening_hours = Column(String(100))
    business_days = Column(String(50), default='월~일')
    annual_sales = Column(Integer)

    # 외래키
    category_id = Column(Integer, ForeignKey('category.id'), nullable=False)
    region_id = Column(Integer, ForeignKey('region.id'), nullable=False)

    # 관계
    category = relationship("Category", back_populates="stores")
    region = relationship("Region", back_populates="stores")

    def __repr__(self):
        return f"<Store({self.name})>"