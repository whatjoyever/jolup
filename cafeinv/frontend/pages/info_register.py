import os, sys
import streamlit as st
import re

# --- sidebar import 경로 보정 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

from sidebar import render_sidebar
from client import api_get, api_post

# -------------------------------
# 페이지 설정 & 커스텀 사이드바
# -------------------------------
st.set_page_config(page_title="신규 등록", page_icon="⚙️", layout="wide")
render_sidebar("info")

# 기본 여백/스타일
st.markdown("""
<style>
    .main .block-container {
        max-width: 900px;
        padding-top: 1rem;
        padding-right: 1.5rem;
        padding-left: 1.5rem;
        padding-bottom: 1rem;
    }
    div[data-testid="stHorizontalBlock"] { padding-left: 0.5rem; }
    button[data-testid="baseButton-secondary"]:hover {
        background-color: #d3d3d3 !important;
        border-color: #d3d3d3 !important;
    }
    .sidebar-menu {
        padding: 10px;
        margin: 5px 0;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s;
    }
    .sidebar-menu:hover {
        background-color: #f0f0f0;
    }
    .sidebar-menu.active {
        background-color: #0B3B75;
        color: white;
    }
</style>
<script>
    // 탭 상태 유지를 위한 JavaScript
    function findTabs() {
        // 여러 방법으로 탭 버튼 찾기
        let tabs = document.querySelectorAll('button[data-baseweb="tab"]');
        if (!tabs || tabs.length === 0) {
            tabs = document.querySelectorAll('[role="tab"]');
        }
        if (!tabs || tabs.length === 0) {
            tabs = document.querySelectorAll('div[data-testid="stTabs"] button');
        }
        if (!tabs || tabs.length === 0) {
            tabs = document.querySelectorAll('[data-testid="stTabs"] button');
        }
        if (!tabs || tabs.length === 0) {
            tabs = document.querySelectorAll('button[type="button"][aria-selected]');
        }
        return tabs;
    }
    
    function activateTab(tabIndex) {
        const tabs = findTabs();
        if (tabs && tabs.length > tabIndex && tabs[tabIndex]) {
            const tab = tabs[tabIndex];
            if (tab.offsetParent !== null) {
                tab.click();
                setTimeout(function() {
                    const currentTabs = findTabs();
                    if (currentTabs && currentTabs.length > tabIndex) {
                        const currentTab = currentTabs[tabIndex];
                        if (currentTab.getAttribute('aria-selected') !== 'true' && 
                            !currentTab.classList.contains('st-ah') &&
                            !currentTab.classList.contains('active')) {
                            currentTab.click();
                        }
                    }
                }, 50);
                return true;
            }
        }
        return false;
    }
    
    function setupTabListeners() {
        const tabButtons = findTabs();
        if (tabButtons && tabButtons.length > 0) {
            tabButtons.forEach(function(btn, index) {
                if (!btn.hasAttribute('data-tab-listener')) {
                    btn.setAttribute('data-tab-listener', 'true');
                    btn.addEventListener('click', function() {
                        sessionStorage.setItem('info_register_tab', index.toString());
                        sessionStorage.removeItem('info_register_tab_force');
                    }, true);
                }
            });
        }
    }
    
    function tryActivateSavedTab() {
        const savedTab = sessionStorage.getItem('info_register_tab');
        const forceFlag = sessionStorage.getItem('info_register_tab_force');
        
        if (savedTab !== null) {
            const tabIndex = parseInt(savedTab);
            
            if (forceFlag === '1') {
                let attempts = 0;
                const maxAttempts = 50;
                const tryActivate = setInterval(function() {
                    attempts++;
                    const tabs = findTabs();
                    if (tabs && tabs.length > tabIndex) {
                        if (activateTab(tabIndex)) {
                            const currentTabs = findTabs();
                            if (currentTabs && currentTabs.length > tabIndex) {
                                const currentTab = currentTabs[tabIndex];
                                if (currentTab.getAttribute('aria-selected') === 'true' || 
                                    currentTab.classList.contains('st-ah') ||
                                    currentTab.classList.contains('active')) {
                                    clearInterval(tryActivate);
                                    sessionStorage.removeItem('info_register_tab_force');
                                }
                            }
                        }
                    }
                    if (attempts >= maxAttempts) {
                        clearInterval(tryActivate);
                        sessionStorage.removeItem('info_register_tab_force');
                    }
                }, 150);
            } else {
                let attempts = 0;
                const tryActivate = setInterval(function() {
                    attempts++;
                    if (activateTab(tabIndex) || attempts > 30) {
                        clearInterval(tryActivate);
                    }
                }, 100);
            }
        }
    }
    
    window.addEventListener('load', function() {
        tryActivateSavedTab();
        setTimeout(setupTabListeners, 200);
        setTimeout(setupTabListeners, 500);
        setTimeout(setupTabListeners, 1000);
        setTimeout(setupTabListeners, 2000);
    });
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            tryActivateSavedTab();
            setupTabListeners();
        });
    } else {
        tryActivateSavedTab();
        setupTabListeners();
    }
    
    let observerTimeout;
    let lastTabCheck = -1;
    const observer = new MutationObserver(function(mutations) {
        clearTimeout(observerTimeout);
        observerTimeout = setTimeout(function() {
            const savedTab = sessionStorage.getItem('info_register_tab');
            const forceFlag = sessionStorage.getItem('info_register_tab_force');
            
            if (savedTab !== null) {
                const tabIndex = parseInt(savedTab);
                
                if (forceFlag === '1') {
                    tryActivateSavedTab();
                    setupTabListeners();
                    return;
                }
                
                const tabs = findTabs();
                if (tabs && tabs.length > tabIndex) {
                    let activeTab = -1;
                    tabs.forEach(function(tab, idx) {
                        if (tab.getAttribute('aria-selected') === 'true' || 
                            tab.classList.contains('st-ah') || 
                            tab.classList.contains('active')) {
                            activeTab = idx;
                        }
                    });
                    
                    if (activeTab !== tabIndex && lastTabCheck !== tabIndex) {
                        activateTab(tabIndex);
                        lastTabCheck = tabIndex;
                    }
                }
                setupTabListeners();
            }
        }, 300);
    });
    
    document.addEventListener('DOMContentLoaded', function() {
        const tabsContainer = document.querySelector('[data-testid="stTabs"]') || document.body;
        observer.observe(tabsContainer, { 
            childList: true, 
            subtree: true, 
            attributes: true, 
            attributeFilter: ['class', 'aria-selected', 'aria-expanded'] 
        });
    });
    
    const streamlitObserver = new MutationObserver(function(mutations) {
        const forceFlag = sessionStorage.getItem('info_register_tab_force');
        if (forceFlag === '1') {
            setTimeout(function() {
                tryActivateSavedTab();
                setupTabListeners();
            }, 100);
        }
    });
    
    setTimeout(function() {
        const streamlitContainer = document.querySelector('.main') || document.body;
        streamlitObserver.observe(streamlitContainer, {
            childList: true,
            subtree: true
        });
    }, 500);
</script>
""", unsafe_allow_html=True)

