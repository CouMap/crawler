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
                'display': 1,
                'start': 1,
                'sort': 'comment'
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
                        longitude = float(mapx) / 10000000
                        latitude = float(mapy) / 10000000

                        road_address = item.get('roadAddress', '').strip()
                        base_address = item.get('address', '').strip()

                        final_address = road_address if road_address else base_address

                        logger.debug(f"네이버 API 주소 처리: 도로명='{road_address}', 지번='{base_address}', 최종='{final_address}'")

                        return {
                            'latitude': latitude,
                            'longitude': longitude,
                            'place_name': item.get('title', '').replace('<b>', '').replace('</b>', ''),
                            'base_address': base_address,
                            'road_address': road_address,
                            'final_address': final_address,
                            'category': item.get('category', ''),
                            'found': True
                        }

                logger.debug(f"네이버 API 검색 결과 없음: {query}")
                return {
                    'found': False,
                    'error': 'No results found',
                    'query': query
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

    def create_search_scenarios_with_reduction(self, store_name: str, address: str) -> list:
        """검색어 축소 전략으로 시나리오 생성"""
        scenarios = []

        address_parts = address.strip().split()

        # 1단계: 상호명 + 전체 주소
        if address_parts:
            scenarios.append(f"{store_name} {' '.join(address_parts)}")

        # 2단계: 상호명 + 주소 축소
        for i in range(len(address_parts) - 1, 0, -1):
            if i <= len(address_parts):
                reduced_address = ' '.join(address_parts[:i])
                scenarios.append(f"{store_name} {reduced_address}")

        # 3단계: 상호명만
        scenarios.append(store_name)

        # 중복 제거하면서 순서 유지
        unique_scenarios = []
        seen = set()
        for scenario in scenarios:
            scenario = scenario.strip()
            if scenario and scenario not in seen:
                unique_scenarios.append(scenario)
                seen.add(scenario)

        return unique_scenarios

    def search_store_location(self, store_name: str, category: str, address: str) -> Dict[str, Any]:
        """네이버 검색 API 기반 가맹점 위치 확인 - 축소 전략 사용"""
        try:
            logger.debug(f"네이버 검색 API 시작: {store_name}")

            clean_address = self.clean_address_for_search(address)

            search_scenarios = self.create_search_scenarios_with_reduction(store_name, clean_address)

            logger.debug(f"검색 시나리오 ({len(search_scenarios)}개): {search_scenarios}")

            for i, query in enumerate(search_scenarios, 1):
                if not query:
                    continue

                logger.debug(f"{i}차 네이버 검색 (축소전략): {query}")
                result = self.get_coordinates_by_keyword(query)

                if result.get('found'):
                    logger.info(f"네이버 검색 성공 (시나리오 {i}): {query}")
                    return {
                        'found': True,
                        'search_type': f'naver_reduction_{i}',
                        'query': query,
                        'coordinates': result,
                        'api_used': 'naver'
                    }

            # 모든 시나리오 실패
            failed_queries = ' → '.join(search_scenarios)
            logger.warning(f"모든 축소 검색 실패: {failed_queries}")

            return {
                'found': False,
                'search_type': 'naver_reduction_failed',
                'query': failed_queries,
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