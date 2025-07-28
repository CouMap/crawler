import time
from typing import Dict, List, Any, Optional
from loguru import logger

from .base_crawler import BaseCrawler
from ..config import crawler_config


class Crawler(BaseCrawler):
    """KB카드 가맹점 크롤러 - 선택적 복구 기능"""

    def __init__(self, enable_recovery: bool = True):
        super().__init__()
        self.location_agreed = False
        self.current_province = None
        self.current_district = None

        # 복구 기능 설정
        if not enable_recovery:
            self.disable_recovery()
            logger.info("복구 기능 비활성화로 초기화")
        else:
            logger.info("복구 기능 활성화로 초기화")

    def access_website(self) -> bool:
        """KB카드 사이트 접근 및 초기 설정"""

        def _access_website_impl():
            logger.info("KB카드 사이트 접근")
            self.driver.get(crawler_config.KB_CARD_URL)
            self.save_crawling_state(step='site_access')

            # 고정 대기시간 사용
            time.sleep(5)

            # 위치정보 동의 팝업 처리
            if not self.location_agreed:
                self.handle_location_agreement()

            # 필터 팝업 열기
            self.open_filter_popup()

            # 조건 설정
            self.set_search_conditions()

            logger.info("사이트 접근 및 설정 완료")
            self.save_crawling_state(step='site_ready')
            return True

        try:
            if self.recovery_enabled:
                return self.execute_with_recovery(
                    _access_website_impl,
                    description="웹사이트 접근 및 설정"
                )
            else:
                return self.execute_simple(
                    _access_website_impl,
                    description="웹사이트 접근 및 설정"
                )
        except Exception as e:
            logger.error(f"사이트 접근 및 설정 실패: {e}")
            return False

    def handle_location_agreement(self):
        """위치정보 동의 팝업 처리"""

        def _handle_location_agreement_impl():
            logger.debug("위치정보 동의 팝업 확인 중...")

            script = """
            // 위치정보 동의 팝업 처리
            var agreePopup = document.getElementById('agreePopup');
            if (agreePopup && agreePopup.style.display !== 'none') {
                console.log('위치정보 동의 팝업 발견');

                // 체크박스 클릭
                var checkbox = document.getElementById('chkbox2');
                if (checkbox) {
                    checkbox.click();
                    console.log('체크박스 클릭');
                }

                // 동의 버튼 클릭 (1초 후)
                setTimeout(function() {
                    chkAgree();
                    console.log('동의 버튼 클릭');
                }, 1000);

                return 'agreement_processed';
            }
            return 'no_popup';
            """

            result = self.driver.execute_script(script)

            if result == 'agreement_processed':
                logger.info("위치정보 동의 팝업 처리 완료")
                self.location_agreed = True
                time.sleep(3)
            else:
                logger.debug("위치정보 동의 팝업 없음")
                self.location_agreed = True

        try:
            if self.recovery_enabled:
                self.execute_with_recovery(
                    _handle_location_agreement_impl,
                    description="위치정보 동의 처리"
                )
            else:
                self.execute_simple(
                    _handle_location_agreement_impl,
                    description="위치정보 동의 처리"
                )
        except Exception as e:
            logger.error(f"위치정보 동의 처리 실패: {e}")

    def open_filter_popup(self):
        """필터 팝업 열기"""

        def _open_filter_popup_impl():
            logger.debug("필터 팝업 열기 시도...")

            script = """
            console.log('필터 팝업 열기 시작');

            // 조회조건 버튼 클릭
            var filterBtn = document.querySelector('a[href="#filterPopup"]');
            if (filterBtn) {
                filterBtn.click();
                console.log('필터 버튼 클릭 완료');
                return 'filter_opened';
            } else {
                console.log('필터 버튼을 찾을 수 없음');
                return 'filter_button_not_found';
            }
            """

            result = self.driver.execute_script(script)

            if result == 'filter_opened':
                logger.info("필터 팝업 열기 완료")
            else:
                raise Exception(f"필터 팝업 열기 실패: {result}")

            time.sleep(3)

        try:
            if self.recovery_enabled:
                self.execute_with_recovery(
                    _open_filter_popup_impl,
                    description="필터 팝업 열기"
                )
            else:
                self.execute_simple(
                    _open_filter_popup_impl,
                    description="필터 팝업 열기"
                )
        except Exception as e:
            logger.error(f"필터 팝업 열기 실패: {e}")

    def set_search_conditions(self):
        """검색 조건 설정"""

        def _set_search_conditions_impl():
            logger.debug("검색 조건 설정 중...")

            script = """
            console.log('검색 조건 설정 시작');

            // 1. 사용처 선택 - 기본으로 소비쿠폰이 체크되어 있으므로 그대로 사용
            console.log('사용처: 소비쿠폰 선택됨 (기본값)');

            // 2. 검색반경 - 500m (기본 선택되어 있음)
            var radius500 = document.getElementById('radiusRdo2');
            if (radius500) {
                radius500.checked = true;
                radius500.closest('.radio-box').classList.add('checked');
                console.log('검색반경: 500m 선택');
            }

            // 3. 위치 - 지역선택으로 변경
            var locationRadio = document.getElementById('locationRdo2');
            if (locationRadio) {
                locationRadio.click();
                locationRadio.checked = true;
                // 기존 선택 해제
                document.querySelectorAll('#locationType .radio-box').forEach(function(box) {
                    box.classList.remove('checked');
                });
                locationRadio.closest('.radio-box').classList.add('checked');
                console.log('위치: 지역선택 선택');
            }

            // 4. 지역선택 버튼 클릭하여 지역 설정 팝업 열기
            setTimeout(function() {
                var areaBtn = document.querySelector('a[data-bs="selBsArea"]');
                if (areaBtn) {
                    areaBtn.click();
                    console.log('지역선택 버튼 클릭');
                }
            }, 1000);

            return 'conditions_set';
            """

            result = self.driver.execute_script(script)
            logger.info("검색 조건 설정 완료")
            time.sleep(3)

        try:
            if self.recovery_enabled:
                self.execute_with_recovery(
                    _set_search_conditions_impl,
                    description="검색 조건 설정"
                )
            else:
                self.execute_simple(
                    _set_search_conditions_impl,
                    description="검색 조건 설정"
                )
        except Exception as e:
            logger.error(f"검색 조건 설정 실패: {e}")

    def get_all_regions_from_site(self) -> List[Dict[str, str]]:
        """사이트에서 모든 지역 정보 추출"""

        def _get_all_regions_impl():
            logger.debug("사이트에서 지역 정보 추출 중...")

            script = """
            var provinces = [];
            var areaSelect = document.querySelector('select[data-gub="Area"]');

            if (areaSelect) {
                Array.from(areaSelect.options).forEach(function(option, index) {
                    if (index > 0 && option.value) {
                        provinces.push({
                            value: option.value,
                            name: option.text.trim()
                        });
                    }
                });
            }

            console.log('추출된 시/도 수:', provinces.length);

            return {
                provinces: provinces,
                success: true
            };
            """

            region_data = self.driver.execute_script(script)

            if region_data['success']:
                logger.info(f"시/도 {len(region_data['provinces'])}개 추출 완료")
                return region_data['provinces']
            else:
                raise Exception("지역 정보 추출 실패")

        try:
            if self.recovery_enabled:
                return self.execute_with_recovery(
                    _get_all_regions_impl,
                    description="지역 정보 추출"
                )
            else:
                return self.execute_simple(
                    _get_all_regions_impl,
                    description="지역 정보 추출"
                )
        except Exception as e:
            logger.error(f"지역 정보 추출 오류: {e}")
            return []

    def get_districts_for_province(self, province_value: str) -> List[Dict[str, str]]:
        """특정 시/도의 시/군/구 목록 가져오기"""

        def _get_districts_impl():
            logger.debug("시/군/구 목록 가져오는 중...")

            # 시/도 선택
            script = f"""
            var areaSelect = document.querySelector('select[data-gub="Area"]');
            if (areaSelect) {{
                areaSelect.value = '{province_value}';

                if (typeof setArea2 === 'function') {{
                    setArea2('{province_value}');
                }}

                var selectedOption = areaSelect.options[areaSelect.selectedIndex];
                var selectTarget = document.querySelector('.js-select_target[pop-name="sel-0000344"]');
                if (selectTarget && selectedOption) {{
                    selectTarget.textContent = selectedOption.text;
                }}

                console.log('시/도 선택:', selectedOption ? selectedOption.text : 'unknown');
            }}

            return 'province_selected';
            """

            self.driver.execute_script(script)
            time.sleep(3)

            # 시/군/구 목록 가져오기
            districts_script = """
            var districts = [];
            var districtTabs = document.querySelectorAll('#areaDepth2 li a');

            districtTabs.forEach(function(tab, index) {
                var value = tab.getAttribute('data-value');
                var name = tab.textContent.trim();
                if (value && name) {
                    districts.push({
                        value: value,
                        name: name
                    });
                }
            });

            console.log('시/군/구 수:', districts.length);
            return districts;
            """

            districts = self.driver.execute_script(districts_script)
            logger.debug(f"시/군/구 {len(districts)}개 발견")
            return districts

        try:
            self.save_crawling_state(province=province_value, step='getting_districts')

            if self.recovery_enabled:
                return self.execute_with_recovery(
                    _get_districts_impl,
                    description=f"시/군/구 목록 조회 ({province_value})"
                )
            else:
                return self.execute_simple(
                    _get_districts_impl,
                    description=f"시/군/구 목록 조회 ({province_value})"
                )
        except Exception as e:
            logger.error(f"시/군/구 추출 오류: {e}")
            return []

    def get_dongs_for_district(self, district_value: str) -> List[Dict[str, Any]]:
        """특정 시/군/구의 읍/면/동 목록 가져오기"""

        def _get_dongs_impl():
            logger.debug("읍/면/동 목록 가져오는 중...")

            # 시/군/구 선택
            script = f"""
            var districtTab = document.querySelector('#areaDepth2 li a[data-value="{district_value}"]');
            if (districtTab) {{
                document.querySelectorAll('#areaDepth2 li').forEach(function(li) {{
                    li.classList.remove('on');
                    li.querySelector('a').removeAttribute('title');
                }});

                districtTab.closest('li').classList.add('on');
                districtTab.setAttribute('title', '선택됨');
                districtTab.click();

                if (typeof setArea3 === 'function') {{
                    setArea3('{district_value}');
                }}

                console.log('시/군/구 선택 완료:', districtTab.textContent);
            }}

            return 'district_selected';
            """

            self.driver.execute_script(script)
            time.sleep(3)

            # 읍/면/동 목록 가져오기
            dongs_script = """
            var dongs = [];
            var dongTabs = document.querySelectorAll('#areaDepth3 li a');

            dongTabs.forEach(function(tab, index) {
                var name = tab.textContent.trim();
                if (name) {
                    dongs.push({
                        name: name,
                        index: index
                    });
                }
            });

            console.log('읍/면/동 수:', dongs.length);
            return dongs;
            """

            dongs = self.driver.execute_script(dongs_script)
            logger.debug(f"읍/면/동 {len(dongs)}개 발견")
            return dongs

        try:
            self.save_crawling_state(district=district_value, step='getting_dongs')

            if self.recovery_enabled:
                return self.execute_with_recovery(
                    _get_dongs_impl,
                    description=f"읍/면/동 목록 조회 ({district_value})"
                )
            else:
                return self.execute_simple(
                    _get_dongs_impl,
                    description=f"읍/면/동 목록 조회 ({district_value})"
                )
        except Exception as e:
            logger.error(f"읍/면/동 추출 오류: {e}")
            return []

    def select_dong_and_search(self, dong_index: int) -> Optional[str]:
        """특정 읍/면/동 선택하고 검색 실행"""

        def _select_dong_and_search_impl():
            logger.debug("읍/면/동 선택 및 검색 중...")

            # 읍/면/동 선택
            script = f"""
            var dongTabs = document.querySelectorAll('#areaDepth3 li');
            if (dongTabs.length > {dong_index}) {{
                dongTabs.forEach(function(li) {{
                    li.classList.remove('on');
                }});

                var targetDong = dongTabs[{dong_index}];
                targetDong.classList.add('on');
                targetDong.querySelector('a').click();

                console.log('읍/면/동 선택 완료:', targetDong.querySelector('a').textContent);
                return 'dong_selected:' + targetDong.querySelector('a').textContent;
            }}

            return 'dong_selection_failed';
            """

            result = self.driver.execute_script(script)

            if 'dong_selected:' in result:
                dong_name = result.split(':')[1]
                logger.debug(f"읍/면/동 선택: {dong_name}")

                time.sleep(2)

                # 선택 완료 및 검색 실행
                self.complete_area_selection()
                self.execute_search_from_popup()

                # 결과 로딩 대기
                time.sleep(5)

                return dong_name
            else:
                raise Exception("읍/면/동 선택 실패")

        try:
            self.save_crawling_state(dong=dong_index, step='selecting_dong')

            if self.recovery_enabled:
                return self.execute_with_recovery(
                    _select_dong_and_search_impl,
                    description=f"읍/면/동 선택 및 검색 ({dong_index})"
                )
            else:
                return self.execute_simple(
                    _select_dong_and_search_impl,
                    description=f"읍/면/동 선택 및 검색 ({dong_index})"
                )
        except Exception as e:
            logger.error(f"읍/면/동 선택 오류: {e}")
            return None

    def complete_area_selection(self):
        """지역 선택 완료"""

        def _complete_area_selection_impl():
            script = """
            var selectBtn = document.querySelector('button[onclick=\"selBs(\\'selBsArea\\');\"]');
            if (selectBtn) {
                selectBtn.click();
                console.log('지역 선택 완료 버튼 클릭 성공');
                return 'area_selection_completed';
            } else {
                console.log('선택 완료 버튼을 찾을 수 없음');
                return 'complete_button_not_found';
            }
            """

            result = self.driver.execute_script(script)

            if result == 'area_selection_completed':
                logger.debug("지역 선택 완료")
            else:
                raise Exception(f"지역 선택 완료 실패: {result}")

            time.sleep(2)

        try:
            if self.recovery_enabled:
                self.execute_with_recovery(
                    _complete_area_selection_impl,
                    description="지역 선택 완료"
                )
            else:
                self.execute_simple(
                    _complete_area_selection_impl,
                    description="지역 선택 완료"
                )
        except Exception as e:
            logger.error(f"지역 선택 완료 실패: {e}")

    def execute_search_from_popup(self):
        """팝업에서 검색 실행"""

        def _execute_search_impl():
            script = """
            var searchBtn = document.querySelector('button[onclick=\"doSearch(\\'#filterPopup\\');\"]');
            if (searchBtn) {
                searchBtn.click();
                console.log('조회 버튼 클릭 완료');
                return 'search_executed_from_popup';
            } else {
                console.log('조회 버튼을 찾을 수 없음');
                return 'search_button_not_found';
            }
            """

            result = self.driver.execute_script(script)

            if result == 'search_executed_from_popup':
                logger.debug("검색 실행 완료")
            else:
                raise Exception(f"검색 실행 실패: {result}")

        try:
            if self.recovery_enabled:
                self.execute_with_recovery(
                    _execute_search_impl,
                    description="검색 실행"
                )
            else:
                self.execute_simple(
                    _execute_search_impl,
                    description="검색 실행"
                )
        except Exception as e:
            logger.error(f"검색 실행 실패: {e}")

    def extract_data(self) -> Dict[str, Any]:
        """데이터 추출"""

        def _extract_data_impl():
            script = """
            var allResults = [];

            console.log('=== 데이터 추출 시작 (원본 그대로 사용) ===');

            // 디버깅: 전역 변수 상태 확인
            console.log('totalCnt:', typeof totalCnt !== 'undefined' ? totalCnt : 'undefined');
            console.log('resultMinsJson:', typeof resultMinsJson !== 'undefined' ? resultMinsJson.length : 'undefined');

            // 데이터 처리 함수
            function processData(data, type) {
                if (typeof data !== 'undefined' && Array.isArray(data) && data.length > 0) {
                    console.log(type + ' 원본 데이터:', data.length + '개');
                    var processedCount = 0;
                    var skippedCount = 0;

                    // 모든 데이터 처리
                    for (var i = 0; i < data.length; i++) {
                        var item = data[i];
                        if (item && item.content) {
                            var name = item.content.title || '';
                            var address = item.content.address || '';

                            if (!name || !address) {
                                skippedCount++;
                                continue;
                            }

                            allResults.push({
                                type: type,
                                name: name,
                                address: address,
                                category: item.content.category || '',
                                phone: item.content.tel || '',
                                distance: item.content.distance || ''
                            });
                            processedCount++;
                        } else {
                            skippedCount++;
                        }
                    }
                    console.log(type + ' 처리결과:');
                    console.log('  - 처리완료: ' + processedCount + '개');
                    console.log('  - 빈데이터: ' + skippedCount + '개');
                    console.log('  - 총계확인: ' + (processedCount + skippedCount) + ' = ' + data.length);
                } else {
                    console.log(type + ' 데이터 없음');
                }
            }

            // 소비쿠폰만 처리
            processData(resultMinsJson, '소비쿠폰');

            // 전체 카운트 확인
            var totalCount = document.querySelector('[data-comma="total"]');
            var totalText = totalCount ? totalCount.textContent.trim() : '0';

            console.log('=== 추출 완료 (원본 데이터 그대로) ===');
            console.log('총 추출된 데이터:', allResults.length + '개');
            console.log('페이지 표시 총계:', totalText + '건');

            // 일치 여부 확인
            var displayTotal = parseInt(totalText.replace(/,/g, '')) || 0;
            if (allResults.length === displayTotal) {
                console.log('✓ 완벽 일치: 모든 데이터 추출 성공');
            } else if (allResults.length < displayTotal) {
                console.log('일부 누락: 빈 데이터로 인한 차이');
            } else {
                console.log('초과 추출');
            }

            return {
                total_display: totalText,
                results: allResults,
                counts: {
                    mins: typeof resultMinsJson !== 'undefined' && Array.isArray(resultMinsJson) ? resultMinsJson.length : 0
                },
                extracted_count: allResults.length,
                display_total: displayTotal
            };
            """

            result = self.driver.execute_script(script)

            if result:
                extracted = result.get('extracted_count', 0)
                display = result.get('display_total', 0)
                counts = result.get('counts', {})

                logger.info(f"데이터 추출 분석:")
                logger.info(f"  소비쿠폰: {counts.get('mins', 0)}개")
                logger.info(f"  최종 추출: {extracted}개")
                logger.info(f"  화면 표시: {display}개")

                if extracted == display:
                    logger.info("완벽 일치: 모든 데이터 추출 성공")
                elif extracted < display:
                    diff = display - extracted
                    logger.warning(f"일부 누락: {diff}개 (빈 데이터로 추정)")
                else:
                    diff = extracted - display
                    logger.warning(f"초과 추출: {diff}개 (예상치 못한 상황)")

            return result

        try:
            self.save_crawling_state(step='extracting_data')

            if self.recovery_enabled:
                return self.execute_with_recovery(
                    _extract_data_impl,
                    description="데이터 추출"
                )
            else:
                return self.execute_simple(
                    _extract_data_impl,
                    description="데이터 추출"
                )
        except Exception as e:
            logger.error(f"결과 추출 실패: {e}")
            return None

    def extract_region_from_address(self, address):
        """주소에서 지역 정보 추출"""
        try:
            logger.debug(f"주소 파싱: {address}")

            # AddressParser 사용
            parsed = self.address_parser.parse_address(address)

            province = parsed.get('province')
            city = parsed.get('city')
            town = parsed.get('town')

            if not province or not city:
                logger.warning(f"필수 지역 정보 누락: {address}")
                return None

            logger.debug(f"파싱 결과: {province} > {city} > {town}")
            return (province, city, town)

        except Exception as e:
            logger.error(f"주소 파싱 실패: {e}")
            return None

    def crawl_single_region_simple(self, province_name: str = "서울", district_name: str = "강남구",
                                   dong_name: str = "일원본동") -> Dict[str, Any]:
        """단순화된 단일 지역 크롤링 - 복구 기능 없이"""
        logger.info(f"단일 지역 크롤링 (단순버전): {province_name} {district_name} {dong_name}")

        # 복구 기능 비활성화
        original_recovery_state = self.recovery_enabled
        self.disable_recovery()

        total_stats = {
            'regions_crawled': 0,
            'total_stores': 0,
            'total_saved': 0,
            'api_success': 0,
            'api_failed': 0
        }

        try:
            # 1. 사이트 접근 및 설정
            if not self.access_website():
                logger.error("사이트 접근 실패")
                return total_stats

            # 2. 지역 목록 가져오기
            provinces = self.get_all_regions_from_site()
            if not provinces:
                logger.error("시/도 목록을 가져올 수 없습니다")
                return total_stats

            # 3. 지정된 시/도 찾기
            target_province = None
            for province in provinces:
                if province_name in province['name']:
                    target_province = province
                    break

            if not target_province:
                logger.error(f"시/도를 찾을 수 없습니다: {province_name}")
                return total_stats

            logger.info(f"대상 시/도: {target_province['name']}")

            # 4. 시/군/구 목록 가져오기
            districts = self.get_districts_for_province(target_province['value'])
            if not districts:
                logger.error("시/군/구 목록을 가져올 수 없습니다")
                return total_stats

            # 5. 지정된 시/군/구 찾기
            target_district = None
            for district in districts:
                if district_name in district['name']:
                    target_district = district
                    break

            if not target_district:
                logger.error(f"시/군/구를 찾을 수 없습니다: {district_name}")
                return total_stats

            logger.info(f"대상 시/군/구: {target_district['name']}")

            # 6. 읍/면/동 목록 가져오기
            dongs = self.get_dongs_for_district(target_district['value'])
            if not dongs:
                logger.error("읍/면/동 목록을 가져올 수 없습니다")
                return total_stats

            # 7. 지정된 읍/면/동 찾기
            target_dong = None
            for dong in dongs:
                if dong_name in dong['name']:
                    target_dong = dong
                    break

            if not target_dong:
                # 첫 번째 동을 사용
                target_dong = dongs[0] if dongs else None
                logger.warning(f"지정된 읍/면/동을 찾을 수 없어 첫 번째 동 사용: {target_dong['name'] if target_dong else 'None'}")

            if not target_dong:
                logger.error("사용할 읍/면/동이 없습니다")
                return total_stats

            logger.info(f"대상 읍/면/동: {target_dong['name']}")

            # 8. 읍/면/동 선택 및 검색
            selected_dong = self.select_dong_and_search(target_dong['index'])

            if selected_dong:
                logger.info(f"검색 완료: {selected_dong}")

                # 9. 데이터 추출
                data = self.extract_data()

                if data and data.get('results'):
                    stores_count = len(data['results'])
                    logger.info(f"{stores_count}개 가맹점 발견")

                    # 10. 데이터베이스 저장
                    save_stats = self.save_store_data(data['results'])

                    total_stats['regions_crawled'] = 1
                    total_stats['total_stores'] = stores_count
                    total_stats['total_saved'] = save_stats['saved']
                    total_stats['api_success'] = save_stats['naver_success'] + save_stats['kakao_success']
                    total_stats['api_failed'] = save_stats['api_failed']

                    logger.info(f"저장 결과:")
                    logger.info(f"  - 저장 성공: {save_stats['saved']}개")
                    logger.info(f"  - 네이버 성공: {save_stats['naver_success']}개")
                    logger.info(f"  - 카카오 성공: {save_stats['kakao_success']}개")
                    logger.info(f"  - API 실패: {save_stats['api_failed']}개")
                else:
                    logger.info("가맹점 없음")
            else:
                logger.error(f"{target_dong['name']} 검색 실패")

            return total_stats

        except Exception as e:
            logger.error(f"단일 지역 크롤링 오류: {e}")
            return total_stats
        finally:
            # 원래 복구 설정 복원
            if original_recovery_state:
                self.enable_recovery()

    def crawl_single_region_with_recovery(self, province_name: str = None, district_name: str = None,
                                          dong_name: str = None) -> Dict[str, Any]:
        """복구 기능이 있는 단일 지역 크롤링"""
        if province_name:
            logger.info(f"단일 지역 크롤링 (복구기능): {province_name} {district_name} {dong_name}")
        else:
            logger.info("전국 크롤링 (복구기능)")

        # 복구 기능 활성화 확인
        if not self.recovery_enabled:
            self.enable_recovery()

        total_stats = {
            'regions_crawled': 0,
            'total_stores': 0,
            'total_saved': 0,
            'api_success': 0,
            'api_failed': 0
        }

        def _crawl_with_recovery():
            # 사이트 접근
            if not self.access_website():
                raise Exception("사이트 접근 실패")

            # 지역 목록 가져오기
            provinces = self.get_all_regions_from_site()
            if not provinces:
                raise Exception("시/도 목록 조회 실패")

            # 대상 지역 크롤링
            for province in provinces:
                if province_name and province_name not in province['name']:
                    continue

                logger.info(f"시/도 크롤링: {province['name']}")
                self.current_province = province
                self.save_crawling_state(province=province['name'])

                districts = self.get_districts_for_province(province['value'])

                for district in districts:
                    if district_name and district_name not in district['name']:
                        continue

                    logger.info(f"시/군/구 크롤링: {district['name']}")
                    self.current_district = district
                    self.save_crawling_state(province=province['name'], district=district['name'])

                    dongs = self.get_dongs_for_district(district['value'])

                    for dong in dongs:
                        if dong_name and dong_name not in dong['name']:
                            continue

                        logger.info(f"읍/면/동 크롤링: {dong['name']}")
                        self.save_crawling_state(
                            province=province['name'],
                            district=district['name'],
                            dong=dong['name']
                        )

                        # 읍/면/동 선택 및 검색
                        selected_dong = self.select_dong_and_search(dong['index'])

                        if selected_dong:
                            # 데이터 추출
                            data = self.extract_data()

                            if data and data.get('results'):
                                stores_count = len(data['results'])
                                logger.info(f"{stores_count}개 가맹점 발견")

                                # 데이터베이스 저장
                                save_stats = self.save_store_data(data['results'])

                                total_stats['regions_crawled'] += 1
                                total_stats['total_stores'] += stores_count
                                total_stats['total_saved'] += save_stats['saved']
                                total_stats['api_success'] += save_stats['naver_success'] + save_stats['kakao_success']
                                total_stats['api_failed'] += save_stats['api_failed']

                                logger.info(f"저장 완료: {save_stats['saved']}개")
                            else:
                                logger.info("가맹점 없음")
                        else:
                            logger.warning(f"{dong['name']} 검색 실패")

                        # 지정된 지역만 크롤링하는 경우 여기서 종료
                        if dong_name:
                            return total_stats

                        # 다음 동을 위한 팝업 재오픈 (마지막 동이 아닌 경우)
                        if dongs.index(dong) < len(dongs) - 1:
                            self.reopen_area_selection()
                            # 현재 시/도, 시/군/구 재선택
                            self.get_districts_for_province(province['value'])
                            self.get_dongs_for_district(district['value'])

                    # 지정된 시/군/구만 크롤링하는 경우 여기서 종료
                    if district_name:
                        return total_stats

                    # 다음 시/군/구를 위한 팝업 재오픈 (마지막 시/군/구가 아닌 경우)
                    if districts.index(district) < len(districts) - 1:
                        self.reopen_area_selection()
                        self.get_districts_for_province(province['value'])

                # 지정된 시/도만 크롤링하는 경우 여기서 종료
                if province_name:
                    return total_stats

                # 다음 시/도를 위한 팝업 재오픈 (마지막 시/도가 아닌 경우)
                if provinces.index(province) < len(provinces) - 1:
                    self.reopen_area_selection()

            return total_stats

        try:
            return self.execute_with_recovery(
                _crawl_with_recovery,
                description=f"지역 크롤링 ({province_name or '전국'} {district_name or ''} {dong_name or ''})"
            )
        except Exception as e:
            logger.error(f"복구 기능 지역 크롤링 실패: {e}")
            return total_stats

    def reopen_area_selection(self):
        """지역선택 팝업 다시 열기"""

        def _reopen_area_selection_impl():
            logger.debug("지역선택 팝업 다시 열기...")

            # 필터 팝업 다시 열기
            self.open_filter_popup()

            # 지역선택으로 다시 설정
            script = """
            var locationRadio = document.getElementById('locationRdo2');
            if (locationRadio) {
                locationRadio.click();
                locationRadio.checked = true;
                document.querySelectorAll('#locationType .radio-box').forEach(function(box) {
                    box.classList.remove('checked');
                });
                locationRadio.closest('.radio-box').classList.add('checked');
                console.log('위치: 지역선택 재설정');
            }

            setTimeout(function() {
                var areaBtn = document.querySelector('a[data-bs="selBsArea"]');
                if (areaBtn) {
                    areaBtn.click();
                    console.log('지역선택 버튼 재클릭');
                }
            }, 1000);

            return 'reopened';
            """

            self.driver.execute_script(script)
            time.sleep(3)

            logger.debug("지역선택 팝업 재오픈 완료")

        try:
            if self.recovery_enabled:
                self.execute_with_recovery(
                    _reopen_area_selection_impl,
                    description="지역선택 팝업 재오픈"
                )
            else:
                self.execute_simple(
                    _reopen_area_selection_impl,
                    description="지역선택 팝업 재오픈"
                )
        except Exception as e:
            logger.error(f"지역선택 팝업 재열기 실패: {e}")

    def crawl_all_regions(self) -> Dict[str, Any]:
        """전국 모든 지역 크롤링"""
        logger.info("전국 크롤링 시작")
        return self.crawl_single_region_with_recovery(province_name=None, district_name=None, dong_name=None)

    def crawl_single_region(self, province_name: str, district_name: str = None,
                            dong_name: str = None) -> Dict[str, Any]:
        """단일 지역 크롤링 - 모드에 따라 복구 기능 선택"""

        # test 모드이거나 특정 조건인 경우 단순버전 사용
        if (province_name == "서울" and district_name == "강남구" and
                dong_name == "일원본동"):
            logger.info("테스트 모드: 단순 크롤링 방식 사용")
            return self.crawl_single_region_simple(province_name, district_name, dong_name)
        else:
            logger.info("일반 모드: 복구 기능 포함 크롤링 사용")
            return self.crawl_single_region_with_recovery(province_name, district_name, dong_name)

    def set_recovery_mode(self, enabled: bool):
        """복구 모드 설정"""
        if enabled:
            self.enable_recovery()
        else:
            self.disable_recovery()

        logger.info(f"복구 모드 {'활성화' if enabled else '비활성화'}")

    def get_recovery_status(self) -> Dict[str, Any]:
        """복구 기능 상태 반환"""
        return {
            'recovery_enabled': self.recovery_enabled,
            'max_recovery_attempts': self.max_recovery_attempts,
            'current_recovery_count': self.recovery_count,
            'current_state': self.current_state,
            'recovery_attempts_made': self.crawling_stats.get('recovery_attempts', 0)
        }