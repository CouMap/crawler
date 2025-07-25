import os
from dotenv import load_dotenv

load_dotenv()

# 데이터베이스 설정
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', '3308'))
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME', 'coumap')

# 네이버 API 설정
NAVER_CLIENT_ID = os.getenv('NAVER_API_CLIENT_ID')
NAVER_CLIENT_SECRET = os.getenv('NAVER_API_CLIENT_SECRET')

# 크롤링 설정
KB_CARD_URL = 'https://m.kbcard.com/BON/DVIEW/MBAM0005'
HEADLESS = os.getenv('HEADLESS', 'true').lower() == 'true'
CRAWL_DELAY = 2.0  # 지역 간 대기시간
API_DELAY = 0.2    # API 호출 간 대기시간

# 필수 설정 검증
if not DB_USER or not DB_PASSWORD:
    raise ValueError("DB_USER와 DB_PASSWORD가 필요합니다.")

if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
    raise ValueError("NAVER_API_CLIENT_ID와 NAVER_API_CLIENT_SECRET이 필요합니다.")