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
            params = {'query': query, 'size': 1}
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

    def search_store_location(self, store_name: str, category: str, address: str) -> Dict[str, Any]:
        """카카오 키워드 검색 기반 가맹점 위치 확인"""
        try:
            logger.debug(f"카카오 키워드 검색 시작: {store_name}")

            # 주소 정리
            clean_address = self.clean_address_for_search(address)
            dong = self.extract_dong_from_address(clean_address)

            # 검색 시나리오들
            search_scenarios = [
                f"{store_name} {dong}".strip(),
                f"{store_name} {category} {dong}".strip(),
            ]

            for i, query in enumerate(search_scenarios, 1):
                if not query:
                    continue

                logger.debug(f"{i}차 카카오 검색: {query}")
                result = self.get_coordinates_by_keyword(query)

                if result.get('found'):
                    return {
                        'found': True,
                        'search_type': f'kakao_scenario_{i}',
                        'query': query,
                        'coordinates': result,
                        'api_used': 'kakao'
                    }

            # 모든 시나리오 실패
            return {
                'found': False,
                'search_type': 'kakao_failed',
                'query': ' / '.join(search_scenarios),
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