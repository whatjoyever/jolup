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
st.set_page_config(page_title="목록 조회/수정", page_icon="⚙️", layout="wide")
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
</style>
""", unsafe_allow_html=True)

# -------------------------------
# 세션 상태 초기화
# -------------------------------
if "categories" not in st.session_state:
    st.session_state.categories = []
if "category_selected" not in st.session_state:
    st.session_state.category_selected = set()
if "category_edit_mode" not in st.session_state:
    st.session_state.category_edit_mode = False

if "products" not in st.session_state:
    st.session_state.products = []
if "product_selected" not in st.session_state:
    st.session_state.product_selected = set()
if "product_edit_mode" not in st.session_state:
    st.session_state.product_edit_mode = False

if "partners" not in st.session_state:
    st.session_state.partners = []
if "partner_selected" not in st.session_state:
    st.session_state.partner_selected = set()
if "partner_edit_mode" not in st.session_state:
    st.session_state.partner_edit_mode = False

if "admins" not in st.session_state:
    st.session_state.admins = []
if "admin_selected" not in st.session_state:
    st.session_state.admin_selected = set()
if "admin_edit_mode" not in st.session_state:
    st.session_state.admin_edit_mode = False


# -------------------------------
# 헤더 & 뒤로가기 & 신규 등록 버튼
# -------------------------------
title_col, button_col1, button_col2 = st.columns([4, 1, 1])
with title_col:
    st.title("목록 조회/수정")
with button_col1:
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
    if st.button("← 뒤로가기", use_container_width=True, key="back_button"):
        st.switch_page("pages/info.py")
with button_col2:
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
    if st.button("+ 신규 등록", use_container_width=True, key="new_register_button"):
        st.switch_page("pages/info_register.py")

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# -------------------------------
# 탭 구조
# -------------------------------
category_tab, product_tab, partner_tab, admin_tab = st.tabs(
    ["카테고리 목록", "품목 목록", "거래처 목록", "관리자 목록"]
)

# -------------------------------
# 카테고리 목록 탭
# -------------------------------
with category_tab:
    # 검색 섹션 (Form 형태)
    st.markdown("### 🔍 검색")
    with st.form("category_search_form", clear_on_submit=False):
        cat_search = st.text_input("검색", key="cat_search", placeholder="코드번호 또는 카테고리명 입력")
        search_submitted = st.form_submit_button("검색", use_container_width=True, type="primary")
    
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    
    # 필터링된 카테고리 목록
    filtered_categories = st.session_state.categories
    if cat_search and cat_search.strip():
        search_term = cat_search.strip().lower()
        filtered_categories = [c for c in filtered_categories 
                              if search_term in c["code"].lower() 
                              or search_term in c["name"].lower()]
    
    with st.form("category_list_form"):
        if st.session_state.category_edit_mode:
            title_col, btn_col1, btn_col2, btn_col3 = st.columns([5, 1, 1, 1])
            with title_col:
                st.subheader("카테고리 목록")
            with btn_col1:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("선택 삭제", use_container_width=True):
                    if not st.session_state.category_selected:
                        st.info("삭제할 항목을 선택하세요.")
                    else:
                        for i in sorted(st.session_state.category_selected, reverse=True):
                            if 0 <= i < len(st.session_state.categories):
                                st.session_state.categories.pop(i)
                        st.session_state.category_selected = set()
                        st.success("선택한 항목을 삭제했습니다.")
                        st.rerun()
            with btn_col2:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("전체 삭제", use_container_width=True):
                    st.session_state.categories = []
                    st.session_state.category_selected = set()
                    st.success("전체 항목을 삭제했습니다.")
                    st.rerun()
            with btn_col3:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("저장", use_container_width=True):
                    for idx, row in enumerate(st.session_state.categories):
                        new_code = st.session_state.get(f"cat_code_{idx}", row["code"]).strip()
                        new_name = st.session_state.get(f"cat_name_{idx}", row["name"]).strip()
                        if any(c["code"] == new_code and i != idx for i, c in enumerate(st.session_state.categories)):
                            st.error(f"'{new_code}'는 이미 존재하는 코드번호입니다.")
                        else:
                            st.session_state.categories[idx] = {"code": new_code, "name": new_name}
                    st.session_state.category_edit_mode = False
                    st.success("저장되었습니다.")
                    st.rerun()
        else:
            title_col, btn_col = st.columns([5, 1])
            with title_col:
                st.subheader("카테고리 목록")
            with btn_col:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("수정", use_container_width=True):
                    st.session_state.category_edit_mode = True
                    st.rerun()

        if len(st.session_state.categories) == 0:
            st.warning("등록된 카테고리가 없습니다")
            st.form_submit_button("", use_container_width=True, help="")
        elif len(filtered_categories) == 0:
            st.warning("검색 결과가 없습니다")
            st.form_submit_button("", use_container_width=True, help="")
        else:
            if cat_search:
                st.info(f"검색 결과: {len(filtered_categories)}개")
            st.markdown("""
            <div style="max-height: 400px; overflow-y: auto;">
            """, unsafe_allow_html=True)

            for filtered_cat in filtered_categories:
                # 원본 인덱스 찾기
                original_idx = next(i for i, c in enumerate(st.session_state.categories) if c == filtered_cat)
                row = st.session_state.categories[original_idx]
                cat_col1, cat_col2, cat_col3 = st.columns([2, 3, 1])
                with cat_col1:
                    st.caption("코드번호")
                    st.text_input("코드번호", value=row["code"], key=f"cat_code_{original_idx}",
                                  disabled=not st.session_state.category_edit_mode, label_visibility="collapsed")
                with cat_col2:
                    st.caption("카테고리명")
                    st.text_input("카테고리명", value=row["name"], key=f"cat_name_{original_idx}",
                                  disabled=not st.session_state.category_edit_mode, label_visibility="collapsed")
                with cat_col3:
                    st.caption("\u00A0")
                    st.markdown("<div style='height: 37px'></div>", unsafe_allow_html=True)
                    checked = st.checkbox("", key=f"cat_sel_{original_idx}")
                    if checked:
                        st.session_state.category_selected.add(original_idx)
                    else:
                        st.session_state.category_selected.discard(original_idx)

            st.markdown("</div>", unsafe_allow_html=True)

# -------------------------------
# 품목 목록 탭
# -------------------------------
with product_tab:
    # 검색 섹션 (Form 형태 - 통합 검색)
    st.markdown("### 🔍 검색 및 필터")
    with st.form("product_search_form", clear_on_submit=False):
        product_search = st.text_input("검색", key="product_search", 
                                       placeholder="코드번호, 카테고리명, 품목명, 단위, 상태 등 모든 항목으로 검색 가능")
        search_prod_col1, search_prod_col2, search_prod_col3 = st.columns([1, 1, 1])
        with search_prod_col1:
            # 카테고리 필터 추가
            category_options = ["전체"] + list(set([p.get("category", "") for p in st.session_state.products if p.get("category")]))
            category_filter = st.selectbox("카테고리 필터", options=category_options, 
                                           key="category_filter_search", index=0)
        with search_prod_col2:
            unit_search = st.selectbox("단위 필터", options=["전체", "병", "박스", "kg", "갯수", "기타"], 
                                        key="unit_search", index=0)
        with search_prod_col3:
            status_search = st.selectbox("상태 필터", options=["전체", "사용", "단종"], 
                                         key="status_search", index=0)
        search_submitted = st.form_submit_button("검색", use_container_width=True, type="primary")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    
    # 전체 품목 수 표시
    total_count = len(st.session_state.products)
    if total_count > 0:
        st.caption(f"📦 총 등록된 품목: {total_count}개")
    
    # 필터링된 품목 목록
    filtered_products = list(st.session_state.products)  # 리스트 복사본 생성
    
    # 검색어 필터 (모든 필드 검색)
    if product_search and product_search.strip():
        search_term = product_search.strip().lower()
        filtered_products = [p for p in filtered_products 
                            if search_term in p.get("code", "").lower() 
                            or search_term in p.get("category", "").lower()
                            or search_term in p.get("name", "").lower()
                            or search_term in p.get("unit", "").lower()
                            or search_term in p.get("status", "").lower()
                            or search_term in str(p.get("safety", "")).lower()]
    
    # 카테고리 필터
    if category_filter and category_filter != "전체":
        filtered_products = [p for p in filtered_products if p.get("category") == category_filter]
    
    # 단위 필터
    if unit_search and unit_search != "전체":
        filtered_products = [p for p in filtered_products if p.get("unit") == unit_search]
    
    # 상태 필터 (기본값: "사용"으로 등록되므로 "전체"일 때는 모든 상태 표시)
    if status_search and status_search != "전체":
        filtered_products = [p for p in filtered_products if p.get("status") == status_search]

    with st.form("product_list_form"):
        if st.session_state.product_edit_mode:
            title_col, btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([5, 1, 1, 1, 1])
            with title_col:
                st.subheader("품목 목록")
            with btn_col1:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("선택 삭제", use_container_width=True):
                    if not st.session_state.product_selected:
                        st.info("삭제할 항목을 선택하세요.")
                    else:
                        for i in sorted(st.session_state.product_selected, reverse=True):
                            if 0 <= i < len(st.session_state.products):
                                st.session_state.products.pop(i)
                        st.session_state.product_selected = set()
                        st.success("선택한 항목을 삭제했습니다.")
                        st.rerun()
            with btn_col2:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("전체 삭제", use_container_width=True):
                    st.session_state.products = []
                    st.session_state.product_selected = set()
                    st.success("전체 항목을 삭제했습니다.")
                    st.rerun()
            with btn_col3:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("저장", use_container_width=True):
                    for idx, row in enumerate(st.session_state.products):
                        new_code = st.session_state.get(f"prod_code_{idx}", row["code"]).strip()
                        new_name = st.session_state.get(f"prod_name_{idx}", row["name"]).strip()
                        new_unit = st.session_state.get(f"prod_unit_{idx}", row["unit"]).strip()
                        new_status = st.session_state.get(f"prod_status_{idx}", row["status"]).strip()
                        new_safety = int(st.session_state.get(f"prod_safety_{idx}", row.get("safety", 0)))

                        if any(p["code"] == new_code and i != idx for i, p in enumerate(st.session_state.products)):
                            st.error(f"'{new_code}'는 이미 존재하는 코드번호입니다.")
                        else:
                            st.session_state.products[idx] = {
                                "code": new_code, "category": row["category"], "name": new_name,
                                "unit": new_unit, "status": new_status, "safety": new_safety
                            }
                    st.session_state.product_edit_mode = False
                    st.success("저장되었습니다.")
                    st.rerun()
            with btn_col4:
                st.write("")
        else:
            title_col, btn_col = st.columns([5, 1])
            with title_col:
                st.subheader("품목 목록")
            with btn_col:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("수정", use_container_width=True):
                    st.session_state.product_edit_mode = True
                    st.rerun()

        # 디버깅: 세션 상태 확인
        if len(st.session_state.products) == 0:
            st.warning("등록된 품목이 없습니다")
            st.info("💡 품목 등록 페이지에서 품목을 먼저 등록해주세요.")
            st.form_submit_button("", use_container_width=True, help="")
        elif len(filtered_products) == 0:
            st.warning("검색 결과가 없습니다")
            st.info(f"💡 전체 등록된 품목 수: {len(st.session_state.products)}개")
            # 검색 조건 초기화 안내
            reset_col1, reset_col2 = st.columns([1, 1])
            with reset_col1:
                if st.button("검색 조건 초기화", key="reset_search", use_container_width=True):
                    st.session_state.product_search = ""
                    st.session_state.unit_search = "전체"
                    st.session_state.status_search = "전체"
                    st.rerun()
            with reset_col2:
                st.form_submit_button("", use_container_width=True, help="")
        else:
            if product_search or (unit_search and unit_search != "전체") or (status_search and status_search != "전체"):
                st.info(f"검색 결과: {len(filtered_products)}개")
            
            st.markdown("""
            <div style="max-height: 400px; overflow-y: auto;">
            """, unsafe_allow_html=True)

            for filtered_idx, pr in enumerate(filtered_products):
                original_idx = next(i for i, p in enumerate(st.session_state.products) if p == pr)
                
                # 카테고리 목록과 같은 카드 형태
                prod_col1, prod_col2, prod_col3, prod_col4, prod_col5, prod_col6, prod_col7 = st.columns([1.5, 2.5, 1.2, 1.2, 1.2, 1.2, 1])
                
                with prod_col1:
                    st.caption("코드번호")
                    st.text_input("코드번호", value=pr["code"], key=f"prod_code_{original_idx}",
                                  disabled=not st.session_state.product_edit_mode, label_visibility="collapsed")
                
                with prod_col2:
                    st.caption("품목명")
                    st.text_input("품목명", value=pr["name"], key=f"prod_name_{original_idx}",
                                  disabled=not st.session_state.product_edit_mode, label_visibility="collapsed")
                
                with prod_col3:
                    st.caption("단위")
                    if st.session_state.product_edit_mode:
                        unit_options = ["병", "박스", "kg", "갯수", "기타"]
                        current_unit_index = unit_options.index(pr.get("unit", "병")) if pr.get("unit") in unit_options else 0
                        st.selectbox("단위", options=unit_options, index=current_unit_index,
                                     key=f"prod_unit_{original_idx}", label_visibility="collapsed")
                    else:
                        st.text_input("단위", value=pr.get("unit", ""), key=f"prod_unit_{original_idx}",
                                      disabled=True, label_visibility="collapsed")
                
                with prod_col4:
                    st.caption("상태")
                    if st.session_state.product_edit_mode:
                        st.selectbox("상태", options=["사용", "단종"],
                                     index=(0 if pr.get("status") == "사용" else 1),
                                     key=f"prod_status_{original_idx}", label_visibility="collapsed")
                    else:
                        st.text_input("상태", value=pr.get("status", ""), key=f"prod_status_{original_idx}",
                                      disabled=True, label_visibility="collapsed")
                
                with prod_col5:
                    st.caption("안전재고")
                    if st.session_state.product_edit_mode:
                        st.number_input("안전재고", min_value=0, step=1, value=int(pr.get("safety", 0)),
                                        key=f"prod_safety_{original_idx}", label_visibility="collapsed")
                    else:
                        st.text_input("안전재고", value=str(pr.get("safety", 0)),
                                      key=f"prod_safety_{original_idx}", disabled=True, label_visibility="collapsed")
                
                with prod_col6:
                    st.caption("카테고리")
                    st.text_input("카테고리", value=pr.get("category", ""), key=f"prod_category_{original_idx}",
                                  disabled=True, label_visibility="collapsed")
                
                with prod_col7:
                    st.caption("\u00A0")
                    st.markdown("<div style='height: 37px'></div>", unsafe_allow_html=True)
                    checked = st.checkbox("", key=f"prod_sel_{original_idx}")
                    if checked:
                        st.session_state.product_selected.add(original_idx)
                    else:
                        st.session_state.product_selected.discard(original_idx)

            st.markdown("</div>", unsafe_allow_html=True)

# -------------------------------
# 거래처 목록 탭
# -------------------------------
with partner_tab:
    # 검색 섹션 (Form 형태)
    st.markdown("### 🔍 검색")
    with st.form("partner_search_form", clear_on_submit=False):
        partner_search = st.text_input("검색", key="partner_search", 
                                       placeholder="거래처 코드, 거래처명, 사업자번호, 대표자 또는 주소 입력")
        search_submitted = st.form_submit_button("검색", use_container_width=True, type="primary")
    
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    
    # 필터링된 거래처 목록
    filtered_partners = st.session_state.partners
    if partner_search and partner_search.strip():
        search_term = partner_search.strip().lower()
        filtered_partners = [p for p in filtered_partners 
                            if search_term in p["code"].lower()
                            or search_term in p["name"].lower()
                            or search_term in p.get("business_number", "").lower()
                            or search_term in p.get("representative", "").lower()
                            or search_term in p.get("address", "").lower()]
    
    with st.form("partner_list_form"):
        if st.session_state.partner_edit_mode:
            title_col, btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([5, 1, 1, 1, 1])
            with title_col:
                st.subheader("거래처 목록")
            with btn_col1:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("선택 삭제", use_container_width=True):
                    if not st.session_state.partner_selected:
                        st.info("삭제할 항목을 선택하세요.")
                    else:
                        for i in sorted(st.session_state.partner_selected, reverse=True):
                            if 0 <= i < len(st.session_state.partners):
                                st.session_state.partners.pop(i)
                        st.session_state.partner_selected = set()
                        st.success("선택한 항목을 삭제했습니다.")
                        st.rerun()
            with btn_col2:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("전체 삭제", use_container_width=True):
                    st.session_state.partners = []
                    st.session_state.partner_selected = set()
                    st.success("전체 항목을 삭제했습니다.")
                    st.rerun()
            with btn_col3:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("저장", use_container_width=True):
                    for idx, row in enumerate(st.session_state.partners):
                        new_code = st.session_state.get(f"partner_code_{idx}", row["code"]).strip()
                        new_name = st.session_state.get(f"partner_name_{idx}", row["name"]).strip()
                        new_bus = st.session_state.get(f"partner_bus_{idx}", row["business_number"]).strip()
                        new_rep = st.session_state.get(f"partner_rep_{idx}", row["representative"]).strip()
                        new_addr = st.session_state.get(f"partner_addr_{idx}", row["address"]).strip()
                        if any(p["code"] == new_code and i != idx for i, p in enumerate(st.session_state.partners)):
                            st.error(f"'{new_code}'는 이미 존재하는 거래처 코드입니다.")
                        elif new_bus and not re.match(r'^[0-9\-]+$', new_bus):
                            st.error(f"'{new_bus}'는 올바른 사업자번호 형식이 아닙니다. 숫자와 하이픈(-)만 입력 가능합니다.")
                        elif new_rep and not re.match(r'^[가-힣a-zA-Z\s]+$', new_rep):
                            st.error(f"'{new_rep}'는 올바른 이름 형식이 아닙니다. 한글과 영문만 입력 가능합니다.")
                        else:
                            st.session_state.partners[idx] = {
                                "code": new_code, "name": new_name, "business_number": new_bus,
                                "representative": new_rep, "address": new_addr
                            }
                    st.session_state.partner_edit_mode = False
                    st.success("저장되었습니다.")
                    st.rerun()
            with btn_col4:
                st.write("")
        else:
            title_col, btn_col = st.columns([5, 1])
            with title_col:
                st.subheader("거래처 목록")
            with btn_col:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("수정", use_container_width=True):
                    st.session_state.partner_edit_mode = True
                    st.rerun()

        if len(st.session_state.partners) == 0:
            st.warning("등록된 거래처가 없습니다")
            st.form_submit_button("", use_container_width=True, help="")
        elif len(filtered_partners) == 0:
            st.warning("검색 결과가 없습니다")
            st.form_submit_button("", use_container_width=True, help="")
        else:
            if partner_search:
                st.info(f"검색 결과: {len(filtered_partners)}개")
            h1, h2, h3, h4, h5, h6 = st.columns([1.5, 2, 2, 2, 3, 0.5])
            with h1:
                st.write("**거래처 코드**")
            with h2:
                st.write("**거래처명**")
            with h3:
                st.write("**사업자번호**")
            with h4:
                st.write("**대표자**")
            with h5:
                st.write("**주소**")
            with h6:
                st.write("**선택**")

            for filtered_partner in filtered_partners:
                # 원본 인덱스 찾기
                original_idx = next(i for i, p in enumerate(st.session_state.partners) if p == filtered_partner)
                partner = st.session_state.partners[original_idx]
                c1, c2, c3, c4, c5, c6 = st.columns([1.5, 2, 2, 2, 3, 0.5])
                with c1:
                    st.text_input("거래처 코드", value=partner["code"], key=f"partner_code_{original_idx}",
                                  disabled=not st.session_state.partner_edit_mode, label_visibility="collapsed")
                with c2:
                    st.text_input("거래처명", value=partner["name"], key=f"partner_name_{original_idx}",
                                  disabled=not st.session_state.partner_edit_mode, label_visibility="collapsed")
                with c3:
                    st.text_input("사업자번호", value=partner.get("business_number", ""), key=f"partner_bus_{original_idx}",
                                  disabled=not st.session_state.partner_edit_mode, label_visibility="collapsed")
                with c4:
                    st.text_input("대표자", value=partner.get("representative", ""), key=f"partner_rep_{original_idx}",
                                  disabled=not st.session_state.partner_edit_mode, label_visibility="collapsed")
                with c5:
                    st.text_input("주소", value=partner.get("address", ""), key=f"partner_addr_{original_idx}",
                                  disabled=not st.session_state.partner_edit_mode, label_visibility="collapsed")
                with c6:
                    checked = st.checkbox("", key=f"partner_sel_{original_idx}")
                    if checked:
                        st.session_state.partner_selected.add(original_idx)
                    else:
                        st.session_state.partner_selected.discard(original_idx)

# -------------------------------
# 관리자 목록 탭
# -------------------------------
with admin_tab:
    # 검색 섹션 (Form 형태 - 통합 검색)
    st.markdown("### 🔍 검색 및 필터")
    with st.form("admin_search_form", clear_on_submit=False):
        admin_search = st.text_input("검색", key="admin_search", 
                                     placeholder="사번번호, 이름, 이메일, 전화번호, 성별, 직급, 관리종류, 재직현황 등 모든 항목으로 검색 가능")
        search_admin_col1, search_admin_col2, search_admin_col3, search_admin_col4 = st.columns([1, 1, 1, 1])
        with search_admin_col1:
            admin_gender_search = st.selectbox("성별 필터", options=["전체", "남성", "여성"], key="admin_gender_search")
        with search_admin_col2:
            admin_position_search = st.selectbox("직급 필터", options=["전체", "직원", "매니저", "파트타이머"], key="admin_position_search")
        with search_admin_col3:
            admin_mgmt_search = st.selectbox("관리 종류 필터", options=["전체", "출/입고 관리", "청소", "손님 응대", "음료 제조", "음식 제조", "기타"], key="admin_mgmt_search")
        with search_admin_col4:
            admin_status_search = st.selectbox("재직현황 필터", options=["전체", "재직", "퇴사", "휴직"], key="admin_status_search")
        search_submitted = st.form_submit_button("검색", use_container_width=True, type="primary")
    
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    
    # 필터링된 관리자 목록
    filtered_admins = st.session_state.admins
    # 통합 검색 (모든 필드 검색)
    if admin_search and admin_search.strip():
        search_term = admin_search.strip().lower()
        filtered_admins = [a for a in filtered_admins 
                          if search_term in a["emp_no"].lower()
                          or search_term in a["name"].lower()
                          or search_term in a.get("email", "").lower()
                          or search_term in a.get("phone", "").lower()
                          or search_term in a.get("gender", "").lower()
                          or search_term in a.get("position", "").lower()
                          or search_term in a.get("management_type", "").lower()
                          or search_term in a.get("status", "").lower()]
    if admin_gender_search and admin_gender_search != "전체":
        filtered_admins = [a for a in filtered_admins if a["gender"] == admin_gender_search]
    if admin_position_search and admin_position_search != "전체":
        filtered_admins = [a for a in filtered_admins if a["position"] == admin_position_search]
    if admin_mgmt_search and admin_mgmt_search != "전체":
        filtered_admins = [a for a in filtered_admins if a["management_type"] == admin_mgmt_search]
    if admin_status_search and admin_status_search != "전체":
        filtered_admins = [a for a in filtered_admins if a["status"] == admin_status_search]
    
    with st.form("admin_list_form"):
        if st.session_state.admin_edit_mode:
            title_col, btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([5, 1, 1, 1, 1])
            with title_col:
                st.subheader("관리자 목록")
            with btn_col1:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("선택 삭제", use_container_width=True):
                    if not st.session_state.admin_selected:
                        st.info("삭제할 항목을 선택하세요.")
                    else:
                        for i in sorted(st.session_state.admin_selected, reverse=True):
                            if 0 <= i < len(st.session_state.admins):
                                st.session_state.admins.pop(i)
                        st.session_state.admin_selected = set()
                        st.success("선택한 항목을 삭제했습니다.")
                        st.rerun()
            with btn_col2:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("전체 삭제", use_container_width=True):
                    st.session_state.admins = []
                    st.session_state.admin_selected = set()
                    st.success("전체 항목을 삭제했습니다.")
                    st.rerun()
            with btn_col3:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("저장", use_container_width=True):
                    for idx, row in enumerate(st.session_state.admins):
                        new_emp_no = st.session_state.get(f"admin_emp_no_{idx}", row["emp_no"]).strip()
                        new_name   = st.session_state.get(f"admin_name_{idx}", row["name"]).strip()
                        new_gender = st.session_state.get(f"admin_gender_{idx}", row["gender"])
                        new_email  = st.session_state.get(f"admin_email_{idx}", row["email"]).strip()
                        new_phone  = st.session_state.get(f"admin_phone_{idx}", row["phone"]).strip()
                        new_position = st.session_state.get(f"admin_position_{idx}", row["position"])
                        new_mgmt_type = st.session_state.get(f"admin_mgmt_type_{idx}", row["management_type"])
                        new_status = st.session_state.get(f"admin_status_{idx}", row["status"])

                        if any(a["emp_no"] == new_emp_no and i != idx for i, a in enumerate(st.session_state.admins)):
                            st.error(f"'{new_emp_no}'는 이미 존재하는 사번번호입니다.")
                        else:
                            st.session_state.admins[idx] = {
                                "emp_no": new_emp_no, "name": new_name, "gender": new_gender,
                                "email": new_email, "phone": new_phone, "position": new_position,
                                "management_type": new_mgmt_type, "status": new_status
                            }
                    st.session_state.admin_edit_mode = False
                    st.success("저장되었습니다.")
                    st.rerun()
            with btn_col4:
                st.write("")
        else:
            title_col, btn_col = st.columns([5, 1])
            with title_col:
                st.subheader("관리자 목록")
            with btn_col:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("수정", use_container_width=True):
                    st.session_state.admin_edit_mode = True
                    st.rerun()

        if len(st.session_state.admins) == 0:
            st.warning("등록된 관리자가 없습니다")
            st.form_submit_button("", use_container_width=True, help="")
        elif len(filtered_admins) == 0:
            st.warning("검색 결과가 없습니다")
            st.form_submit_button("", use_container_width=True, help="")
        else:
            if (admin_search or 
                (admin_gender_search and admin_gender_search != "전체") or 
                (admin_position_search and admin_position_search != "전체") or 
                (admin_mgmt_search and admin_mgmt_search != "전체") or 
                (admin_status_search and admin_status_search != "전체")):
                st.info(f"검색 결과: {len(filtered_admins)}개")
            h1, h2, h3, h4, h5, h6, h7, h8, h9 = st.columns([1, 1.5, 0.8, 1.5, 1.5, 1.2, 1.5, 1, 0.8])
            with h1:
                st.write("**선택**")
            with h2:
                st.write("**사번번호**")
            with h3:
                st.write("**이름**")
            with h4:
                st.write("**성별**")
            with h5:
                st.write("**연락처**")
            with h6:
                st.write("**직급**")
            with h7:
                st.write("**관리 종류**")
            with h8:
                st.write("**재직현황**")
            with h9:
                st.write("**수정**")

            for filtered_admin in filtered_admins:
                # 원본 인덱스 찾기
                original_idx = next(i for i, a in enumerate(st.session_state.admins) if a == filtered_admin)
                admin = st.session_state.admins[original_idx]
                c1, c2, c3, c4, c5, c6, c7, c8, c9 = st.columns([1, 1.5, 0.8, 1.5, 1.5, 1.2, 1.5, 1, 0.8])
                with c1:
                    checked = st.checkbox("", key=f"admin_sel_{original_idx}")
                    if checked:
                        st.session_state.admin_selected.add(original_idx)
                    else:
                        st.session_state.admin_selected.discard(original_idx)
                with c2:
                    st.text_input("사번번호", value=admin["emp_no"], key=f"admin_emp_no_{original_idx}",
                                  disabled=not st.session_state.admin_edit_mode, label_visibility="collapsed")
                with c3:
                    st.text_input("이름", value=admin["name"], key=f"admin_name_{original_idx}",
                                  disabled=not st.session_state.admin_edit_mode, label_visibility="collapsed")
                with c4:
                    if st.session_state.admin_edit_mode:
                        st.selectbox("성별", options=["남성", "여성"],
                                     index=(0 if admin["gender"] == "남성" else 1),
                                     key=f"admin_gender_{original_idx}", label_visibility="collapsed")
                    else:
                        st.text_input("성별", value=admin["gender"], key=f"admin_gender_{original_idx}",
                                      disabled=True, label_visibility="collapsed")
                with c5:
                    if st.session_state.admin_edit_mode:
                        col_email, col_phone = st.columns(2)
                        with col_email:
                            st.text_input("이메일", value=admin["email"], key=f"admin_email_{original_idx}", label_visibility="collapsed")
                        with col_phone:
                            st.text_input("전화번호", value=admin["phone"], key=f"admin_phone_{original_idx}", label_visibility="collapsed")
                    else:
                        st.text_input("연락처", value=f"{admin['email']} / {admin['phone']}",
                                      key=f"admin_contact_{original_idx}", disabled=True, label_visibility="collapsed")
                with c6:
                    if st.session_state.admin_edit_mode:
                        position_options = ["직원", "매니저", "파트타이머"]
                        pos_index = position_options.index(admin["position"]) if admin["position"] in position_options else 0
                        st.selectbox("직급", options=position_options, index=pos_index,
                                     key=f"admin_position_{original_idx}", label_visibility="collapsed")
                    else:
                        st.text_input("직급", value=admin["position"], key=f"admin_position_{original_idx}",
                                      disabled=True, label_visibility="collapsed")
                with c7:
                    if st.session_state.admin_edit_mode:
                        mgmt_options = ["출/입고 관리", "청소", "손님 응대", "음료 제조", "음식 제조", "기타"]
                        mgmt_index = mgmt_options.index(admin["management_type"]) if admin["management_type"] in mgmt_options else 0
                        st.selectbox("관리 종류", options=mgmt_options, index=mgmt_index,
                                     key=f"admin_mgmt_type_{original_idx}", label_visibility="collapsed")
                    else:
                        st.text_input("관리 종류", value=admin["management_type"], key=f"admin_mgmt_type_{original_idx}",
                                      disabled=True, label_visibility="collapsed")
                with c8:
                    if st.session_state.admin_edit_mode:
                        status_options = ["재직", "퇴사", "휴직"]
                        status_index = status_options.index(admin["status"]) if admin["status"] in status_options else 0
                        st.selectbox("재직현황", options=status_options, index=status_index,
                                     key=f"admin_status_{original_idx}", label_visibility="collapsed")
                    else:
                        st.text_input("재직현황", value=admin["status"], key=f"admin_status_{original_idx}",
                                      disabled=True, label_visibility="collapsed")
                with c9:
                    st.write("")

