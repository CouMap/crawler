from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from loguru import logger
import re
from datetime import datetime
from typing import Optional, List, Dict, Any

from .models import Base, Region, Category, Store
from .config import db_config


class Database:
    """데이터베이스 관리 클래스"""

    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self.connect()

    def connect(self):
        """데이터베이스 연결"""
        try:
            self.engine = create_engine(
                db_config.url,
                echo=False,
                pool_pre_ping=True,
                pool_recycle=3600
            )
            self.SessionLocal = sessionmaker(bind=self.engine)
            logger.info("데이터베이스 연결 성공")
        except Exception as e:
            logger.error(f"데이터베이스 연결 실패: {e}")
            raise

    @contextmanager
    def get_session(self):
        """세션 컨텍스트 매니저"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"데이터베이스 오류: {e}")
            raise
        finally:
            session.close()

    def create_tables(self):
        """테이블 생성"""
        try:
            Base.metadata.create_all(self.engine)
            logger.info("데이터베이스 테이블 생성 완료")
        except Exception as e:
            logger.error(f"테이블 생성 실패: {e}")
            raise

    def get_or_create_region(self, province: str, city: str, town: Optional[str] = None) -> Region:
        """지역 조회 또는 생성"""
        import time

        with self.get_session() as session:
            # 1차: 정확한 매칭 시도
            result = session.query(Region).filter(
                Region.province == province,
                Region.city == city,
                Region.town == town
            ).first()

            if result:
                logger.debug(f"기존 지역 매칭: {result.province} {result.city} {result.town}")
                session.expunge(result)
                return result

            # 2차: 없으면 새로 생성
            logger.info(f"새 지역 생성: {province} {city} {town}")

            # 지역 코드 생성 (유니크하게)
            import hashlib
            code_str = f"{province}{city}{town or ''}{int(time.time())}"
            code = hashlib.md5(code_str.encode()).hexdigest()[:10]

            new_region = Region(
                province=province,
                city=city,
                town=town,
                code=code
            )

            session.add(new_region)
            session.flush()
            session.expunge(new_region)

            logger.info(f"지역 생성 완료: ID={new_region.id}, {province} {city} {town}")
            return new_region


    def get_all_regions(self) -> List[Region]:
        """모든 지역 조회"""
        with self.get_session() as session:
            regions = session.query(Region).all()
            for region in regions:
                session.expunge(region)
            return regions

    def get_category_by_name(self, name: str) -> Optional[Category]:
        """카테고리명으로 조회"""
        with self.get_session() as session:
            result = session.query(Category).filter(Category.name == name).first()
            if result:
                session.expunge(result)
            return result

    def create_category(self, code: str, name: str) -> Category:
        """카테고리 생성 또는 기존 반환"""
        with self.get_session() as session:
            existing = session.query(Category).filter(Category.name == name).first()
            if existing:
                session.expunge(existing)
                return existing

            category = Category(
                code=code,
                name=name
            )
            session.add(category)
            session.flush()
            session.expunge(category)

            logger.info(f"새 카테고리 생성: {name}")
            return category

    def store_exists(self, name: str, address: str, region_id: int) -> bool:
        """중복 가맹점 체크"""
        with self.get_session() as session:
            count = session.query(Store).filter(
                and_(
                    Store.name == name,
                    Store.address == address,
                    Store.region_id == region_id
                )
            ).count()
            return count > 0

    def create_store(self, name: str, category: Category, region: Region,
                     address: str, latitude: float = None, longitude: float = None,
                     annual_sales: int = None, business_days: str = None,
                     category_str: str = None, is_franchise: bool = True,
                     opening_hours: str = None) -> Store:
        """가맹점 생성"""
        with self.get_session() as session:
            store = Store(
                name=name,
                category_id=category.id,
                region_id=region.id,
                address=address,
                latitude=latitude,
                longitude=longitude,
                annual_sales=annual_sales,
                business_days=business_days or '월~일',
                category=category_str,  # 문자열 카테고리
                is_franchise=is_franchise,
                opening_hours=opening_hours
            )

            session.add(store)
            session.flush()
            session.expunge(store)

            logger.debug(f"가맹점 저장: {name}")
            return store

    def get_statistics(self) -> Dict[str, Any]:
        """통계 조회"""
        with self.get_session() as session:
            total = session.query(Store).count()
            with_coords = session.query(Store).filter(
                and_(
                    Store.latitude.isnot(None),
                    Store.longitude.isnot(None)
                )
            ).count()

            by_category_str = session.query(
                Store.category,
                session.query(Store).filter(Store.category == Store.category).count()
            ).group_by(Store.category).all() if total > 0 else []

            by_category_obj = session.query(
                Category.name,
                session.query(Store).filter(Store.category_id == Category.id).count()
            ).join(Store).group_by(Category.name).all() if total > 0 else []

            return {
                'total_stores': total,
                'stores_with_coordinates': with_coords,
                'success_rate': round((with_coords / total * 100) if total > 0 else 0, 2),
                'stores_by_category_str': dict(by_category_str),
                'stores_by_category_obj': dict(by_category_obj)
            }

    def close(self):
        """연결 종료"""
        if self.engine:
            self.engine.dispose()
            logger.info("데이터베이스 연결 종료")