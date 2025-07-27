import csv
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from loguru import logger

from ..config import DATA_DIR


class CSVHandler:
    """CSV 파일 처리 클래스"""

    @staticmethod
    def save_failed_stores(failed_stores: List[Dict[str, Any]],
                           filename: str = None) -> Path:
        """검색 실패한 가맹점들을 CSV로 저장 (덮어쓰기)"""
        if not filename:
            filename = "failed_stores.csv"  # 고정된 파일명 사용

        filepath = DATA_DIR / filename

        try:
            fieldnames = [
                'store_name', 'address', 'category', 'phone', 'store_type',
                'distance', 'search_attempts', 'region_info', 'failed_apis',
                'timestamp', 'error_reason'
            ]

            # 기존 데이터 읽기 (있다면)
            existing_data = []
            if filepath.exists():
                existing_data = CSVHandler.read_csv(filepath)
                logger.info(f"기존 실패 데이터 {len(existing_data)}개 발견")

            # 새 데이터 추가
            all_data = existing_data + failed_stores

            # 중복 제거 (store_name + address 기준)
            seen = set()
            unique_data = []
            for store in all_data:
                key = f"{store.get('store_name', '')}-{store.get('address', '')}"
                if key not in seen:
                    seen.add(key)
                    unique_data.append(store)

            # 파일 덮어쓰기
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for store in unique_data:
                    # 누락된 필드 기본값 설정
                    row = {field: store.get(field, '') for field in fieldnames}
                    if not row['timestamp']:
                        row['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    writer.writerow(row)

            logger.info(f"실패 가맹점 CSV 저장 완료: {filepath}")
            logger.info(f"총 저장된 가맹점 수: {len(unique_data)}개 (중복 제거 후)")

            return filepath

        except Exception as e:
            logger.error(f"CSV 저장 실패: {e}")
            raise

    @staticmethod
    def save_crawling_summary(summary_data: Dict[str, Any],
                              filename: str = None) -> Path:
        """크롤링 요약 정보를 CSV로 저장 (덮어쓰기)"""
        if not filename:
            filename = "crawling_summary.csv"  # 고정된 파일명 사용

        filepath = DATA_DIR / filename

        try:
            fieldnames = [
                'region', 'total_found', 'total_saved', 'naver_success',
                'kakao_success', 'api_failed', 'duplicates', 'success_rate',
                'crawl_time', 'timestamp'
            ]

            # 기존 데이터 읽기 (있다면)
            existing_data = []
            if filepath.exists():
                existing_data = CSVHandler.read_csv(filepath)
                logger.info(f"기존 요약 데이터 {len(existing_data)}개 발견")

            # 새 데이터 처리
            if isinstance(summary_data, list):
                new_data = summary_data
            else:
                new_data = [summary_data]

            # 기존 데이터와 병합
            all_data = existing_data + new_data

            # 같은 지역의 최신 데이터만 유지
            region_data = {}
            for data in all_data:
                region = data.get('region', '알수없음')
                timestamp = data.get('timestamp', '')

                # 더 최신 데이터로 업데이트
                if region not in region_data or timestamp > region_data[region].get('timestamp', ''):
                    region_data[region] = data

            # 파일 덮어쓰기
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                # 지역별로 정렬해서 저장
                sorted_data = sorted(region_data.values(), key=lambda x: x.get('region', ''))
                for data in sorted_data:
                    # 누락된 필드 기본값 설정
                    row = {field: data.get(field, '') for field in fieldnames}
                    writer.writerow(row)

            logger.info(f"크롤링 요약 CSV 저장 완료: {filepath}")
            logger.info(f"저장된 지역 수: {len(region_data)}개")
            return filepath

        except Exception as e:
            logger.error(f"요약 CSV 저장 실패: {e}")
            raise

    @staticmethod
    def save_stores_export(stores: List[Dict[str, Any]],
                           filename: str = None) -> Path:
        """가맹점 데이터를 CSV로 내보내기 (덮어쓰기)"""
        if not filename:
            filename = "stores_export.csv"  # 고정된 파일명 사용

        filepath = DATA_DIR / filename

        try:
            fieldnames = [
                'id', 'name', 'category', 'address', 'phone', 'latitude',
                'longitude', 'store_type', 'region', 'created_at'
            ]

            # 파일 덮어쓰기
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(stores)

            logger.info(f"가맹점 데이터 CSV 내보내기 완료: {filepath}")
            logger.info(f"내보낸 가맹점 수: {len(stores)}개")

            return filepath

        except Exception as e:
            logger.error(f"가맹점 CSV 내보내기 실패: {e}")
            raise

    @staticmethod
    def read_csv(filepath: Path) -> List[Dict[str, Any]]:
        """CSV 파일 읽기"""
        try:
            data = []
            with open(filepath, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                data = list(reader)

            logger.debug(f"CSV 파일 읽기 완료: {filepath} ({len(data)}행)")
            return data

        except Exception as e:
            logger.error(f"CSV 파일 읽기 실패: {e}")
            return []

    @staticmethod
    def get_csv_files(pattern: str = "*.csv") -> List[Path]:
        """데이터 디렉토리에서 CSV 파일 목록 조회"""
        try:
            csv_files = list(DATA_DIR.glob(pattern))
            csv_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return csv_files
        except Exception as e:
            logger.error(f"CSV 파일 목록 조회 실패: {e}")
            return []

    @staticmethod
    def cleanup_old_files(days: int = 30, pattern: str = "*.csv") -> int:
        """오래된 CSV 파일 정리 (백업 파일만)"""
        try:
            from datetime import timedelta

            cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
            deleted_count = 0

            # 백업 파일만 삭제 (기본 파일은 유지)
            protected_files = ['failed_stores.csv', 'crawling_summary.csv', 'stores_export.csv']

            for filepath in DATA_DIR.glob(pattern):
                if (filepath.name not in protected_files and
                        filepath.stat().st_mtime < cutoff_time):
                    filepath.unlink()
                    deleted_count += 1
                    logger.debug(f"오래된 파일 삭제: {filepath}")

            if deleted_count > 0:
                logger.info(f"오래된 CSV 파일 {deleted_count}개 삭제 완료")

            return deleted_count

        except Exception as e:
            logger.error(f"CSV 파일 정리 실패: {e}")
            return 0

    @staticmethod
    def validate_csv_data(data: List[Dict[str, Any]],
                          required_fields: List[str]) -> bool:
        """CSV 데이터 유효성 검사"""
        if not data:
            logger.warning("CSV 데이터가 비어있음")
            return False

        missing_fields = []
        for field in required_fields:
            if field not in data[0]:
                missing_fields.append(field)

        if missing_fields:
            logger.error(f"필수 필드 누락: {missing_fields}")
            return False

        logger.info("CSV 데이터 유효성 검사 통과")
        return True

    @staticmethod
    def create_backup(filepath: Path) -> Path:
        """CSV 파일 백업 생성"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"{filepath.stem}_backup_{timestamp}{filepath.suffix}"
            backup_path = filepath.parent / backup_name

            import shutil
            shutil.copy2(filepath, backup_path)

            logger.info(f"백업 파일 생성: {backup_path}")
            return backup_path

        except Exception as e:
            logger.error(f"백업 생성 실패: {e}")
            raise