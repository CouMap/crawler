import re
from typing import Dict, Optional, Tuple
from loguru import logger


class AddressParser:
    """주소 파싱 클래스"""

    # 행정구역 매핑 테이블
    PROVINCE_MAPPING = {
        '서울': '서울특별시',
        '부산': '부산광역시',
        '대구': '대구광역시',
        '인천': '인천광역시',
        '광주': '광주광역시',
        '대전': '대전광역시',
        '울산': '울산광역시',
        '세종': '세종특별자치시',
        '경기': '경기도',
        '강원': '강원도',
        '충북': '충청북도',
        '충남': '충청남도',
        '전북': '전라북도',
        '전남': '전라남도',
        '경북': '경상북도',
        '경남': '경상남도',
        '제주': '제주특별자치도'
    }

    @classmethod
    def parse_address(cls, address: str) -> Dict[str, Optional[str]]:
        """주소를 파싱하여 시/도, 시/군/구, 읍/면/동으로 분리"""
        logger.debug(f"주소 파싱 시작: {address}")

        # 주소 전처리
        cleaned_address = address.replace(',', ' ').strip()
        parts = cleaned_address.split()

        logger.debug(f"주소 분할: {parts}")

        result = {
            'province': None,
            'city': None,
            'town': None,
            'detail': None
        }

        # 1. 시/도 찾기
        result['province'] = cls._extract_province(parts)

        # 2. 시/군/구 찾기
        result['city'] = cls._extract_city(parts)

        # 3. 읍/면/동 찾기
        result['town'] = cls._extract_town(parts)

        # 4. 상세 주소 추출
        result['detail'] = cls._extract_detail(parts, result)

        logger.debug(f"파싱 결과: {result}")
        return result

    @classmethod
    def _extract_province(cls, parts: list) -> Optional[str]:
        """시/도 추출"""
        for part in parts:
            # 직접 매칭
            if part in cls.PROVINCE_MAPPING:
                province = cls.PROVINCE_MAPPING[part]
                logger.debug(f"시/도 직접 매칭: {part} → {province}")
                return province

            # 부분 매칭
            for key, value in cls.PROVINCE_MAPPING.items():
                if key in part:
                    province = value
                    logger.debug(f"시/도 부분 매칭: {part} ({key}) → {province}")
                    return province

        # 기본값 (강남구가 있으면 서울로 가정)
        address_str = ' '.join(parts)
        if '강남구' in address_str:
            logger.debug("기본값 설정: 강남구 감지 → 서울특별시")
            return '서울특별시'

        logger.warning(f"시/도를 식별할 수 없음: {parts}")
        return None

    @classmethod
    def _extract_city(cls, parts: list) -> Optional[str]:
        """시/군/구 추출"""
        for part in parts:
            if any(suffix in part for suffix in ['구', '시', '군']):
                # 시/도가 아닌 것만 (특별시, 광역시, 도 등 제외)
                if not any(province_suffix in part for province_suffix in ['특별시', '광역시', '도', '자치시', '자치도']):
                    # 특별한 경우 처리
                    if '구' in part and not part.endswith('구'):
                        # "강남구청" 같은 경우 "강남구"로 추출
                        if part.endswith('청') or part.endswith('역'):
                            city = part.replace('청', '').replace('역', '')
                            if not city.endswith('구'):
                                city += '구'
                        else:
                            city = part
                    else:
                        city = part

                    logger.debug(f"시/군/구 매칭: {part} → {city}")
                    return city

        # 기본값 (강남구가 있으면)
        address_str = ' '.join(parts)
        if '강남구' in address_str:
            logger.debug("기본값 설정: 강남구 감지 → 강남구")
            return '강남구'

        logger.warning(f"시/군/구를 식별할 수 없음: {parts}")
        return None

    @classmethod
    def _extract_town(cls, parts: list) -> Optional[str]:
        """읍/면/동 추출"""
        for part in parts:
            if any(suffix in part for suffix in ['동', '면', '읍', '리']):
                logger.debug(f"읍/면/동 매칭: {part}")
                return part

        logger.debug("읍/면/동을 찾을 수 없음")
        return None

    @classmethod
    def _extract_detail(cls, parts: list, parsed: dict) -> Optional[str]:
        """상세 주소 추출"""
        # 시/도, 시/군/구, 읍/면/동을 제외한 나머지
        excluded = [parsed['province'], parsed['city'], parsed['town']]
        detail_parts = []

        for part in parts:
            # 이미 추출된 행정구역이 아닌 경우
            if not any(excluded_item and excluded_item in part for excluded_item in excluded if excluded_item):
                detail_parts.append(part)

        if detail_parts:
            detail = ' '.join(detail_parts)
            logger.debug(f"상세 주소: {detail}")
            return detail

        return None

    @classmethod
    def normalize_address(cls, address: str) -> str:
        """주소 정규화"""
        # 기본 정리
        normalized = address.strip()

        # 특수문자 정리 (괄호 제거)
        normalized = re.sub(r'\([^)]*\)', '', normalized)
        normalized = normalized.replace(',', ' ')

        # 연속된 공백을 단일 공백으로 변경
        normalized = re.sub(r'\s+', ' ', normalized)

        return normalized.strip()

    @classmethod
    def extract_building_number(cls, address: str) -> Optional[str]:
        """건물 번호 추출"""
        # 번지 패턴 찾기
        patterns = [
            r'\b(\d+(-\d+)?)\b',  # 123 또는 123-45
            r'\b(\d+번지)\b',  # 123번지
            r'\b(\d+번)\b'  # 123번
        ]

        for pattern in patterns:
            match = re.search(pattern, address)
            if match:
                return match.group(1)

        return None

    @classmethod
    def is_valid_address(cls, address: str) -> bool:
        """주소 유효성 검사"""
        if not address or len(address.strip()) < 5:
            return False

        parsed = cls.parse_address(address)

        # 최소한 시/도와 시/군/구는 있어야 함
        return parsed['province'] is not None and parsed['city'] is not None

    @classmethod
    def format_address(cls, province: str, city: str, town: str = None, detail: str = None) -> str:
        """주소 포맷팅"""
        parts = [province, city]

        if town:
            parts.append(town)

        if detail:
            parts.append(detail)

        return ' '.join(parts)

    @classmethod
    def compare_addresses(cls, addr1: str, addr2: str) -> float:
        """두 주소의 유사도 계산 (0.0 ~ 1.0)"""
        parsed1 = cls.parse_address(addr1)
        parsed2 = cls.parse_address(addr2)

        score = 0.0
        total_weight = 0.0

        # 시/도 비교 (가중치: 3)
        if parsed1['province'] and parsed2['province']:
            if parsed1['province'] == parsed2['province']:
                score += 3.0
            total_weight += 3.0

        # 시/군/구 비교 (가중치: 3)
        if parsed1['city'] and parsed2['city']:
            if parsed1['city'] == parsed2['city']:
                score += 3.0
            total_weight += 3.0

        # 읍/면/동 비교 (가중치: 2)
        if parsed1['town'] and parsed2['town']:
            if parsed1['town'] == parsed2['town']:
                score += 2.0
            elif cls._similar_town(parsed1['town'], parsed2['town']):
                score += 1.0
            total_weight += 2.0

        # 상세주소 비교 (가중치: 1)
        if parsed1['detail'] and parsed2['detail']:
            detail_similarity = cls._calculate_string_similarity(
                parsed1['detail'], parsed2['detail']
            )
            score += detail_similarity
            total_weight += 1.0

        return score / total_weight if total_weight > 0 else 0.0

    @classmethod
    def _similar_town(cls, town1: str, town2: str) -> bool:
        """동명 유사성 검사"""
        clean1 = re.sub(r'\d+', '', town1)
        clean2 = re.sub(r'\d+', '', town2)

        return clean1 == clean2

    @classmethod
    def _calculate_string_similarity(cls, str1: str, str2: str) -> float:
        """문자열 유사도 계산 (간단한 Jaccard 유사도)"""
        if not str1 or not str2:
            return 0.0

        set1 = set(str1.split())
        set2 = set(str2.split())

        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))

        return intersection / union if union > 0 else 0.0