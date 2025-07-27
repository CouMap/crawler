import time
from typing import Dict, List, Any, Optional
from loguru import logger

from .base_crawler import BaseCrawler
from ..config import crawler_config


class Crawler(BaseCrawler):
    """KB카드 가맹점 크롤러"""

    def __init__(self):
        super().__init__()
        self.location_agreed = False
        self.current_province = None
        self.current_district = None

    def access_website(self) -> bool:
        """KB카드 사이트 접근 및 초기 설정"""
        try:
            logger.info("KB카드 사이트 접근")
            self.driver.get(crawler_config.KB_CARD_URL)
            time.sleep(5)

            # 위치정보 동의 팝업 처리
            self.handle_location_agreement()

            # 필터 팝업 열기
            self.open_filter_popup()

            # 조건 설정
            self.set_search_conditions()

            return True

        except Exception as e:
            logger.error(f"사이트 접근 및 설정 실패: {e}")
            return False

    def handle_location_agreement(self):
        """위치정보 동의 팝업 처리"""
        try:
            if self.location_agreed:
                logger.debug("위치정보 이미 동의됨, 건너뛰기")
                return

            logger.debug("위치정보 동의 팝업 확인 중...")

            script = """
            var agreePopup = document.getElementById('agreePopup');
            if (agreePopup && agreePopup.style.display !== 'none') {
                console.log('위치정보 동의 팝업 발견');

                var checkbox = document.getElementById('chkbox2');
                if (checkbox) {
                    checkbox.click();
                    console.log('체크박스 클릭');
                }

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

        except Exception as e:
            logger.error(f"위치정보 동의 처리 실패: {e}")

    def open_filter_popup(self):
        """필터 팝업 열기"""
        try:
            logger.debug("필터 팝업 열기 시도...")

            script = """
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
                logger.warning(f"필터 팝업 열기 실패: {result}")

            time.sleep(3)

        except Exception as e:
            logger.error(f"필터 팝업 열기 실패: {e}")

    def set_search_conditions(self):
        """검색 조건 설정"""
        try:
            logger.debug("검색 조건 설정 중...")

            script = """
            // 사용처 선택 - 기본으로 소비쿠폰이 체크되어 있으므로 그대로 사용
            console.log('사용처: 소비쿠폰 선택됨 (기본값)');

            // 검색반경 - 가장 큰 범위 자동 선택
            var radiusOptions = ['radiusRdo4', 'radiusRdo3', 'radiusRdo2', 'radiusRdo1'];
            var radiusLabels = ['3km', '1km', '500m', '200m'];
            var selectedRadius = null;

            for (var i = 0; i < radiusOptions.length; i++) {
                var radiusElement = document.getElementById(radiusOptions[i]);
                if (radiusElement && !radiusElement.disabled) {
                    radiusElement.checked = true;
                    radiusElement.closest('.radio-box').classList.add('checked');
                    selectedRadius = radiusLabels[i];
                    console.log('검색반경: ' + selectedRadius + ' 선택 (가장 큰 범위)');
                    break;
                }
            }

            if (!selectedRadius) {
                console.log('검색반경 옵션을 찾을 수 없음');
            }

            // 위치 - 지역선택으로 변경
            var locationRadio = document.getElementById('locationRdo2');
            if (locationRadio) {
                locationRadio.click();
                locationRadio.checked = true;
                document.querySelectorAll('#locationType .radio-box').forEach(function(box) {
                    box.classList.remove('checked');
                });
                locationRadio.closest('.radio-box').classList.add('checked');
                console.log('위치: 지역선택 선택');
            }

            // 지역선택 버튼 클릭
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
            logger.info("검색 조건 설정 완료 - 동적 검색반경 선택")
            time.sleep(3)

        except Exception as e:
            logger.error(f"검색 조건 설정 실패: {e}")

    def get_all_regions_from_site(self) -> List[Dict[str, str]]:
        """사이트에서 모든 지역 정보 추출"""
        try:
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
                logger.error("지역 정보 추출 실패")
                return []

        except Exception as e:
            logger.error(f"지역 정보 추출 오류: {e}")
            return []

    def get_districts_for_province(self, province_value: str) -> List[Dict[str, str]]:
        """특정 시/도의 시/군/구 목록 가져오기"""
        try:
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

        except Exception as e:
            logger.error(f"시/군/구 추출 오류: {e}")
            return []

    def get_dongs_for_district(self, district_value: str) -> List[Dict[str, Any]]:
        """특정 시/군/구의 읍/면/동 목록 가져오기"""
        try:
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

        except Exception as e:
            logger.error(f"읍/면/동 추출 오류: {e}")
            return []

    def select_dong_and_search(self, dong_index: int) -> Optional[str]:
        """특정 읍/면/동 선택하고 검색 실행"""
        try:
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
                logger.warning("읍/면/동 선택 실패")
                return None

        except Exception as e:
            logger.error(f"읍/면/동 선택 오류: {e}")
            return None

    def complete_area_selection(self):
        """지역 선택 완료"""
        try:
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
                logger.warning(f"지역 선택 완료 실패: {result}")

            time.sleep(2)

        except Exception as e:
            logger.error(f"지역 선택 완료 실패: {e}")

    def execute_search_from_popup(self):
        """팝업에서 검색 실행"""
        try:
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
                logger.warning(f"검색 실행 실패: {result}")

        except Exception as e:
            logger.error(f"검색 실행 실패: {e}")

    def extract_data(self) -> Dict[str, Any]:
        """JavaScript 변수에서 결과 추출"""
        try:
            script = """
            var allResults = [];
            var seenStores = new Set();

            console.log('=== 데이터 추출 시작 ===');

            // 디버깅: 전역 변수 상태 확인
            console.log('totalCnt:', typeof totalCnt !== 'undefined' ? totalCnt : 'undefined');
            console.log('resultGpsJson:', typeof resultGpsJson !== 'undefined' ? resultGpsJson.length : 'undefined');
            console.log('resultOnnrJson:', typeof resultOnnrJson !== 'undefined' ? resultOnnrJson.length : 'undefined');
            console.log('resultTrdtJson:', typeof resultTrdtJson !== 'undefined' ? resultTrdtJson.length : 'undefined');  
            console.log('resultMinsJson:', typeof resultMinsJson !== 'undefined' ? resultMinsJson.length : 'undefined');

            // 중복 체크 함수
            function isDuplicate(name, address) {
                var key = name + '|' + address;
                if (seenStores.has(key)) {
                    return true;
                }
                seenStores.add(key);
                return false;
            }

            // 데이터 처리 함수
            function processData(data, type) {
                if (typeof data !== 'undefined' && Array.isArray(data) && data.length > 0) {
                    console.log(type + ' 데이터 발견:', data.length + '개');
                    for (var i = 0; i < Math.min(data.length, 50); i++) {
                        var item = data[i];
                        if (item && item.content) {
                            var name = item.content.title || '';
                            var address = item.content.address || '';

                            if (!isDuplicate(name, address)) {
                                allResults.push({
                                    type: type,
                                    name: name,
                                    address: address,
                                    category: item.content.category || '',
                                    phone: item.content.tel || '',
                                    distance: item.content.distance || ''
                                });
                            }
                        }
                    }
                }
            }

            // 각 데이터 타입별 처리
            processData(resultMinsJson, '소비쿠폰');
            processData(resultGpsJson, '착한가격업소');
            processData(resultOnnrJson, '온누리상품권');
            processData(resultTrdtJson, '전통시장');

            // 전체 카운트 확인
            var totalCount = document.querySelector('[data-comma="total"]');
            var totalText = totalCount ? totalCount.textContent.trim() : '0';

            console.log('=== 추출 완료 (중복 제거 후) ===');
            console.log('총 추출된 데이터:', allResults.length + '개');
            console.log('페이지 표시 총계:', totalText + '건');

            return {
                total_display: totalText,
                results: allResults,
                counts: {
                    gps: typeof resultGpsJson !== 'undefined' && Array.isArray(resultGpsJson) ? resultGpsJson.length : 0,
                    onnr: typeof resultOnnrJson !== 'undefined' && Array.isArray(resultOnnrJson) ? resultOnnrJson.length : 0,
                    trdt: typeof resultTrdtJson !== 'undefined' && Array.isArray(resultTrdtJson) ? resultTrdtJson.length : 0,
                    mins: typeof resultMinsJson !== 'undefined' && Array.isArray(resultMinsJson) ? resultMinsJson.length : 0
                }
            };
            """

            result = self.driver.execute_script(script)
            return result

        except Exception as e:
            logger.error(f"결과 추출 실패: {e}")
            return None

    def reopen_area_selection(self):
        """지역선택 팝업 다시 열기"""
        try:
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

        except Exception as e:
            logger.error(f"지역선택 팝업 재열기 실패: {e}")

    def crawl_region(self, province_name: str = None, district_name: str = None,
                     dong_name: str = None) -> Dict[str, Any]:
        """특정 지역 크롤링"""
        logger.info(f"지역 크롤링 시작: {province_name or '전체'} > {district_name or '전체'} > {dong_name or '전체'}")

        total_stats = {
            'regions_crawled': 0,
            'total_stores': 0,
            'total_saved': 0,
            'api_success': 0,
            'api_failed': 0
        }

        try:
            # 웹사이트 접근
            if not self.access_website():
                return total_stats

            # 지역 목록 가져오기
            provinces = self.get_all_regions_from_site()
            logger.info(f"KB사이트에서 가져온 시/도 목록: {[p['name'] for p in provinces]}")

            for province in provinces:
                logger.info(f"현재 검사 중인 시/도: '{province['name']}', 찾는 지역: '{province_name}'")

                if province_name and province_name not in province['name']:
                    logger.info(f"'{province['name']}'은 '{province_name}'과 매칭되지 않음 - 건너뛰기")
                    continue

                logger.info(f"시/도 크롤링: {province['name']}")
                self.current_province = province

                districts = self.get_districts_for_province(province['value'])

                for district in districts:
                    if district_name and district_name not in district['name']:
                        continue

                    logger.info(f"시/군/구 크롤링: {district['name']}")
                    self.current_district = district

                    dongs = self.get_dongs_for_district(district['value'])

                    for dong_idx, dong in enumerate(dongs):
                        if dong_name and dong_name not in dong['name']:
                            continue

                        logger.info(f"읍/면/동 크롤링: {dong['name']}")

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

                        # 다음 검색을 위해 팝업 재오픈
                        if dong_idx < len(dongs) - 1:
                            self.reopen_area_selection()
                            # 현재 시/도, 시/군/구 재선택
                            self.get_districts_for_province(province['value'])
                            self.get_dongs_for_district(district['value'])

                    # 다음 시/군/구를 위한 재오픈
                    if districts.index(district) < len(districts) - 1:
                        self.reopen_area_selection()
                        self.get_districts_for_province(province['value'])

                # 다음 시/도를 위한 재오픈
                if provinces.index(province) < len(provinces) - 1:
                    self.reopen_area_selection()

            return total_stats

        except Exception as e:
            logger.error(f"지역 크롤링 오류: {e}")
            return total_stats

    def extract_region_from_address(self, address):
        """주소에서 지역 정보 추출 - 간소화된 버전"""
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

    def crawl_all_regions(self) -> Dict[str, Any]:
        """전국 모든 지역 크롤링"""
        logger.info("전국 크롤링 시작")
        return self.crawl_region()

    def crawl_single_region(self, province_name: str, district_name: str = None,
                            dong_name: str = None) -> Dict[str, Any]:
        """단일 지역 크롤링"""
        return self.crawl_region(province_name, district_name, dong_name)