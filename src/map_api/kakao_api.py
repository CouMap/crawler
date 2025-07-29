import requests
from typing import Dict, Any
from loguru import logger

from .base import BaseMapAPI
from ..config import api_config


class KakaoMapAPI(BaseMapAPI):
    """카카오 지도 API 클래스"""

    def __init__(self):
        super().__init__("Kakao")

        if not api_config.KAKAO_API_KEY:
            raise ValueError("KAKAO_API_KEY 환경 변수가 필요합니다.")

        self.headers = {
            'Authorization': f'KakaoAK {api_config.KAKAO_API_KEY}',
            'Accept': 'application/json'
        }
        self.geocoding_url = 'https://dapi.kakao.com/v2/local/search/address.json'
        self.keyword_url = 'https://dapi.kakao.com/v2/local/search/keyword.json'

    def get_coordinates_by_keyword(self, query: str) -> Dict[str, Any]:
        """카카오 키워드 검색 API로 좌표 조회"""
        try:
            params = {
                'query': query,
                'size': 1,
                'sort': 'accuracy'
            }
            response = requests.get(
                self.keyword_url,
                headers=self.headers,
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('documents'):
                    doc = data['documents'][0]

                    address_name = doc.get('address_name', '').strip()
                    road_address_name = doc.get('road_address_name', '').strip()

                    # 비교용 주소: 지번주소 우선, 없으면 도로명주소
                    compare_address = address_name if address_name else road_address_name

                    # 저장용 주소: 도로명주소 우선, 없으면 지번주소
                    final_address = road_address_name if road_address_name else address_name

                    logger.debug(f"카카오 API 주소 처리:")
                    logger.debug(f"  - 도로명: '{road_address_name}'")
                    logger.debug(f"  - 지번: '{address_name}'")
                    logger.debug(f"  - 비교용: '{compare_address}'")
                    logger.debug(f"  - 저장용: '{final_address}'")

                    return {
                        'latitude': float(doc['y']),
                        'longitude': float(doc['x']),
                        'place_name': doc.get('place_name'),
                        'address_name': address_name,
                        'road_address_name': road_address_name,
                        'compare_address': compare_address,  # 비교용 주소 추가
                        'final_address': final_address,  # 저장용 주소
                        'category_name': doc.get('category_name'),
                        'found': True
                    }

            return self.handle_api_error(response, query)

        except Exception as e:
            logger.error(f"카카오 키워드 API 오류: {e}")
            return {
                'found': False,
                'error': str(e),
                'query': query
            }
        finally:
            self.rate_limit()

    def get_coordinates_by_address(self, address: str) -> Dict[str, Any]:
        """주소로 좌표 조회"""
        try:
            params = {'query': address}
            response = requests.get(
                self.geocoding_url,
                headers=self.headers,
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('documents'):
                    doc = data['documents'][0]

                    address_name = doc.get('address_name', '').strip()
                    road_address_name = doc.get('road_address_name', '').strip()

                    # 비교용 주소: 지번주소 우선
                    compare_address = address_name if address_name else road_address_name

                    # 저장용 주소: 도로명주소 우선
                    final_address = road_address_name if road_address_name else address_name

                    return {
                        'latitude': float(doc['y']),
                        'longitude': float(doc['x']),
                        'address_name': address_name,
                        'road_address_name': road_address_name,
                        'compare_address': compare_address,
                        'final_address': final_address,
                        'found': True
                    }

            return self.handle_api_error(response, address)

        except Exception as e:
            logger.error(f"카카오 지오코딩 API 오류: {e}")
            return {
                'found': False,
                'error': str(e),
                'query': address
            }
        finally:
            self.rate_limit()

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

            # 읍/면/동 비교 - 지번주소 기준으로 완화
            original_town = original_parsed.get('town')
            api_town = api_parsed.get('town')

            if original_town and api_town:
                # 완전 일치
                if original_town == api_town:
                    logger.debug(f"읍/면/동 완전 일치: {original_town}")
                    return True

                # 부분 일치 검사 (동산동 vs 동산1동 같은 경우)
                if self._is_similar_town(original_town, api_town):
                    logger.debug(f"읍/면/동 유사 일치: 크롤링={original_town} vs API={api_town}")
                    return True

                # 지번주소 사용 시 읍/면/동 불일치 경고만 하고 통과
                logger.info(f"읍/면/동 불일치하지만 지번주소 기준으로 허용: 크롤링={original_town} vs API={api_town}")
                return True

            logger.debug(f"주소 검증 성공: {original_address} ↔ {api_address}")
            return True

        except Exception as e:
            logger.error(f"주소 검증 중 오류: {e}")
            return False

    def _is_similar_town(self, town1: str, town2: str) -> bool:
        """읍/면/동 유사성 검사"""
        import re

        # 숫자 제거 후 비교 (동산동 vs 동산1동)
        clean1 = re.sub(r'\d+', '', town1)
        clean2 = re.sub(r'\d+', '', town2)

        if clean1 == clean2:
            return True

        # 앞 2글자만 비교 (동산동 vs 동세로 - 이건 다름)
        if len(clean1) >= 2 and len(clean2) >= 2:
            return clean1[:2] == clean2[:2]

        return False

    def search_store_location(self, store_name: str, category: str, address: str) -> Dict[str, Any]:
        """카카오 키워드 검색 기반 가맹점 위치 확인 - 지번주소 비교, 도로명주소 저장"""
        try:
            logger.debug(f"카카오 키워드 검색 시작: {store_name}")
            clean_address = self.clean_address_for_search(address)
            search_scenarios = self.create_search_scenarios_with_reduction(store_name, clean_address)
            logger.debug(f"카카오 검색 시나리오 ({len(search_scenarios)}개): {search_scenarios}")

            for i, query in enumerate(search_scenarios, 1):
                if not query:
                    continue

                logger.debug(f"{i}차 카카오 검색 (축소전략): {query}")
                result = self.get_coordinates_by_keyword(query)

                if result.get('found'):
                    # 비교는 지번주소로 (compare_address)
                    compare_address = result.get('compare_address', '')

                    if self.validate_address_match(address, compare_address):
                        logger.info(f"카카오 검색 성공 (시나리오 {i}): {query}")

                        # 결과에 저장용 주소 추가 (도로명주소 우선)
                        result['final_address'] = result.get('road_address_name') or result.get('address_name', '')

                        return {
                            'found': True,
                            'search_type': f'kakao_reduction_{i}',
                            'query': query,
                            'coordinates': result,
                            'api_used': 'kakao'
                        }
                    else:
                        logger.warning(f"주소 불일치로 검색 결과 무효: {query}")
                        logger.debug(f"  크롤링 주소: {address}")
                        logger.debug(f"  API 비교 주소: {compare_address}")
                        continue

            failed_queries = ' → '.join(search_scenarios)
            logger.warning(f"모든 카카오 축소 검색 실패: {failed_queries}")

            return {
                'found': False,
                'search_type': 'kakao_reduction_failed',
                'query': failed_queries,
                'coordinates': None,
                'api_used': 'kakao'
            }

        except Exception as e:
            logger.error(f"카카오 검색 중 오류: {e}")
            return {
                'found': False,
                'search_type': 'kakao_error',
                'query': store_name,
                'coordinates': None,
                'api_used': 'kakao',
                'error': str(e)
            }