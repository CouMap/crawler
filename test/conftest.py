import pytest
from unittest.mock import patch
import os

@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """테스트 환경 설정"""
    # 테스트용 환경 변수 설정
    os.environ['DB_HOST'] = 'localhost'
    os.environ['DB_PORT'] = '3306'
    os.environ['DB_USER'] = 'test_user'
    os.environ['DB_PASSWORD'] = 'test_password'
    os.environ['DB_NAME'] = 'test_db'
    os.environ['NAVER_CLIENT_ID'] = 'test_naver_id'
    os.environ['NAVER_CLIENT_SECRET'] = 'test_naver_secret'
    os.environ['KAKAO_API_KEY'] = 'test_kakao_key'
    os.environ['HEADLESS'] = 'true'

@pytest.fixture
def mock_database():
    """Mock 데이터베이스 픽스처"""
    with patch('src.database.Database') as mock_db:
        yield mock_db

@pytest.fixture
def mock_webdriver():
    """Mock 웹드라이버 픽스처"""
    with patch('selenium.webdriver.Chrome') as mock_driver:
        yield mock_driver