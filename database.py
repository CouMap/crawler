from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import logging

from models import Base, Region, Category, Store
from config import *

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self.connect()

    def connect(self):
        """데이터베이스 연결"""
        try:
            db_url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

            self.engine = create_engine(db_url, echo=False)
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

    def get_all_regions(self):
        """모든 지역 조회"""
        with self.get_session() as session:
            return session.query(Region).all()

    def get_category_by_name(self, name):
        """카테고리명으로 조회"""
        with self.get_session() as session:
            return session.query(Category).filter(Category.name == name).first()

    def create_category(self, code, name):
        """카테고리 생성 또는 기존 반환"""
        with self.get_session() as session:
            existing = session.query(Category).filter(Category.name == name).first()
            if existing:
                return existing

            category = Category(code=code, name=name)
            session.add(category)
            session.flush()

            logger.info(f"새 카테고리 생성: {name}")
            return category

    def store_exists(self, name, address, region_id):
        """중복 가맹점 체크"""
        with self.get_session() as session:
            count = session.query(Store).filter(
                Store.name == name,
                Store.address == address,
                Store.region_id == region_id
            ).count()
            return count > 0

    def create_store(self, name, category, region, address, latitude=None, longitude=None):
        """가맹점 생성"""
        with self.get_session() as session:
            store = Store(
                name=name,
                category_id=category.id,
                region_id=region.id,
                address=address,
                latitude=latitude,
                longitude=longitude,
                is_franchise=True,
                business_days='월~일'
            )

            session.add(store)
            session.flush()

            logger.debug(f"가맹점 저장: {name}")
            return store

    def get_statistics(self):
        """통계 조회"""
        with self.get_session() as session:
            total = session.query(Store).count()
            with_coords = session.query(Store).filter(
                Store.latitude.isnot(None),
                Store.longitude.isnot(None)
            ).count()

            return {
                'total_stores': total,
                'stores_with_coordinates': with_coords,
                'success_rate': round((with_coords / total * 100) if total > 0 else 0, 2)
            }

    def close(self):
        """연결 종료"""
        if self.engine:
            self.engine.dispose()