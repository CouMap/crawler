from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Region(Base):
    """지역 정보 모델"""
    __tablename__ = 'region'

    id = Column(Integer, primary_key=True)
    province = Column(String(255), nullable=False)
    city = Column(String(255), nullable=False)
    town = Column(String(255), nullable=True)
    code = Column(String(255), unique=True, nullable=True)

    # 관계 추가
    stores = relationship("Store", back_populates="region")

    def __repr__(self):
        return f"<Region({self.province} {self.city} {self.town})>"

    @property
    def full_name(self):
        """전체 지역명 반환"""
        parts = [self.province, self.city]
        if self.town:
            parts.append(self.town)
        return " ".join(parts)


class Category(Base):
    """카테고리 모델"""
    __tablename__ = 'category'

    id = Column(Integer, primary_key=True)
    code = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)

    # 관계 추가
    stores = relationship("Store", back_populates="category_obj")

    def __repr__(self):
        return f"<Category({self.name})>"


class Store(Base):
    """가맹점 모델"""
    __tablename__ = 'store'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    address = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    annual_sales = Column(Integer, nullable=True)
    business_days = Column(String(255), nullable=True)
    category = Column(String(255), nullable=True)  # 문자열 카테고리
    is_franchise = Column(Boolean, nullable=True)
    opening_hours = Column(String(255), nullable=True)

    # 외래키
    region_id = Column(Integer, ForeignKey('region.id'), nullable=False)
    category_id = Column(Integer, ForeignKey('category.id'), nullable=False)

    # 관계 추가
    region = relationship("Region", back_populates="stores")
    category_obj = relationship("Category", back_populates="stores")  # category는 이미 컬럼명이라 category_obj로

    def __repr__(self):
        return f"<Store({self.name})>"

    @property
    def has_coordinates(self):
        """좌표 정보 보유 여부"""
        return self.latitude is not None and self.longitude is not None

    @property
    def full_address(self):
        """전체 주소 반환"""
        if self.region:
            return f"{self.region.full_name} {self.address}"
        return self.address