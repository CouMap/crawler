import requests
from typing import Dict, Any
from loguru import logger

from .base import BaseMapAPI
from ..config import api_config


class NaverSearchAPI(BaseMapAPI):
    """네이버 검색 API 클래스"""

    def __init__(self):
        super().__init__("Naver")

        if not api_config.NAVER_CLIENT_ID or not api_config.NAVER_CLIENT_SECRET:
            raise ValueError("NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET 환경 변수가 필요합니다.")

        self.headers = {
            'X-Naver-Client-Id': api_config.NAVER_CLIENT_ID,
            'X-Naver-Client-Secret': api_config.NAVER_CLIENT_SECRET,
            'Accept': 'application/json'
        }
        self.search_url = 'https://openapi.naver.com/v1/search/local.json'

    def get_coordinates_by_keyword(self, query: str) -> Dict[str, Any]:
        """네이버 지역검색 API로 좌표 조회"""
        try:
            params = {
                'query': query,
                'display': 5,
                'start': 1,
                'sort': 'random'
            }

            response = requests.get(
                self.search_url,
                headers=self.headers,
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('items') and len(data['items']) > 0:
                    item = data['items'][0]

                    mapx = item.get('mapx', '')
                    mapy = item.get('mapy', '')

                    if mapx and mapy:
                        # 카텍좌표계를 WGS84로 변환
                        longitude = float(mapx) / 10000000
                        latitude = float(mapy) / 10000000

                        return {
                            'latitude': latitude,
                            'longitude': longitude,
                            'place_name': item.get('title', '').replace('<b>', '').replace('</b>', ''),
                            'address_name': item.get('address', ''),
                            'road_address': item.get('roadAddress', ''),
                            'category': item.get('category', ''),
                            'found': True
                        }

            return self.handle_api_error(response, query)

        except Exception as e:
            logger.error(f"네이버 검색 API 오류: {e}")
            return {
                'found': False,
                'error': str(e),
                'query': query
            }
        finally:
            self.rate_limit()

    def get_coordinates_by_address(self, address: str) -> Dict[str, Any]:
        """주소로 좌표 조회 (키워드 검색 사용)"""
        return self.get_coordinates_by_keyword(address)

    def search_store_location(self, store_name: str, category: str, address: str) -> Dict[str, Any]:
        """네이버 검색 API 기반 가맹점 위치 확인"""
        try:
            logger.debug(f"네이버 검색 API 시작: {store_name}")

            # 주소 정리
            clean_address = self.clean_address_for_search(address)
            dong = self.extract_dong_from_address(clean_address)

            # 검색 시나리오들
            search_scenarios = [
                f"{store_name} {dong} {category}".strip(),
                f"{store_name} {dong}".strip(),
                f"{store_name} {category}".strip(),
                store_name
            ]

            for i, query in enumerate(search_scenarios, 1):
                if not query:
                    continue

                logger.debug(f"{i}차 네이버 검색: {query}")
                result = self.get_coordinates_by_keyword(query)

                if result.get('found'):
                    return {
                        'found': True,
                        'search_type': f'naver_scenario_{i}',
                        'query': query,
                        'coordinates': result,
                        'api_used': 'naver'
                    }

            # 모든 시나리오 실패
            return {
                'found': False,
                'search_type': 'naver_failed',
                'query': ' / '.join(search_scenarios),
                'coordinates': None,
                'api_used': 'naver'
            }

        except Exception as e:
            logger.error(f"네이버 검색 중 오류: {e}")
            return {
                'found': False,
                'search_type': 'naver_error',
                'query': store_name,
                'coordinates': None,
                'api_used': 'naver',
                'error': str(e)
            }