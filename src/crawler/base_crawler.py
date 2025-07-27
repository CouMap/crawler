import os
import shutil
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from loguru import logger

from ..config import crawler_config, logging_config
from ..database import Database
from ..map_api import IntegratedMapAPI
from ..utils import CSVHandler, AddressParser


class BaseCrawler(ABC):
    """크롤러 기본 클래스"""

    def __init__(self):
        self.driver: Optional[webdriver.Chrome] = None
        self.db = Database()
        self.map_api = IntegratedMapAPI()
        self.address_parser = AddressParser()
        self.csv_handler = CSVHandler()

        # 크롤링 상태
        self.failed_stores: List[Dict[str, Any]] = []
        self.crawling_stats = {
            'total_found': 0,
            'total_saved': 0,
            'naver_success': 0,
            'kakao_success': 0,
            'api_failed': 0,
            'duplicates': 0,
            'errors': 0
        }

        # 로깅 설정
        self.setup_logging()

    def setup_logging(self):
        """로깅 설정"""
        log_file = logging_config.get_log_file_path(self.__class__.__name__.lower())

        logger.add(
            log_file,
            format=logging_config.FILE_FORMAT,
            level=logging_config.LEVEL,
            rotation="100 MB",
            retention="30 days"
        )

        logger.info(f"{self.__class__.__name__} 초기화 완료")

    def setup_driver(self):
        """크롬 드라이버 설정"""
        chrome_options = Options()

        # 기본 옵션 추가
        for option in crawler_config.CHROME_OPTIONS:
            chrome_options.add_argument(option)

        # 헤드리스 모드 설정
        if crawler_config.HEADLESS:
            chrome_options.add_argument('--headless')

        # User-Agent 설정
        chrome_options.add_argument(f'--user-agent={crawler_config.USER_AGENT}')

        # ChromeDriver 캐시 문제 해결
        try:
            cache_dir = os.path.expanduser("~/.wdm")
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir)
                logger.info("ChromeDriver 캐시 삭제 완료")
        except Exception as e:
            logger.warning(f"캐시 삭제 실패: {e}")

        # 드라이버 초기화 시도
        driver_initialized = False

        # 1. 시스템 PATH의 chromedriver 사용
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            logger.info("시스템 chromedriver 사용")
            driver_initialized = True
        except Exception as e1:
            logger.warning(f"시스템 chromedriver 실패: {e1}")

        # 2. Homebrew 경로의 chromedriver 사용
        if not driver_initialized:
            try:
                driver_path = "/opt/homebrew/bin/chromedriver"
                if os.path.exists(driver_path):
                    service = Service(driver_path)
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    logger.info("Homebrew chromedriver 사용")
                    driver_initialized = True
                else:
                    raise FileNotFoundError("Homebrew chromedriver 없음")
            except Exception as e2:
                logger.warning(f"Homebrew chromedriver 실패: {e2}")

        # 3. ChromeDriverManager를 마지막에 시도
        if not driver_initialized:
            try:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                logger.info("ChromeDriverManager 사용")
                driver_initialized = True
            except Exception as e3:
                logger.error(f"모든 드라이버 초기화 실패: {e3}")

        if not driver_initialized:
            raise Exception("ChromeDriver를 초기화할 수 없습니다.")

    @abstractmethod
    def access_website(self) -> bool:
        """웹사이트 접근"""
        pass

    @abstractmethod
    def extract_data(self) -> Dict[str, Any]:
        """데이터 추출"""
        pass

    @abstractmethod
    def extract_region_from_address(self, address: str):
        """주소에서 지역 정보 추출 (각 크롤러에서 구현)"""
        pass

    def save_store_data(self, stores_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """가맹점 데이터 저장 - API 이름 사용"""
        logger.info(f"가맹점 데이터 저장 시작: {len(stores_data)}개")

        stats = {
            'saved': 0,
            'skipped': 0,
            'api_failed': 0,
            'naver_success': 0,
            'kakao_success': 0,
            'duplicates': 0,
            'errors': 0,
            'new_regions': 0
        }

        for i, store_data in enumerate(stores_data, 1):
            try:
                logger.debug(f"[{i}/{len(stores_data)}] 처리 중: {store_data.get('name', '이름없음')}")

                # 필수 정보 확인
                original_name = store_data.get('name', '').strip()
                address = store_data.get('address', '').strip()
                category_name = store_data.get('category', '기타').strip()

                if not original_name or not address:
                    logger.warning(f"필수 정보 누락: {original_name} / {address}")
                    stats['skipped'] += 1
                    continue

                # 주소 파싱
                parsed_address = self.extract_region_from_address(address)
                if not parsed_address:
                    logger.warning(f"주소 파싱 실패: {address}")
                    stats['skipped'] += 1
                    continue

                province, city, town = parsed_address

                # 지역 조회 또는 생성
                region = self.db.get_or_create_region(province, city, town)

                # 지도 검색
                search_result = self.map_api.search_location(original_name, category_name, address)

                latitude = None
                longitude = None
                final_store_name = original_name  # 기본값은 크롤링한 이름

                if search_result['found']:
                    coords = search_result['coordinates']
                    latitude = coords['latitude']
                    longitude = coords['longitude']

                    # API에서 받은 이름 사용
                    if search_result.get('api_store_name'):
                        final_store_name = search_result['api_store_name']
                        logger.debug(f"API 이름 사용: '{original_name}' -> '{final_store_name}'")

                    api_used = search_result['api_used']
                    if api_used == 'naver':
                        stats['naver_success'] += 1
                    elif api_used == 'kakao':
                        stats['kakao_success'] += 1

                    logger.debug(f"지도 검색 성공: {api_used.upper()}")
                else:
                    logger.warning(f"지도 검색 실패: {original_name}")
                    stats['api_failed'] += 1

                    # 실패 데이터 저장
                    self.failed_stores.append({
                        'store_name': original_name,
                        'address': address,
                        'category': category_name,
                        'phone': store_data.get('phone', ''),
                        'store_type': store_data.get('type', ''),
                        'distance': store_data.get('distance', ''),
                        'search_attempts': search_result['query'],
                        'region_info': f"{region.province} {region.city} {region.town or ''}",
                        'failed_apis': 'naver,kakao',
                        'error_reason': search_result.get('error', 'Unknown'),
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })

                # 중복 체크 (최종 이름으로)
                if self.db.store_exists(final_store_name, address, region.id):
                    logger.debug(f"이미 존재하는 가맹점: {final_store_name}")
                    stats['duplicates'] += 1
                    stats['skipped'] += 1
                    continue

                # 카테고리 생성/조회
                category = self.db.create_category(
                    code=category_name.upper(),
                    name=category_name
                )

                # 가맹점 저장 (API에서 받은 이름 사용)
                self.db.create_store(
                    name=final_store_name,  # API 이름 사용
                    category=category,
                    region=region,
                    address=address,
                    latitude=latitude,
                    longitude=longitude,
                    annual_sales=None,
                    business_days='월~일',
                    category_str=category_name,
                    is_franchise=True,
                    opening_hours=None
                )

                stats['saved'] += 1
                logger.debug(f"저장 완료: {final_store_name}")

            except Exception as e:
                logger.error(f"가맹점 저장 실패 - {store_data.get('name', 'Unknown')}: {e}")
                stats['errors'] += 1

        # 실패 데이터 CSV 저장
        if self.failed_stores:
            self.csv_handler.save_failed_stores(self.failed_stores)

        # 통계 업데이트
        self.crawling_stats.update(stats)

        logger.info(f"가맹점 저장 완료 - 성공: {stats['saved']}, 신규 지역: {stats['new_regions']}")
        return stats

    def wait_with_delay(self, delay: float = None):
        """대기"""
        delay = delay or crawler_config.CRAWL_DELAY
        logger.debug(f"{delay}초 대기 중...")
        time.sleep(delay)

    def cleanup(self):
        """리소스 정리"""
        try:
            if self.driver:
                self.driver.quit()
                logger.info("브라우저 종료")

            if self.db:
                self.db.close()
                logger.info("데이터베이스 연결 종료")

            logger.info("크롤러 정리 완료")

        except Exception as e:
            logger.error(f"정리 중 오류: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """크롤링 통계 반환"""
        total = self.crawling_stats['total_saved'] + self.crawling_stats['api_failed']
        success_rate = (
            (self.crawling_stats['naver_success'] + self.crawling_stats['kakao_success']) / total * 100
            if total > 0 else 0
        )

        return {
            **self.crawling_stats,
            'success_rate': round(success_rate, 2)
        }

    def save_summary(self, region_name: str = "전체") -> Path:
        """크롤링 요약 저장"""
        summary = {
            'region': region_name,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            **self.get_statistics()
        }

        return self.csv_handler.save_crawling_summary(summary)