# -------------------------------
# 세션 상태 초기화
# -------------------------------
if "categories" not in st.session_state:
    st.session_state.categories = []
if "products" not in st.session_state:
    st.session_state.products = []
if "partners" not in st.session_state:
    st.session_state.partners = []
if "admins" not in st.session_state:
    st.session_state.admins = []

# -------------------------------
# 공통 코드 자동 채번 함수
# -------------------------------
def generate_next_code(prefix: str, width: int, existing_codes: list[str]) -> str:
    max_num = 0
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")

    for code in existing_codes:
        if not code:
            continue
        match = pattern.match(code)
        if match:
            try:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num
            except ValueError:
                continue

    next_num = max_num + 1
    return f"{prefix}{next_num:0{width}d}"

def generate_next_category_code() -> str:
    existing = [c.get("code", "") for c in st.session_state.categories]
    return generate_next_code("cat_", 3, existing)

def generate_next_product_code() -> str:
    existing = [p.get("code", "") for p in st.session_state.products]
    return generate_next_code("pr_", 3, existing)

def generate_next_partner_code() -> str:
    existing = [p.get("code", "") for p in st.session_state.partners]
    # ✅ pt_001, pt_002 ... 형식
    return generate_next_code("pt_", 3, existing)

# -------------------------------
# 헤더 & 뒤로가기
# -------------------------------
title_col, button_col = st.columns([4, 1])
with title_col:
    st.title("신규 등록")
