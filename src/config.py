import os
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

# 필요한 디렉토리 생성
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# 환경 변수 로드
load_dotenv(PROJECT_ROOT / ".env")


# 데이터베이스 설정
class DatabaseConfig:
    HOST = os.getenv('DB_HOST', 'localhost')
    PORT = int(os.getenv('DB_PORT', '3308'))
    USER = os.getenv('DB_USER')
    PASSWORD = os.getenv('DB_PASSWORD')
    NAME = os.getenv('DB_NAME', 'coumap')

    @property
    def url(self):
        return f"mysql+pymysql://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.NAME}?charset=utf8mb4"


# API 설정
class APIConfig:
    # 네이버 API 설정
    NAVER_CLIENT_ID = os.getenv('NAVER_CLIENT_ID')
    NAVER_CLIENT_SECRET = os.getenv('NAVER_CLIENT_SECRET')

    # 카카오 API 설정
    KAKAO_API_KEY = os.getenv('KAKAO_API_KEY')


# 크롤링 설정
class CrawlerConfig:
    KB_CARD_URL = 'https://m.kbcard.com/BON/DVIEW/MBAM0005'

    # 디버깅을 위해 기본값을 False로 변경
    HEADLESS = os.getenv('HEADLESS', 'false').lower() == 'true'

    # 대기시간을 더 길게 설정
    CRAWL_DELAY = float(os.getenv('CRAWL_DELAY', '8.0'))
    API_DELAY = float(os.getenv('API_DELAY', '1.0'))

    # 사용자 에이전트 설정
    USER_AGENT = os.getenv('USER_AGENT',
                           'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15'
                           )

    # 크롬 드라이버 옵션 - 더 안정적으로 설정
    CHROME_OPTIONS = [
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--window-size=1200,800',
        '--disable-web-security',
        '--disable-features=VizDisplayCompositor',
        '--disable-blink-features=AutomationControlled',  # 자동화 감지 방지
        '--disable-extensions',
        '--no-first-run',
        '--disable-default-apps'
    ]


# 로깅 설정
class LoggingConfig:
    LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    FILE_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name} | {message}"

    @staticmethod
    def get_log_file_path(name: str) -> Path:
        return LOGS_DIR / f"{name}_{os.getenv('GITHUB_RUN_ID', 'local')}.log"


# 설정 검증 - 개발 환경에서는 완화
def validate_config():
    """필수 설정 검증"""
    errors = []

    # GitHub Actions 환경이 아닌 경우 API 키 검증 완화
    if os.getenv('GITHUB_ACTIONS') == 'true':
        db_config = DatabaseConfig()
        if not db_config.USER or not db_config.PASSWORD:
            errors.append("DB_USER와 DB_PASSWORD가 필요합니다.")

        api_config = APIConfig()
        if not api_config.NAVER_CLIENT_ID or not api_config.NAVER_CLIENT_SECRET:
            errors.append("NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET이 필요합니다.")

        if not api_config.KAKAO_API_KEY:
            errors.append("KAKAO_API_KEY가 필요합니다.")

        if errors:
            raise ValueError("\n".join(errors))


# 전역 설정 인스턴스
db_config = DatabaseConfig()
api_config = APIConfig()
crawler_config = CrawlerConfig()
logging_config = LoggingConfig()

# 설정 검증
validate_config()