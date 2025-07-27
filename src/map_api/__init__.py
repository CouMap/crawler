from typing import Dict, Any, Optional
from loguru import logger

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

    def search_location(self, store_name: str, category: str, address: str) -> Dict[str, Any]:
        """통합 지도 검색 - 네이버 우선, 실패시 카카오"""
        logger.debug(f"통합 지도 검색 시작: {store_name}")

        # 1. 네이버 검색 API 우선 검색
        if self.naver_api:
            logger.debug("네이버 검색 API 시도...")
            naver_result = self.naver_api.search_store_location(store_name, category, address)

            if naver_result['found']:
                logger.debug("네이버 검색 API 성공!")
                return naver_result
            else:
                logger.debug("네이버 검색 API 실패")

        # 2. 카카오 지도 백업 검색
        if self.kakao_api:
            logger.debug("카카오 지도 백업 검색 시도...")
            kakao_result = self.kakao_api.search_store_location(store_name, category, address)

            if kakao_result['found']:
                logger.debug("카카오 지도 검색 성공!")
                return kakao_result
            else:
                logger.debug("카카오 지도 검색도 실패")

        # 3. 모든 검색 실패
        return {
            'found': False,
            'search_type': 'all_failed',
            'query': f"네이버+카카오 모두 실패",
            'coordinates': None,
            'api_used': 'none'
        }

    def get_coordinates_by_address(self, address: str) -> Dict[str, Any]:
        """주소로 좌표 조회"""
        # 카카오 API가 주소 검색에 더 정확함
        if self.kakao_api:
            result = self.kakao_api.get_coordinates_by_address(address)
            if result.get('found'):
                return result

        # 카카오 실패시 네이버 시도
        if self.naver_api:
            return self.naver_api.get_coordinates_by_address(address)

        return {'found': False}


# 편의를 위한 전역 인스턴스
def get_map_api() -> IntegratedMapAPI:
    """지도 API 인스턴스 반환"""
    return IntegratedMapAPI()