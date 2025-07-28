import sys
import argparse
from datetime import datetime
from loguru import logger

from src.crawler import Crawler
from src.map_api import get_map_api
from src.database import Database
from src.models import Base


def setup_database():
    """데이터베이스 초기화"""
    try:
        db = Database()
        Base.metadata.create_all(db.engine)
        logger.info("데이터베이스 테이블 생성 완료")
        db.close()
        return True
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")
        return False


def test_map_apis():
    """지도 API 테스트"""
    logger.info("지도 API 테스트 시작...")

    try:
        map_api = get_map_api()

        test_cases = [
            ("우성", "정육점", "서울 강남구 개포동"),
            ("스타벅스", "카페", "서울 강남구 개포동 186"),
            ("맥도날드", "패스트푸드", "서울 강남구 역삼동 123"),
            ("존재하지않는가게", "기타", "서울 강남구 개포동 999")
        ]

        logger.info("지도 API 테스트 케이스:")

        for i, (name, category, address) in enumerate(test_cases, 1):
            logger.info(f"[{i}] 테스트: {name}")
            result = map_api.search_location(name, category, address)

            if result['found']:
                logger.success(f"검색 성공 - API: {result['api_used'].upper()}")
                logger.info(f"   검색 타입: {result['search_type']}")
                logger.info(f"   검색어: {result['query']}")
                coords = result['coordinates']
                logger.info(f"   좌표: ({coords['latitude']}, {coords['longitude']})")
                if 'place_name' in coords:
                    logger.info(f"   장소명: {coords['place_name']}")
            else:
                logger.error(f"검색 실패 - {result['search_type']}")
                logger.info(f"   시도한 검색: {result['query']}")

        return True

    except Exception as e:
        logger.error(f"지도 API 테스트 실패: {e}")
        return False


def run_crawler(mode: str, province: str = None, district: str = None, dong: str = None):
    """크롤러 실행"""
    logger.info(f"크롤러 모드: {mode}")
    logger.info(f"대상 지역: {province} {district or ''} {dong or ''}")

    crawler = None

    try:
        # 크롤러 초기화 - 모드에 따라 복구 기능 설정
        logger.info("크롤러 초기화 중...")

        # test 모드는 복구 기능 비활성화
        enable_recovery = mode != "test"
        crawler = Crawler(enable_recovery=enable_recovery)

        if enable_recovery:
            logger.info("복구 기능 활성화로 크롤러 초기화")
        else:
            logger.info("복구 기능 비활성화로 크롤러 초기화 (test 모드)")

        # 드라이버 설정
        logger.info("드라이버 설정 중...")
        crawler.setup_driver()
        logger.info("드라이버 설정 완료")

        # 크롤링 실행
        start_time = datetime.now()
        logger.info(f"크롤링 시작 시간: {start_time}")

        if mode == "full_crawl":
            logger.info("전국 크롤링 시작...")
            stats = crawler.crawl_all_regions()
        elif mode == "single_region":
            logger.info(f"단일 지역 크롤링: {province} {district} {dong}")
            stats = crawler.crawl_single_region(province, district, dong)
        elif mode == "test":
            logger.info("테스트 크롤링 시작 (복구 기능 비활성화)...")
            # test.py와 동일한 방식으로 테스트 실행
            stats = crawler.crawl_single_region("서울", "강남구", "일원본동")
        else:
            logger.error(f"알 수 없는 모드: {mode}")
            return False

        end_time = datetime.now()
        duration = end_time - start_time

        # 복구 통계 출력
        recovery_status = crawler.get_recovery_status()
        if recovery_status['recovery_attempts_made'] > 0:
            logger.info(f"세션 복구 시도: {recovery_status['recovery_attempts_made']}회")

        # 결과 출력
        logger.success("크롤링 완료!")
        logger.info(f"소요 시간: {duration}")
        logger.info(f"크롤링 지역: {stats['regions_crawled']}개")
        logger.info(f"발견 가맹점: {stats['total_stores']}개")
        logger.info(f"저장 가맹점: {stats['total_saved']}개")
        logger.info(f"API 성공: {stats['api_success']}개")
        logger.info(f"API 실패: {stats['api_failed']}개")

        # 통계가 있는 경우에만 요약 저장
        if stats['regions_crawled'] > 0:
            # 요약 저장
            region_name = f"{province or '전체'} {district or ''} {dong or ''}".strip()
            summary_file = crawler.save_summary(region_name)
            logger.info(f"요약 저장: {summary_file}")

        # 최소한의 성공 기준
        return stats['regions_crawled'] > 0 or stats['total_stores'] > 0

    except Exception as e:
        logger.error(f"크롤링 실행 실패: {e}")

        # 상세한 오류 정보 출력
        import traceback
        logger.error(f"상세 오류 정보:\n{traceback.format_exc()}")

        return False
    finally:
        if crawler:
            logger.info("크롤러 정리 중...")
            crawler.cleanup()
            logger.info("크롤러 정리 완료")


