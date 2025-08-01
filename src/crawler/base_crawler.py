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
    """크롤러 기본 클래스 - 개선된 세션 복구 로직"""

    def __init__(self):
        self.driver: Optional[webdriver.Chrome] = None
        self.db = Database()
        self.map_api = IntegratedMapAPI()
        self.address_parser = AddressParser()
        self.csv_handler = CSVHandler()

        # 세션 복구 설정
        self.recovery_enabled = True
        self.max_recovery_attempts = 2
        self.recovery_count = 0

        # 크롤링 상태
        self.failed_stores: List[Dict[str, Any]] = []
        self.crawling_stats = {
            'total_found': 0,
            'total_saved': 0,
            'naver_success': 0,
            'kakao_success': 0,
            'api_failed': 0,
            'duplicates': 0,
            'errors': 0,
            'recovery_attempts': 0
        }

        # 현재 크롤링 상태 저장
        self.current_state = {
            'province': None,
            'district': None,
            'dong': None,
            'step': 'init'
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
                logger.debug("ChromeDriver 캐시 삭제 완료")
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

    def save_crawling_state(self, province=None, district=None, dong=None, step='unknown'):
        """현재 크롤링 상태 저장"""
        self.current_state = {
            'province': province,
            'district': district,
            'dong': dong,
            'step': step,
            'timestamp': time.time()
        }
        logger.debug(f"크롤링 상태 저장: {self.current_state}")

    def is_session_error(self, error: Exception) -> bool:
        """세션 관련 오류인지 판단"""
        error_msg = str(error).lower()
        session_keywords = [
            'invalid session',
            'session not created',
            'chrome not reachable',
            'connection refused',
            'no such window',
            'disconnected',
            'target window already closed',
            'chrome has crashed',
            'session deleted because of page crash'
        ]
        return any(keyword in error_msg for keyword in session_keywords)

    def check_browser_health(self) -> bool:
        """브라우저 상태 확인"""
        try:
            # 여러 방법으로 브라우저 상태 확인
            url = self.driver.current_url
            title = self.driver.title

            # JavaScript 실행 테스트
            result = self.driver.execute_script("return document.readyState;")

            logger.debug(f"브라우저 상태 확인 성공 - URL: {url[:50]}..., 상태: {result}")
            return True

        except Exception as e:
            logger.warning(f"브라우저 상태 확인 실패: {e}")
            return False

    def quick_recovery(self) -> bool:
        """빠른 세션 복구"""
        try:
            logger.info("빠른 세션 복구 시도...")
            self.crawling_stats['recovery_attempts'] += 1

            # 기존 드라이버 안전하게 정리
            if self.driver:
                try:
                    self.driver.quit()
                    logger.debug("기존 드라이버 종료 완료")
                except:
                    logger.debug("기존 드라이버 종료 중 오류 (무시)")

            # 잠시 대기
            time.sleep(2)

            # 새 드라이버 설정
            self.setup_driver()
            logger.debug("새 드라이버 설정 완료")

            # 기본 사이트 접근
            self.driver.get(crawler_config.KB_CARD_URL)
            time.sleep(3)

            # 브라우저 상태 확인
            if self.check_browser_health():
                logger.info("빠른 세션 복구 성공")
                return True
            else:
                logger.warning("세션은 복구되었지만 브라우저 상태가 불안정")
                return False

        except Exception as e:
            logger.error(f"빠른 세션 복구 실패: {e}")
            return False

    def execute_with_recovery(self, func, *args, description="", **kwargs):
        """개선된 복구 기능이 있는 함수 실행"""
        if not self.recovery_enabled:
            logger.debug(f"복구 기능 비활성화 상태에서 실행: {description}")
            return func(*args, **kwargs)

        last_error = None

        for attempt in range(self.max_recovery_attempts):
            try:
                if attempt > 0:
                    logger.info(f"재시도 {attempt}/{self.max_recovery_attempts - 1}: {description}")
                else:
                    logger.debug(f"실행 중: {description}")

                # 브라우저 상태 사전 확인 (첫 시도가 아닌 경우)
                if attempt > 0 and not self.check_browser_health():
                    raise Exception("Browser health check failed")

                # 함수 실행
                result = func(*args, **kwargs)

                if attempt > 0:
                    logger.info(f"재시도 성공: {description}")

                return result

            except Exception as e:
                last_error = e
                logger.warning(f"실행 실패 ({attempt + 1}/{self.max_recovery_attempts}): {description} - {e}")

                # 마지막 시도인 경우 복구하지 않고 바로 에러 발생
                if attempt >= self.max_recovery_attempts - 1:
                    break

                # 세션 관련 오류인지 확인
                if self.is_session_error(e):
                    logger.warning(f"세션 오류 감지, 복구 시도: {e}")

                    if self.quick_recovery():
                        logger.info("세션 복구 성공, 다시 시도")
                        continue
                    else:
                        logger.error("세션 복구 실패")
                        break
                else:
                    # 세션 오류가 아닌 경우 바로 종료
                    logger.debug(f"세션 오류가 아님, 재시도하지 않음: {e}")
                    break

        # 모든 시도 실패
        logger.error(f"모든 시도 실패: {description}")
        raise last_error

    def execute_simple(self, func, *args, description="", **kwargs):
        """단순 실행 (복구 없음)"""
        logger.debug(f"단순 실행: {description}")
        return func(*args, **kwargs)

    def disable_recovery(self):
        """복구 기능 비활성화"""
        self.recovery_enabled = False
        logger.info("세션 복구 기능 비활성화")

    def enable_recovery(self):
        """복구 기능 활성화"""
        self.recovery_enabled = True
        logger.info("세션 복구 기능 활성화")

    def save_store_data(self, stores_data: List[Dict[str, Any]]) -> Dict[str, int]:
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

                # 지도 검색 실패시 DB에 저장하지 않고 실패 데이터에만 추가
                if not search_result['found']:
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

                    # DB에 저장하지 않고 다음 가맹점으로
                    continue

                # 지도 검색 성공시에만 DB 저장 진행
                coords = search_result['coordinates']
                latitude = coords['latitude']
                longitude = coords['longitude']

                # API에서 받은 이름, 주소 사용
                final_store_name = search_result.get('api_store_name', original_name)
                final_store_addr = search_result.get('api_store_addr', address)

                api_used = search_result['api_used']
                if api_used == 'naver':
                    stats['naver_success'] += 1
                elif api_used == 'kakao':
                    stats['kakao_success'] += 1

                logger.debug(f"지도 검색 성공: {api_used.upper()}")

                # 중복 체크
                if self.db.store_exists(final_store_name, final_store_addr, region.id):
                    logger.debug(f"이미 존재하는 가맹점: {final_store_name}")
                    stats['duplicates'] += 1
                    stats['skipped'] += 1
                    continue

                # 카테고리 생성/조회
                category = self.db.create_category(
                    code=category_name.upper(),
                    name=category_name
                )

                # 가맹점 저장 (좌표 있는 경우에만)
                self.db.create_store(
                    name=final_store_name,
                    category=category,
                    region=region,
                    address=final_store_addr,
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

        logger.info(f"가맹점 저장 완료 - 성공: {stats['saved']}, 실패: {stats['api_failed']}")
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