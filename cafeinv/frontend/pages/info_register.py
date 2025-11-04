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
        max-width: 100%;
        padding-top: 1rem;
        padding-right: 4rem;
        padding-left: 4rem;
        padding-bottom: 1rem;
    }
    div[data-testid="stHorizontalBlock"] { padding-left: 1rem; }
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
category_tab, product_tab, partner_tab, admin_tab = st.tabs(
    ["카테고리 등록", "품목 등록", "거래처 등록", "관리자 등록"]
)

# -------------------------------
# 카테고리 등록 탭
# -------------------------------
with category_tab:
    st.subheader("카테고리 등록")
    with st.form("category_form", clear_on_submit=True):
        form_col1, form_col2, form_col3 = st.columns([2, 3, 1])
        with form_col1:
            st.caption("코드번호")
            cat_code = st.text_input("코드번호", key="cat_code_input", label_visibility="collapsed", placeholder="cat_001")
        with form_col2:
            st.caption("카테고리명")
            cat_name = st.text_input("카테고리명", key="cat_name_input", label_visibility="collapsed", placeholder="원두")
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
                st.session_state.categories.append({"code": code, "name": name})
                st.session_state.category_success = True
                st.rerun()
    
    # 성공 메시지 표시
    if st.session_state.get("category_success", False):
        st.success("✅ 카테고리가 성공적으로 등록되었습니다!")
        st.session_state.category_success = False

# -------------------------------
# 품목 등록 탭
# -------------------------------
with product_tab:
    st.subheader("품목 등록")
    
    default_code = ""
    default_cat = ""
    default_name = ""
    default_unit = ""
    default_status = True

    with st.form("product_form", clear_on_submit=True):
        r1c1, r1c2, r1c3 = st.columns([2, 3, 3])
        with r1c1:
            st.caption("코드번호")
            pr_code = st.text_input("코드번호", value=default_code, key="prod_code_input",
                                    label_visibility="collapsed", placeholder="pr_001")
        with r1c2:
            st.caption("카테고리명")
            category_names = [c["name"] for c in st.session_state.categories]
            if category_names:
                default_index = category_names.index(default_cat) if default_cat in category_names else 0
                pr_category = st.selectbox("카테고리명", options=category_names, index=default_index,
                                           key="prod_category_select", label_visibility="collapsed")
            else:
                pr_category = st.text_input("카테고리명", value=default_cat, key="prod_category_input_fallback",
                                            label_visibility="collapsed", placeholder="원두")
                st.info("카테고리를 먼저 등록하면 여기에서 선택할 수 있습니다.")
        with r1c3:
            st.caption("품목 명")
            pr_name = st.text_input("품목 명", value=default_name, key="prod_name_input",
                                    label_visibility="collapsed", placeholder="디카페인 원두")

        r2c1, r2c2, r2c3, r2c4 = st.columns([2, 2, 2, 1])
        with r2c1:
            st.caption("입고 단위")
            unit_options = ["병", "박스", "kg", "갯수", "기타"]
            default_unit_index = unit_options.index(default_unit) if default_unit in unit_options else 0
            pr_unit = st.selectbox("입고 단위", options=unit_options, index=default_unit_index,
                                   key="prod_unit_select", label_visibility="collapsed")
        with r2c2:
            st.caption("상태")
            default_status_label = "사용" if default_status else "단종"
            pr_status = st.selectbox("", options=["사용", "단종"],
                                     index=(0 if default_status_label == "사용" else 1),
                                     label_visibility="collapsed")
        with r2c3:
            st.caption("안전재고")
            pr_safety = st.number_input("안전재고", min_value=0, step=1, value=0,
                                        key="prod_safety_input", label_visibility="collapsed")
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
                    st.session_state.products.append({
                        "code": code, "category": cat, "name": name, "unit": unit,
                        "status": pr_status, "safety": int(pr_safety)
                    })
                    st.session_state.product_success = True
                    st.rerun()
    
    # 성공 메시지 표시
    if st.session_state.get("product_success", False):
        st.success("✅ 품목이 성공적으로 등록되었습니다!")
        st.session_state.product_success = False

