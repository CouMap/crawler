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
                    return {
                        'latitude': float(doc['y']),
                        'longitude': float(doc['x']),
                        'place_name': doc.get('place_name'),
                        'address_name': doc.get('address_name'),
                        'road_address_name': doc.get('road_address_name'),
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
                    return {
                        'latitude': float(doc['y']),
                        'longitude': float(doc['x']),
                        'address_name': doc.get('address_name'),
                        'road_address_name': doc.get('road_address_name'),
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
        """카카오 키워드 검색 기반 가맹점 위치 확인 - 축소 전략 사용"""
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
                    logger.info(f"카카오 검색 성공 (시나리오 {i}): {query}")
                    return {
                        'found': True,
                        'search_type': f'kakao_reduction_{i}',
                        'query': query,
                        'coordinates': result,
                        'api_used': 'kakao'
                    }

            # 모든 시나리오 실패
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