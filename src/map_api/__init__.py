from typing import Dict, Any, Optional
from loguru import logger
import re

from .naver_api import NaverSearchAPI
from .kakao_api import KakaoMapAPI


class IntegratedMapAPI:
    """통합 지도 API 관리 클래스"""

    def __init__(self):
        self.naver_api: Optional[NaverSearchAPI] = None
        self.kakao_api: Optional[KakaoMapAPI] = None

        # 네이버 검색 API 초기화
        try:
            self.naver_api = NaverSearchAPI()
            logger.info("네이버 검색 API 초기화 성공")
        except Exception as e:
            logger.warning(f"네이버 검색 API 초기화 실패: {e}")

        # 카카오 API 초기화
        try:
            self.kakao_api = KakaoMapAPI()
            logger.info("카카오 지도 API 초기화 성공")
        except Exception as e:
            logger.warning(f"카카오 지도 API 초기화 실패: {e}")

        if not self.naver_api and not self.kakao_api:
            raise ValueError("네이버와 카카오 지도 API 모두 초기화에 실패했습니다.")

    def clean_store_name(self, store_name: str) -> str:
        """가맹점명 정리 - (주), 주식회사, 영어명 등 제거"""
        cleaned_name = store_name.strip()

        # 제거할 패턴들
        patterns_to_remove = [
            r'\(주\)',  # (주)
            r'\(株\)',  # (株)
            r'주식회사\s*',  # 주식회사
            r'㈜\s*',  # ㈜
            r'\s*회사$',  # 끝에 있는 "회사"
            r'\s*코퍼레이션$',  # 끝에 있는 "코퍼레이션"
            r'\s*corporation$',  # 끝에 있는 "corporation"
            r'\s*corp\.?$',  # 끝에 있는 "corp" 또는 "corp."
            r'\s*inc\.?$',  # 끝에 있는 "inc" 또는 "inc."
            r'\s*ltd\.?$',  # 끝에 있는 "ltd" 또는 "ltd."
            r'\([A-Za-z\s]+\)',  # 영어가 포함된 괄호 제거 (예: (McDonald's), (KFC))
        ]

        for pattern in patterns_to_remove:
            cleaned_name = re.sub(pattern, '', cleaned_name, flags=re.IGNORECASE)

        cleaned_name = re.sub(r'\s+', ' ', cleaned_name).strip()

        if cleaned_name != store_name:
            logger.debug(f"가맹점명 정리: '{store_name}' -> '{cleaned_name}'")

        return cleaned_name

    def search_location(self, store_name: str, category: str, address: str) -> Dict[str, Any]:
        """통합 지도 검색 - 네이버 우선, 실패시 카카오"""
        logger.debug(f"통합 지도 검색 시작: {store_name}")

        # 가맹점명 정리
        cleaned_store_name = self.clean_store_name(store_name)

        # 1. 네이버 검색 API 우선 검색
        if self.naver_api:
            logger.debug("네이버 검색 API 시도...")
            naver_result = self.naver_api.search_store_location(cleaned_store_name, category, address)

            if naver_result['found']:
                logger.info(f"네이버 검색 API 성공: {store_name}")
                # API에서 받은 이름과 주소 사용
                if 'coordinates' in naver_result and 'place_name' in naver_result['coordinates']:
                    naver_result['api_store_name'] = naver_result['coordinates']['place_name']
                    api_address = naver_result['coordinates'].get('final_address', '').strip()
                    naver_result['api_store_addr'] = api_address if api_address else address
                else:
                    naver_result['api_store_name'] = store_name
                    naver_result['api_store_addr'] = address
                return naver_result
            else:
                logger.warning(f"네이버 검색 API 실패: {store_name}")

        # 2. 카카오 지도 백업 검색
        if self.kakao_api:
            logger.debug("카카오 지도 백업 검색 시도...")
            kakao_result = self.kakao_api.search_store_location(cleaned_store_name, category, address)

            if kakao_result['found']:
                logger.info(f"카카오 지도 검색 성공: {store_name}")
                # API에서 받은 이름과 주소 사용
                if 'coordinates' in kakao_result and 'place_name' in kakao_result['coordinates']:
                    kakao_result['api_store_name'] = kakao_result['coordinates']['place_name']
                    kakao_result['api_store_addr'] = kakao_result['coordinates'].get('road_address_name', address)
                else:
                    kakao_result['api_store_name'] = store_name
                    kakao_result['api_store_addr'] = address
                return kakao_result
            else:
                logger.warning(f"카카오 지도 검색도 실패: {store_name}")

        # 3. 모든 검색 실패
        logger.error(f"모든 지도 API 검색 실패: {store_name}")
        return {
            'found': False,
            'search_type': 'all_failed',
            'query': f"네이버+카카오 모두 실패: {cleaned_store_name}",
            'coordinates': None,
            'api_used': 'none',
            'original_name': store_name,
            'cleaned_name': cleaned_store_name,
            'api_store_name': store_name,
            'api_store_addr': address
        }

    def get_coordinates_by_address(self, address: str) -> Dict[str, Any]:
        """주소로 좌표 조회"""
        if self.kakao_api:
            logger.debug("카카오 API로 주소 검색 시도...")
            result = self.kakao_api.get_coordinates_by_address(address)
            if result.get('found'):
                logger.info(f"카카오 주소 검색 성공: {address}")
                return result
            else:
                logger.warning(f"카카오 주소 검색 실패: {address}")

        # 카카오 실패시 네이버 시도
        if self.naver_api:
            logger.debug("네이버 API로 주소 검색 시도...")
            result = self.naver_api.get_coordinates_by_address(address)
            if result.get('found'):
                logger.info(f"네이버 주소 검색 성공: {address}")
                return result
            else:
                logger.warning(f"네이버 주소 검색도 실패: {address}")

        logger.error(f"모든 API 주소 검색 실패: {address}")
        return {'found': False}


def get_map_api() -> IntegratedMapAPI:
    """지도 API 인스턴스 반환"""
    return IntegratedMapAPI()