def run_crawler_with_recovery_control(mode: str, province: str = None, district: str = None,
                                      dong: str = None, recovery_enabled: bool = True):
    """복구 기능을 직접 제어하는 크롤러 실행"""
    logger.info(f"크롤러 모드: {mode} (복구 기능: {'활성화' if recovery_enabled else '비활성화'})")
    logger.info(f"대상 지역: {province} {district or ''} {dong or ''}")

    crawler = None

    try:
        # 크롤러 초기화 - 복구 기능 직접 제어
        logger.info("크롤러 초기화 중...")
        crawler = Crawler(enable_recovery=recovery_enabled)

        # 드라이버 설정
        logger.info("드라이버 설정 중...")
        crawler.setup_driver()
        logger.info("드라이버 설정 완료")

        # 크롤링 실행
        start_time = datetime.now()
        logger.info(f"크롤링 시작 시간: {start_time}")

        if mode == "full_crawl":
            logger.info("전국 크롤링 시작...")
            stats = crawler.crawl_all_regions()
        elif mode == "single_region":
            logger.info(f"단일 지역 크롤링: {province} {district} {dong}")
            stats = crawler.crawl_single_region(province, district, dong)
        elif mode == "test":
            logger.info("테스트 크롤링 시작...")
            stats = crawler.crawl_single_region("서울", "강남구", "일원본동")
        else:
            logger.error(f"알 수 없는 모드: {mode}")
            return False

        end_time = datetime.now()
        duration = end_time - start_time

        # 복구 통계 출력
        recovery_status = crawler.get_recovery_status()
        if recovery_status['recovery_attempts_made'] > 0:
            logger.info(f"세션 복구 시도: {recovery_status['recovery_attempts_made']}회")

        # 결과 출력
        logger.success("크롤링 완료!")
        logger.info(f"소요 시간: {duration}")
        logger.info(f"크롤링 지역: {stats['regions_crawled']}개")
        logger.info(f"발견 가맹점: {stats['total_stores']}개")
        logger.info(f"저장 가맹점: {stats['total_saved']}개")
        logger.info(f"API 성공: {stats['api_success']}개")
        logger.info(f"API 실패: {stats['api_failed']}개")

        # 통계가 있는 경우에만 요약 저장
        if stats['regions_crawled'] > 0:
            region_name = f"{province or '전체'} {district or ''} {dong or ''}".strip()
            summary_file = crawler.save_summary(region_name)
            logger.info(f"요약 저장: {summary_file}")

        return stats['regions_crawled'] > 0 or stats['total_stores'] > 0

    except Exception as e:
        logger.error(f"크롤링 실행 실패: {e}")

        import traceback
        logger.error(f"상세 오류 정보:\n{traceback.format_exc()}")

        return False
    finally:
        if crawler:
            logger.info("크롤러 정리 중...")
            crawler.cleanup()
            logger.info("크롤러 정리 완료")