with button_col:
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
    if st.button("← 뒤로가기", use_container_width=True, key="back_button"):
        st.switch_page("pages/info.py")

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# -------------------------------
# 탭 구조
# -------------------------------
if "current_tab" not in st.session_state:
    st.session_state.current_tab = 0

if "last_registered_category" not in st.session_state:
    st.session_state.last_registered_category = None
if "last_registered_product" not in st.session_state:
    st.session_state.last_registered_product = None
if "last_registered_partner" not in st.session_state:
    st.session_state.last_registered_partner = None
if "last_registered_admin" not in st.session_state:
    st.session_state.last_registered_admin = None

category_tab, product_tab, partner_tab, admin_tab = st.tabs(
    ["카테고리 등록", "품목 등록", "거래처 등록", "관리자 등록"]
)

# -------------------------------
# 카테고리 등록 탭
# -------------------------------
with category_tab:
    st.subheader("카테고리 등록")
    default_cat_code = generate_next_category_code()

    with st.form("category_form", clear_on_submit=True):
        form_col1, form_col2, form_col3 = st.columns([2, 3, 1])
        with form_col1:
            st.caption("코드번호")
            cat_code = st.text_input(
                "코드번호",
                value=default_cat_code,
                key="cat_code_input",
                label_visibility="collapsed",
                placeholder="cat_001"
            )
        with form_col2:
            st.caption("카테고리명")
            cat_name = st.text_input(
                "카테고리명",
                key="cat_name_input",
                label_visibility="collapsed",
                placeholder="원두"
            )
        with form_col3:
            st.markdown("<div style='height: 37px'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button("등록", use_container_width=True)

        if submitted:
            code = (cat_code or "").strip()
            name = (cat_name or "").strip()
            if not code or not name:
                st.warning("코드번호와 카테고리명을 모두 입력하세요.")
            elif any(c["code"] == code for c in st.session_state.categories):
                st.error("이미 존재하는 코드번호입니다.")
            else:
                new_category = {"code": code, "name": name}
                st.session_state.categories.append(new_category)
                st.session_state.last_registered_category = new_category
                st.session_state.category_success = True
                st.session_state.info_register_tab = 0
                st.markdown("""
                <script>
                    sessionStorage.setItem('info_register_tab', '0');
                    sessionStorage.setItem('info_register_tab_force', '1');
                </script>
                """, unsafe_allow_html=True)
                
    
    if st.session_state.get("category_success", False):
        st.success("✅ 카테고리가 성공적으로 등록되었습니다!")
        st.session_state.category_success = False
    
    if st.session_state.last_registered_category:
        st.markdown("---")
        st.markdown("#### 📋 최근 등록한 카테고리")
        last_cat = st.session_state.last_registered_category
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**코드번호:** {last_cat.get('code', '-')}")
        with col2:
            st.write(f"**카테고리명:** {last_cat.get('name', '-')}")

    if st.session_state.categories:
        st.markdown("---")
        st.markdown("#### 📚 등록된 전체 카테고리")
        for idx, cat in enumerate(st.session_state.categories, start=1):
            st.write(f"{idx}. `{cat.get('code', '-')}` - {cat.get('name', '-')}")

# -------------------------------
# 품목 등록 탭
# -------------------------------
with product_tab:
    st.subheader("품목 등록")
    
    default_prod_code = generate_next_product_code()
    default_cat = ""
    default_name = ""
    default_unit = ""
    default_status = True

    with st.form("product_form", clear_on_submit=True):
        r1c1, r1c2, r1c3 = st.columns([2, 3, 3])
        with r1c1:
            st.caption("코드번호")
            pr_code = st.text_input(
                "코드번호",
                value=default_prod_code,
                key="prod_code_input",
                label_visibility="collapsed",
                placeholder="pr_001"
            )
        with r1c2:
            st.caption("카테고리명")
            category_names = [c["name"] for c in st.session_state.categories]
            if category_names:
                default_index = category_names.index(default_cat) if default_cat in category_names else 0
                pr_category = st.selectbox(
                    "카테고리명",
                    options=category_names,
                    index=default_index,
                    key="prod_category_select",
                    label_visibility="collapsed"
                )
            else:
                pr_category = st.text_input(
                    "카테고리명",
                    value=default_cat,
                    key="prod_category_input_fallback",
                    label_visibility="collapsed",
                    placeholder="원두"
                )
                st.info("카테고리를 먼저 등록하면 여기에서 선택할 수 있습니다.")
        with r1c3:
            st.caption("품목 명")
            pr_name = st.text_input(
                "품목 명",
                value=default_name,
                key="prod_name_input",
                label_visibility="collapsed",
                placeholder="디카페인 원두"
            )

        r2c1, r2c2, r2c3, r2c4 = st.columns([2, 2, 2, 1])
        with r2c1:
            st.caption("입고 단위")
            unit_options = ["병", "박스", "kg", "g", "ml", "L", "봉투", "컵", "스푼", "갯수", "기타"]
            default_unit_index = unit_options.index(default_unit) if default_unit in unit_options else 0
            pr_unit = st.selectbox(
                "입고 단위",
                options=unit_options,
                index=default_unit_index,
                key="prod_unit_select",
                label_visibility="collapsed"
            )
        with r2c2:
            st.caption("상태")
            default_status_label = "사용" if default_status else "단종"
            pr_status = st.selectbox(
                "",
                options=["사용", "단종"],
                index=(0 if default_status_label == "사용" else 1),
                label_visibility="collapsed"
            )
        with r2c3:
            st.caption("안전재고")
            pr_safety = st.number_input(
                "안전재고",
                min_value=0,
                step=1,
                value=0,
                key="prod_safety_input",
                label_visibility="collapsed"
            )
        with r2c4:
            st.caption("\u00A0")
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            pr_submitted = st.form_submit_button("등록", use_container_width=True)

        if pr_submitted:
            code = (pr_code or "").strip()
            cat  = (pr_category or "").strip()
            name = (pr_name or "").strip()
            unit = (pr_unit or "").strip()
            if not code or not name:
                st.warning("코드번호와 품목명을 입력하세요.")
            else:
                if any(p["code"] == code for p in st.session_state.products):
                    st.error("이미 존재하는 코드번호입니다.")
                else:
                    new_product = {
                        "code": code,
                        "category": cat,
                        "name": name,
                        "unit": unit,
                        "status": pr_status,
                        "safety": int(pr_safety),
                    }
                    st.session_state.products.append(new_product)
                    st.session_state.last_registered_product = new_product
                    st.session_state.product_success = True
                    st.session_state.info_register_tab = 1
                    st.markdown("""
                    <script>
                        sessionStorage.setItem('info_register_tab', '1');
                        sessionStorage.setItem('info_register_tab_force', '1');
                    </script>
                    """, unsafe_allow_html=True)
                    
    
    if st.session_state.get("product_success", False):
        st.success("✅ 품목이 성공적으로 등록되었습니다!")
        st.session_state.product_success = False
    
    if st.session_state.last_registered_product:
        st.markdown("---")
        st.markdown("#### 📋 최근 등록한 품목")
        last_prod = st.session_state.last_registered_product
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.write(f"**코드번호:** {last_prod.get('code', '-')}")
        with col2:
            st.write(f"**품목명:** {last_prod.get('name', '-')}")
        with col3:
            st.write(f"**카테고리:** {last_prod.get('category', '-')}")
        with col4:
            st.write(f"**단위:** {last_prod.get('unit', '-')}")

    if st.session_state.products:
        st.markdown("---")
        st.markdown("#### 📚 등록된 전체 품목")
        for idx, p in enumerate(st.session_state.products, start=1):
            st.write(
                f"{idx}. `{p.get('code','-')}` - {p.get('name','-')} "
                f"(카테고리: {p.get('category','-')}, 단위: {p.get('unit','-')}, "
                f"상태: {p.get('status','-')}, 안전재고: {p.get('safety','-')})"
            )

# -------------------------------
# 거래처 등록 탭
# -------------------------------
with partner_tab:
    st.subheader("거래처 등록")

    # ✅ pt_001, pt_002 ... 형식 자동 채번
    default_partner_code = generate_next_partner_code()

    with st.form("partner_form", clear_on_submit=True):
        form_col1, form_col2, form_col3, form_col4, form_col5, form_col6 = st.columns([1.5, 2, 2, 2, 3, 1])
        with form_col1:
            st.caption("거래처 코드")
            p_code = st.text_input(
                "거래처 코드",
                value=default_partner_code,
                key="p_code_input",
                label_visibility="collapsed",
                placeholder="pt_001"
            )
        with form_col2:
            st.caption("거래처명")
            p_name = st.text_input(
                "거래처명",
                key="p_name_input",
                label_visibility="collapsed",
                placeholder="○○커피"
            )
        with form_col3:
            st.caption("사업자번호")
            p_bus = st.text_input(
                "사업자번호",
                key="p_bus_input",
                label_visibility="collapsed",
                placeholder="123-45-67890"
            )
        with form_col4:
            st.caption("대표자 이름")
            p_rep = st.text_input(
                "대표자 이름",
                key="p_rep_input",
                label_visibility="collapsed",
                placeholder="홍길동"
            )
        with form_col5:
            st.caption("주소")
            p_addr = st.text_input(
                "주소",
                key="p_addr_input",
                label_visibility="collapsed",
                placeholder="서울시 강남구..."
            )
        with form_col6:
            st.markdown("<div style='height: 37px'></div>", unsafe_allow_html=True)
            partner_submitted = st.form_submit_button("등록", use_container_width=True)

        if partner_submitted:
            if not p_code or not p_name:
                st.error("거래처 코드와 거래처명은 필수 입력 항목입니다.")
            elif any(p["code"] == p_code for p in st.session_state.partners):
                st.error("이미 존재하는 거래처 코드입니다.")
            elif p_bus and not re.match(r'^[0-9\\-]+$', p_bus):
                st.error("사업자번호는 숫자와 하이픈(-)만 입력 가능합니다.")
            elif p_rep and not re.match(r'^[가-힣a-zA-Z\\s]+$', p_rep):
                st.error("대표자 이름은 한글과 영문만 입력 가능합니다.")
            else:
                new_partner = {
                    "code": p_code,
                    "name": p_name,
                    "business_number": p_bus,
                    "representative": p_rep,
                    "address": p_addr,
                }
                st.session_state.partners.append(new_partner)
                st.session_state.last_registered_partner = new_partner
                st.session_state.partner_success = True
                st.session_state.info_register_tab = 2
                st.markdown("""
                <script>
                    sessionStorage.setItem('info_register_tab', '2');
                    sessionStorage.setItem('info_register_tab_force', '1');
                </script>
                """, unsafe_allow_html=True)
               
    
    if st.session_state.get("partner_success", False):
        st.success("✅ 거래처가 성공적으로 등록되었습니다!")
        st.session_state.partner_success = False
    
    if st.session_state.last_registered_partner:
        st.markdown("---")
        st.markdown("#### 📋 최근 등록한 거래처")
        last_part = st.session_state.last_registered_partner
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"**거래처 코드:** {last_part.get('code', '-')}")
            st.write(f"**거래처명:** {last_part.get('name', '-')}")
        with col2:
            st.write(f"**사업자번호:** {last_part.get('business_number', '-')}")
            st.write(f"**대표자:** {last_part.get('representative', '-')}")
        with col3:
            st.write(f"**주소:** {last_part.get('address', '-')}")

    if st.session_state.partners:
        st.markdown("---")
        st.markdown("#### 📚 등록된 전체 거래처")
        for idx, p in enumerate(st.session_state.partners, start=1):
            st.write(
                f"{idx}. `{p.get('code','-')}` - {p.get('name','-')} "
                f"(사업자번호: {p.get('business_number','-')}, 대표자: {p.get('representative','-')}, "
                f"주소: {p.get('address','-')})"
            )

