from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
from loguru import logger
import time


class BaseMapAPI(ABC):
    """지도 API 기본 클래스"""

    def __init__(self, api_name: str):
        self.api_name = api_name
        self.api_delay = 0.2  # API 호출 간 대기시간

    @abstractmethod
    def get_coordinates_by_keyword(self, query: str) -> Dict[str, Any]:
        """키워드로 좌표 조회"""
        pass

    @abstractmethod
    def get_coordinates_by_address(self, address: str) -> Dict[str, Any]:
        """주소로 좌표 조회"""
        pass

    def clean_address_for_search(self, address: str) -> str:
        """주소를 검색용으로 정리"""
        import re

        logger.debug(f"원본 주소: {address}")

        # 기본 정리
        cleaned = address.strip()

        # 불필요한 괄호와 내용 제거
        cleaned = re.sub(r'\([^)]*\)', '', cleaned)

        # 건물명/상세주소 제거 패턴들
        patterns_to_remove = [
            r'[가-힣]*상가\s*\S*',
            r'\s+지하\d*$',
            r'\s+\d+층$',
            r'\s+[A-Z]\d*호$',
            r'\s+\d+\.\d+호$',
            r'\s+\d+호$',
        ]

        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, '', cleaned)

        # 번지만 남기기
        parts = cleaned.split()
        clean_parts = []

        for part in parts:
            if any(suffix in part for suffix in ['동', '면', '읍', '리']):
                clean_parts.append(part)
            elif re.match(r'^\d+(-\d+)?$', part):
                clean_parts.append(part)
                break
            elif not re.search(r'\d', part):
                clean_parts.append(part)
            else:
                number_match = re.match(r'^(\d+(-\d+)?)', part)
                if number_match:
                    clean_parts.append(number_match.group(1))
                    break

        result = ' '.join(clean_parts)
        logger.debug(f"정리된 주소: {result}")
        return result

    def extract_dong_from_address(self, address: str) -> str:
        """주소에서 동 정보 추출"""
        import re

        for part in address.split():
            if any(suffix in part for suffix in ['동', '면', '읍', '리']):
                return re.sub(r'\d+', '', part)  # 숫자 제거
        return ""

    def rate_limit(self):
        """API 호출 제한"""
        time.sleep(self.api_delay)

    def handle_api_error(self, response, query: str) -> Dict[str, Any]:
        """API 오류 처리"""
        logger.warning(f"{self.api_name} API 오류 - 상태코드: {response.status_code}, 쿼리: {query}")
        return {
            'found': False,
            'error': f'HTTP {response.status_code}',
            'query': query
        }