def show_database_stats():
    """데이터베이스 통계 출력"""
    try:
        db = Database()
        stats = db.get_statistics()

        logger.info("데이터베이스 통계:")
        logger.info(f"총 가맹점: {stats['total_stores']}개")
        logger.info(f"좌표 보유: {stats['stores_with_coordinates']}개")
        logger.info(f"성공률: {stats['success_rate']}%")

        if stats.get('stores_by_category_str'):
            logger.info("가맹점 카테고리별 (문자열):")
            for store_type, count in stats['stores_by_category_str'].items():
                logger.info(f"  {store_type}: {count}개")

        if stats.get('stores_by_category_obj'):
            logger.info("가맹점 카테고리별 (객체):")
            for store_type, count in stats['stores_by_category_obj'].items():
                logger.info(f"  {store_type}: {count}개")

        db.close()
        return True

    except Exception as e:
        logger.error(f"데이터베이스 통계 조회 실패: {e}")
        return False


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='KB카드 가맹점 크롤러')
    parser.add_argument('--mode', choices=['test', 'single_region', 'full_crawl', 'map_test', 'stats'],
                        default='test', help='실행 모드')
    parser.add_argument('--province', help='시/도명 (예: 서울, 부산)')
    parser.add_argument('--district', help='시/군/구명 (예: 강남구)')
    parser.add_argument('--dong', help='읍/면/동명 (예: 개포동)')
    parser.add_argument('--setup-db', action='store_true', help='데이터베이스 초기화')
    parser.add_argument('--verbose', '-v', action='store_true', help='상세 로그 출력')
    parser.add_argument('--no-recovery', action='store_true', help='세션 복구 기능 비활성화')
    parser.add_argument('--force-recovery', action='store_true', help='모든 모드에서 세션 복구 기능 강제 활성화')

    args = parser.parse_args()

    # 로깅 레벨 설정
    logger.remove()  # 기존 핸들러 제거

    if args.verbose:
        logger.add(sys.stderr, level="DEBUG",
                   format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>")
    else:
        logger.add(sys.stderr, level="INFO",
                   format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")

    logger.info("=" * 60)
    logger.info("KB카드 가맹점 크롤러")
    logger.info("=" * 60)

    # 환경 정보 출력
    logger.info(f"실행 모드: {args.mode}")
    if args.verbose:
        logger.info("상세 로그 모드 활성화")
    if args.no_recovery:
        logger.info("세션 복구 기능 비활성화")
    if args.force_recovery:
        logger.info("세션 복구 기능 강제 활성화")

    # 데이터베이스 초기화
    if args.setup_db or args.mode != 'map_test':
        logger.info("데이터베이스 초기화 중...")
        if not setup_database():
            logger.error("데이터베이스 초기화 실패")
            sys.exit(1)
        logger.info("데이터베이스 초기화 완료")

    # 모드별 실행
    success = False

    if args.mode == 'map_test':
        # 지도 API 테스트
        success = test_map_apis()

    elif args.mode == 'stats':
        # 데이터베이스 통계
        success = show_database_stats()

    elif args.mode == 'test':
        # 테스트 크롤링
        logger.info("테스트 모드: 서울 강남구 일원본동 크롤링")

        # 복구 기능 설정 결정
        if args.force_recovery:
            logger.info("강제 복구 모드로 테스트 실행")
            success = run_crawler_with_recovery_control('test', recovery_enabled=True)
        elif args.no_recovery:
            logger.info("복구 기능 비활성화로 테스트 실행")
            success = run_crawler_with_recovery_control('test', recovery_enabled=False)
        else:
            logger.info("기본 설정(복구 비활성화)으로 테스트 실행")
            success = run_crawler('test')

    elif args.mode == 'single_region':
        # 단일 지역 크롤링
        if not args.province:
            logger.error("단일 지역 모드에서는 --province가 필요합니다")
            sys.exit(1)

        logger.info(f"단일 지역 크롤링: {args.province} {args.district or ''} {args.dong or ''}")

        # 복구 기능 설정 결정
        if args.no_recovery:
            success = run_crawler_with_recovery_control('single_region', args.province, args.district, args.dong,
                                                        recovery_enabled=False)
        elif args.force_recovery:
            success = run_crawler_with_recovery_control('single_region', args.province, args.district, args.dong,
                                                        recovery_enabled=True)
        else:
            success = run_crawler('single_region', args.province, args.district, args.dong)

    elif args.mode == 'full_crawl':
        # 전국 크롤링
        logger.warning("전국 크롤링을 시작합니다. 이 작업은 수 시간이 소요될 수 있습니다.")

        # GitHub Actions 환경이 아닌 경우 확인 요청
        import os
        if os.getenv('GITHUB_ACTIONS') != 'true':
            response = input("계속하시겠습니까? (y/N): ")
            if response.lower() != 'y':
                logger.info("전국 크롤링이 취소되었습니다.")
                sys.exit(0)

        # 복구 기능 설정 결정
        if args.no_recovery:
            logger.warning("전국 크롤링에서 복구 기능을 비활성화하는 것은 권장되지 않습니다.")
            success = run_crawler_with_recovery_control('full_crawl', recovery_enabled=False)
        else:
            success = run_crawler('full_crawl')

    # 최종 데이터베이스 통계 출력
    if success and args.mode in ['test', 'single_region', 'full_crawl']:
        logger.info("\n" + "=" * 40)
        logger.info("최종 통계")
        logger.info("=" * 40)
        show_database_stats()

    # 종료
    if success:
        logger.success("작업이 성공적으로 완료되었습니다!")
        sys.exit(0)
    else:
        logger.error("작업이 실패했습니다.")
        sys.exit(1)


if __name__ == "__main__":
    main()