# -------------------------------
# 거래처 등록 탭
# -------------------------------
with partner_tab:
    st.subheader("거래처 등록")

    with st.form("partner_form", clear_on_submit=True):
        form_col1, form_col2, form_col3, form_col4, form_col5, form_col6 = st.columns([1.5, 2, 2, 2, 3, 1])
        with form_col1:
            st.caption("거래처 코드")
            p_code = st.text_input("거래처 코드", key="p_code_input", label_visibility="collapsed", placeholder="P001")
        with form_col2:
            st.caption("거래처명")
            p_name = st.text_input("거래처명", key="p_name_input", label_visibility="collapsed", placeholder="○○커피")
        with form_col3:
            st.caption("사업자번호")
            p_bus = st.text_input("사업자번호", key="p_bus_input", label_visibility="collapsed", placeholder="123-45-67890")
        with form_col4:
            st.caption("대표자 이름")
            p_rep = st.text_input("대표자 이름", key="p_rep_input", label_visibility="collapsed", placeholder="홍길동")
        with form_col5:
            st.caption("주소")
            p_addr = st.text_input("주소", key="p_addr_input", label_visibility="collapsed", placeholder="서울시 강남구...")
        with form_col6:
            st.markdown("<div style='height: 37px'></div>", unsafe_allow_html=True)
            partner_submitted = st.form_submit_button("등록", use_container_width=True)

        if partner_submitted:
            if not p_code or not p_name:
                st.error("거래처 코드와 거래처명은 필수 입력 항목입니다.")
            elif any(p["code"] == p_code for p in st.session_state.partners):
                st.error("이미 존재하는 거래처 코드입니다.")
            elif p_bus and not re.match(r'^[0-9\-]+$', p_bus):
                st.error("사업자번호는 숫자와 하이픈(-)만 입력 가능합니다.")
            elif p_rep and not re.match(r'^[가-힣a-zA-Z\s]+$', p_rep):
                st.error("대표자 이름은 한글과 영문만 입력 가능합니다.")
            else:
                st.session_state.partners.append({
                    "code": p_code, "name": p_name, "business_number": p_bus,
                    "representative": p_rep, "address": p_addr
                })
                st.session_state.partner_success = True
                st.rerun()
    
    # 성공 메시지 표시
    if st.session_state.get("partner_success", False):
        st.success("✅ 거래처가 성공적으로 등록되었습니다!")
        st.session_state.partner_success = False

# -------------------------------
# 관리자 등록 탭
# -------------------------------
with admin_tab:
    st.subheader("관리자 등록")

    with st.form("admin_form", clear_on_submit=True):
        form_col1, form_col2, form_col3, form_col4, form_col5, form_col6, form_col7, form_col8 = st.columns([1.2, 1, 1.2, 1.5, 1.5, 1.2, 1.5, 1.2])
        with form_col1:
            st.caption("사번번호")
            emp_no = st.text_input("사번번호", key="admin_emp_no", label_visibility="collapsed", placeholder="EMP001")
        with form_col2:
            st.caption("이름")
            name = st.text_input("이름", key="admin_name", label_visibility="collapsed", placeholder="홍길동")
        with form_col3:
            st.caption("성별")
            gender = st.selectbox("성별", ["남성", "여성"], key="admin_gender", label_visibility="collapsed")
        with form_col4:
            st.caption("이메일")
            email = st.text_input("이메일", key="admin_email", label_visibility="collapsed", placeholder="hong@example.com")
        with form_col5:
            st.caption("전화번호")
            phone = st.text_input("전화번호", key="admin_phone", label_visibility="collapsed", placeholder="010-1234-5678")
        with form_col6:
            st.caption("직급")
            position = st.selectbox("직급", ["직원", "매니저", "파트타이머"], key="admin_position", label_visibility="collapsed")
        with form_col7:
            st.caption("관리 종류")
            management_type = st.selectbox("관리 종류", ["출/입고 관리", "청소", "손님 응대", "음료 제조", "음식 제조", "기타"], key="admin_management", label_visibility="collapsed")
        with form_col8:
            st.caption("재직현황")
            status = st.selectbox("재직현황", ["재직", "퇴사", "휴직"], key="admin_status", label_visibility="collapsed")

        st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
        admin_submitted = st.form_submit_button("등록", use_container_width=True)

        if admin_submitted:
            if not emp_no or not name:
                st.error("사번번호와 이름은 필수 입력 항목입니다.")
            elif any(a["emp_no"] == emp_no for a in st.session_state.admins):
                st.error("이미 존재하는 사번번호입니다.")
            else:
                st.session_state.admins.append({
                    "emp_no": emp_no, "name": name, "gender": gender, "email": email, "phone": phone,
                    "position": position, "management_type": management_type, "status": status
                })
                st.session_state.admin_success = True
                st.rerun()
    
    # 성공 메시지 표시
    if st.session_state.get("admin_success", False):
        st.success("✅ 관리자가 성공적으로 등록되었습니다!")
        st.session_state.admin_success = False