# -------------------------------
# 관리자 등록 탭
# -------------------------------
with admin_tab:
    st.subheader("관리자 등록")

    with st.form("admin_form", clear_on_submit=True):
        form_col1, form_col2, form_col3, form_col4, form_col5, form_col6, form_col7, form_col8 = st.columns(
            [1.2, 1, 1.2, 1.5, 1.5, 1.2, 1.5, 1.2]
        )
        with form_col1:
            st.caption("사번번호")
            emp_no = st.text_input(
                "사번번호",
                key="admin_emp_no",
                label_visibility="collapsed",
                placeholder="EMP001"
            )
        with form_col2:
            st.caption("이름")
            name = st.text_input(
                "이름",
                key="admin_name",
                label_visibility="collapsed",
                placeholder="홍길동"
            )
        with form_col3:
            st.caption("성별")
            gender = st.selectbox(
                "성별",
                ["남성", "여성"],
                key="admin_gender",
                label_visibility="collapsed"
            )
        with form_col4:
            st.caption("이메일")
            email = st.text_input(
                "이메일",
                key="admin_email",
                label_visibility="collapsed",
                placeholder="hong@example.com"
            )
        with form_col5:
            st.caption("전화번호")
            phone = st.text_input(
                "전화번호",
                key="admin_phone",
                label_visibility="collapsed",
                placeholder="010-1234-5678"
            )
        with form_col6:
            st.caption("직급")
            position = st.selectbox(
                "직급",
                ["직원", "매니저", "파트타이머"],
                key="admin_position",
                label_visibility="collapsed"
            )
        with form_col7:
            st.caption("관리 종류")
            management_type = st.selectbox(
                "관리 종류",
                ["출/입고 관리", "청소", "손님 응대", "음료 제조", "음식 제조", "기타"],
                key="admin_management",
                label_visibility="collapsed"
            )
        with form_col8:
            st.caption("재직현황")
            status = st.selectbox(
                "재직현황",
                ["재직", "퇴사", "휴직"],
                key="admin_status",
                label_visibility="collapsed"
            )

        st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
        admin_submitted = st.form_submit_button("등록", use_container_width=True)

        if admin_submitted:
            if not emp_no or not name:
                st.error("사번번호와 이름은 필수 입력 항목입니다.")
            elif any(a["emp_no"] == emp_no for a in st.session_state.admins):
                st.error("이미 존재하는 사번번호입니다.")
            else:
                new_admin = {
                    "emp_no": emp_no,
                    "name": name,
                    "gender": gender,
                    "email": email,
                    "phone": phone,
                    "position": position,
                    "management_type": management_type,
                    "status": status,
                }
                st.session_state.admins.append(new_admin)
                st.session_state.last_registered_admin = new_admin
                st.session_state.admin_success = True
                st.session_state.info_register_tab = 3
                st.markdown("""
                <script>
                    sessionStorage.setItem('info_register_tab', '3');
                    sessionStorage.setItem('info_register_tab_force', '1');
                </script>
                """, unsafe_allow_html=True)
                
    
    if st.session_state.get("admin_success", False):
        st.success("✅ 관리자가 성공적으로 등록되었습니다!")
        st.session_state.admin_success = False
    
    if st.session_state.last_registered_admin:
        st.markdown("---")
        st.markdown("#### 📋 최근 등록한 관리자")
        last_admin = st.session_state.last_registered_admin
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.write(f"**사번번호:** {last_admin.get('emp_no', '-')}")
        with col2:
            st.write(f"**이름:** {last_admin.get('name', '-')}")
        with col3:
            st.write(f"**성별:** {last_admin.get('gender', '-')}")
        with col4:
            st.write(f"**직급:** {last_admin.get('position', '-')}")
        with col3:
            st.write(f"**관리 종류:** {last_admin.get('management_type', '-')}")
        with col4:
            st.write(f"**재직현황:** {last_admin.get('status', '-')}")
    
    if st.session_state.admins:
        st.markdown("---")
        st.markdown("#### 📚 등록된 전체 관리자")
        for idx, a in enumerate(st.session_state.admins, start=1):
            st.write(
                f"{idx}. `{a.get('emp_no','-')}` - {a.get('name','-')} "
                f"(성별: {a.get('gender','-')}, 직급: {a.get('position','-')}, "
                f"관리: {a.get('management_type','-')}, 재직현황: {a.get('status','-')})"
            )
