import requests
import time
import logging
from config import *

logger = logging.getLogger(__name__)


class NaverMapAPI:
    def __init__(self):
        self.headers = {
            'X-NCP-APIGW-API-KEY-ID': NAVER_CLIENT_ID,
            'X-NCP-APIGW-API-KEY': NAVER_CLIENT_SECRET,
            'Accept': 'application/json'
        }
        self.geocoding_url = 'https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode'

    def get_coordinates(self, address):
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
                if data.get('addresses'):
                    addr = data['addresses'][0]
                    return {
                        'latitude': float(addr['y']),
                        'longitude': float(addr['x'])
                    }

            logger.warning(f"좌표 조회 실패: {address}")
            return None

        except Exception as e:
            logger.error(f"네이버 API 오류: {e}")
            return None
        finally:
            time.sleep(API_DELAY)  # API 호출 제한