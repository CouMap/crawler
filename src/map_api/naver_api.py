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

                        # 비교용 주소: 지번주소 우선, 없으면 도로명주소
                        compare_address = base_address if base_address else road_address

                        # 저장용 주소: 도로명주소 우선, 없으면 지번주소
                        final_address = road_address if road_address else base_address

                        logger.debug(f"네이버 API 주소 처리:")
                        logger.debug(f"  - 도로명: '{road_address}'")
                        logger.debug(f"  - 지번: '{base_address}'")
                        logger.debug(f"  - 비교용: '{compare_address}'")
                        logger.debug(f"  - 저장용: '{final_address}'")

                        return {
                            'latitude': latitude,
                            'longitude': longitude,
                            'place_name': item.get('title', '').replace('<b>', '').replace('</b>', ''),
                            'base_address': base_address,
                            'road_address': road_address,
                            'compare_address': compare_address,  # 비교용 주소 추가
                            'final_address': final_address,  # 저장용 주소
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

        if address_parts:
            scenarios.append(f"{store_name} {' '.join(address_parts)}")

        for i in range(len(address_parts) - 1, 0, -1):
            if i <= len(address_parts):
                reduced_address = ' '.join(address_parts[:i])
                scenarios.append(f"{store_name} {reduced_address}")

        scenarios.append(store_name)

        unique_scenarios = []
        seen = set()
        for scenario in scenarios:
            scenario = scenario.strip()
            if scenario and scenario not in seen:
                unique_scenarios.append(scenario)
                seen.add(scenario)

        return unique_scenarios

    def validate_address_match(self, original_address: str, api_address: str) -> bool:
        """크롤링 주소와 API 주소의 시군구읍면동 일치 여부 확인"""
        try:
            from ..utils import AddressParser

            original_parsed = AddressParser.parse_address(original_address)
            api_parsed = AddressParser.parse_address(api_address)

            # 시/도 비교
            if original_parsed.get('province') != api_parsed.get('province'):
                logger.warning(f"시/도 불일치: 크롤링={original_parsed.get('province')} vs API={api_parsed.get('province')}")
                return False

            # 시/군/구 비교
            if original_parsed.get('city') != api_parsed.get('city'):
                logger.warning(f"시/군/구 불일치: 크롤링={original_parsed.get('city')} vs API={api_parsed.get('city')}")
                return False

            # 읍/면/동 비교
            original_town = original_parsed.get('town')
            api_town = api_parsed.get('town')

            if original_town and api_town:
                # 완전 일치
                if original_town == api_town:
                    logger.debug(f"읍/면/동 완전 일치: {original_town}")
                    return True

                # 부분 일치 검사
                if self._is_similar_town(original_town, api_town):
                    logger.debug(f"읍/면/동 유사 일치: 크롤링={original_town} vs API={api_town}")
                    return True

                # 완전히 다른 동인 경우 거부
                logger.warning(f"읍/면/동 불일치로 거부: 크롤링={original_town} vs API={api_town}")
                return False

            logger.debug(f"주소 검증 성공: {original_address} ↔ {api_address}")
            return True

        except Exception as e:
            logger.error(f"주소 검증 중 오류: {e}")
            return False

    def _is_similar_town(self, town1: str, town2: str) -> bool:
        """읍/면/동 유사성 검사"""
        import re

        # 숫자 제거 후 비교
        clean1 = re.sub(r'\d+', '', town1)
        clean2 = re.sub(r'\d+', '', town2)

        return clean1 == clean2

    def search_store_location(self, store_name: str, category: str, address: str) -> Dict[str, Any]:
        """네이버 검색 API 기반 가맹점 위치 확인 - 지번주소 비교, 도로명주소 저장"""
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
                    # 비교는 지번주소로 (compare_address)
                    compare_address = result.get('compare_address', '')

                    if self.validate_address_match(address, compare_address):
                        logger.info(f"네이버 검색 성공 (시나리오 {i}): {query}")

                        # 결과에 저장용 주소 추가 (도로명주소 우선)
                        result['final_address'] = result.get('road_address') or result.get('base_address', '')

                        return {
                            'found': True,
                            'search_type': f'naver_reduction_{i}',
                            'query': query,
                            'coordinates': result,
                            'api_used': 'naver'
                        }
                    else:
                        logger.warning(f"주소 불일치로 검색 결과 무효: {query}")
                        logger.debug(f"  크롤링 주소: {address}")
                        logger.debug(f"  API 비교 주소: {compare_address}")
                        continue

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