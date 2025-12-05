import os, sys
import streamlit as st
import re
import pandas as pd

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
st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)

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

# 현재 선택된 탭 인덱스 저장
if "current_tab_index" not in st.session_state:
    st.session_state.current_tab_index = 1  # 기본값: 품목 목록 탭 (인덱스 1)

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

# 탭 상태 유지를 위한 JavaScript
if st.session_state.get("current_tab_index") is not None:
    tab_index = st.session_state.current_tab_index
    st.markdown(
        f"""
        <script>
        // 즉시 실행 및 DOMContentLoaded 이벤트 모두 처리
        function selectTab() {{
            setTimeout(function() {{
                var tabs = document.querySelectorAll('[data-baseweb="tab"]');
                if (tabs.length > {tab_index}) {{
                    tabs[{tab_index}].click();
                }}
            }}, 100);
        }}
        
        // 즉시 실행
        selectTab();
        
        // DOMContentLoaded 이벤트
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', selectTab);
        }}
        
        // load 이벤트
        window.addEventListener('load', selectTab);
        </script>
        """,
        unsafe_allow_html=True
    )

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
        cat_search = st.text_input(
            "검색", key="cat_search", placeholder="코드번호 또는 카테고리명 입력"
        )
        search_submitted = st.form_submit_button(
            "검색", use_container_width=True, type="primary"
        )

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # 필터링된 카테고리 목록
    filtered_categories = st.session_state.categories
    if cat_search and cat_search.strip():
        search_term = cat_search.strip().lower()
        filtered_categories = [
            c
            for c in filtered_categories
            if search_term in c["code"].lower() or search_term in c["name"].lower()
        ]

    # 버튼 영역 (form 밖)
    if st.session_state.category_edit_mode:
        title_col, btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(
            [5, 1, 1, 1, 1]
        )
        with title_col:
            st.subheader("카테고리 목록")
        with btn_col1:
            st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
            if st.button("선택 삭제", use_container_width=True, key="cat_select_delete"):
                if not st.session_state.category_selected:
                    st.info("삭제할 항목을 선택하세요.")
                else:
                    for i in sorted(
                        st.session_state.category_selected, reverse=True
                    ):
                        if 0 <= i < len(st.session_state.categories):
                            st.session_state.categories.pop(i)
                    st.session_state.category_selected = set()
                    st.success("선택한 항목을 삭제했습니다.")
                    st.rerun()

        with btn_col2:
            st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
            if st.button("전체 삭제", use_container_width=True, key="cat_all_delete"):
                st.session_state.categories = []
                st.session_state.category_selected = set()
                st.success("전체 항목을 삭제했습니다.")
                st.rerun()

        with btn_col3:
            st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
            if st.button("저장", use_container_width=True, key="cat_save"):
                st.session_state._cat_save_clicked = True

        with btn_col4:
            st.write("")
    else:
        title_col, btn_col = st.columns([5, 1])
        with title_col:
            st.subheader("카테고리 목록")
        with btn_col:
            st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
            if st.button("수정", use_container_width=True, key="cat_edit"):
                st.session_state.category_edit_mode = True
                # 카테고리 목록 탭 인덱스 저장 (인덱스 0)
                st.session_state.current_tab_index = 0
                st.rerun()

    if len(st.session_state.categories) == 0:
        st.warning("등록된 카테고리가 없습니다")
    elif len(filtered_categories) == 0:
        st.warning("검색 결과가 없습니다")
    else:
        if cat_search:
            st.info(f"검색 결과: {len(filtered_categories)}개")
        
        if not st.session_state.category_edit_mode:
            # 읽기 모드: 표 형식으로 표시
            categories_data = []
            for idx, cat in enumerate(filtered_categories, start=1):
                categories_data.append({
                    "번호": str(idx),
                    "코드번호": cat.get("code", "-"),
                    "카테고리명": cat.get("name", "-")
                })
            
            if categories_data:
                df_categories = pd.DataFrame(categories_data)
                st.dataframe(
                    df_categories,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "번호": st.column_config.TextColumn("번호", width="small"),
                        "코드번호": st.column_config.TextColumn("코드번호", width="small"),
                        "카테고리명": st.column_config.TextColumn("카테고리명", width="small")
                    }
                )
        else:
            # 수정 모드: 표 형식으로 편집 가능하게
            categories_data = []
            
            for idx, cat in enumerate(filtered_categories, start=1):
                # code 기준으로 원본 인덱스 찾기
                original_idx = next(
                    (
                        i
                        for i, c in enumerate(st.session_state.categories)
                        if c.get("code") == cat.get("code")
                    ),
                    None,
                )
                if original_idx is None:
                    continue
                
                # 체크박스 상태 확인
                is_checked = original_idx in st.session_state.category_selected
                
                categories_data.append({
                    "선택": is_checked,
                    "번호": str(idx),
                    "코드번호": cat.get("code", "-"),
                    "카테고리명": cat.get("name", "-"),
                    "_original_idx": original_idx  # 원본 인덱스 저장용 (표시 안 함)
                })
            
            if categories_data:
                df_categories = pd.DataFrame(categories_data)
                
                # 편집 가능한 표
                edited_df = st.data_editor(
                    df_categories,
                    use_container_width=True,
                    hide_index=True,
                    key="category_data_editor",
                    column_config={
                        "선택": st.column_config.CheckboxColumn("선택", width="small"),
                        "번호": st.column_config.TextColumn("번호", width="small", disabled=True),
                        "코드번호": st.column_config.TextColumn("코드번호", width="small"),
                        "카테고리명": st.column_config.TextColumn("카테고리명", width="small"),
                        "_original_idx": st.column_config.NumberColumn("_original_idx", width="small", disabled=True)
                    },
                    num_rows="dynamic"
                )
                
                # 체크박스 상태 업데이트
                for _, row in edited_df.iterrows():
                    original_idx = int(row["_original_idx"])
                    if row["선택"]:
                        st.session_state.category_selected.add(original_idx)
                    else:
                        st.session_state.category_selected.discard(original_idx)
                
                # 저장 버튼이 클릭되었을 때 처리
                if st.session_state.get("_cat_save_clicked", False):
                    st.session_state._cat_save_clicked = False  # 플래그 리셋
                    has_error = False
                    
                    # st.data_editor의 최신 반환값 직접 사용 (편집된 내용 반영)
                    for _, row in edited_df.iterrows():
                        original_idx = int(row["_original_idx"])
                        if 0 <= original_idx < len(st.session_state.categories):
                            new_code = str(row["코드번호"]).strip()
                            new_name = str(row["카테고리명"]).strip()
                            
                            # 코드번호 중복 체크
                            if any(
                                c["code"] == new_code and i != original_idx
                                for i, c in enumerate(st.session_state.categories)
                            ):
                                st.error(f"'{new_code}'는 이미 존재하는 코드번호입니다.")
                                has_error = True
                            else:
                                st.session_state.categories[original_idx] = {
                                    "code": new_code,
                                    "name": new_name,
                                }
                    
                    if not has_error:
                        st.session_state.category_edit_mode = False
                        st.session_state.current_tab_index = 0
                        st.success("저장되었습니다.")
                        st.rerun()

# -------------------------------
# 품목 목록 탭
# -------------------------------
with product_tab:
    # 검색 섹션 (Form 형태 - 통합 검색)
    st.markdown("### 🔍 검색 및 필터")
    with st.form("product_search_form", clear_on_submit=False):
        product_search = st.text_input(
            "검색",
            key="product_search",
            placeholder="코드번호, 카테고리명, 품목명, 단위, 상태 등 모든 항목으로 검색 가능",
        )
        search_prod_col1, search_prod_col2, search_prod_col3 = st.columns([1, 1, 1])
        with search_prod_col1:
            # 카테고리 필터 추가
            category_options = ["전체"] + list(
                set(
                    [
                        p.get("category", "")
                        for p in st.session_state.products
                        if p.get("category")
                    ]
                )
            )
            category_filter = st.selectbox(
                "카테고리 필터",
                options=category_options,
                key="category_filter_search",
                index=0,
            )
        with search_prod_col2:
            unit_search = st.selectbox(
                "단위 필터",
                options=["전체", "병", "박스", "kg", "갯수", "기타"],
                key="unit_search",
                index=0,
            )
        with search_prod_col3:
            status_search = st.selectbox(
                "상태 필터",
                options=["전체", "사용", "단종"],
                key="status_search",
                index=0,
            )
        search_submitted = st.form_submit_button(
            "검색", use_container_width=True, type="primary"
        )

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
        filtered_products = [
            p
            for p in filtered_products
            if search_term in p.get("code", "").lower()
            or search_term in p.get("category", "").lower()
            or search_term in p.get("name", "").lower()
            or search_term in p.get("unit", "").lower()
            or search_term in p.get("status", "").lower()
            or search_term in str(p.get("safety", "")).lower()
        ]

    # 카테고리 필터
    if category_filter and category_filter != "전체":
        filtered_products = [
            p for p in filtered_products if p.get("category") == category_filter
        ]

    # 단위 필터
    if unit_search and unit_search != "전체":
        filtered_products = [
            p for p in filtered_products if p.get("unit") == unit_search
        ]

    # 상태 필터 (기본값: "사용"으로 등록되므로 "전체"일 때는 모든 상태 표시)
    if status_search and status_search != "전체":
        filtered_products = [
            p for p in filtered_products if p.get("status") == status_search
        ]

    # 버튼 영역 (form 밖)
    if st.session_state.product_edit_mode:
        title_col, btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(
            [5, 1, 1, 1, 1]
        )
        with title_col:
            st.subheader("품목 목록")
        with btn_col1:
            st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
            if st.button("선택 삭제", use_container_width=True, key="prod_select_delete"):
                if not st.session_state.product_selected:
                    st.info("삭제할 항목을 선택하세요.")
                else:
                    for i in sorted(
                        st.session_state.product_selected, reverse=True
                    ):
                        if 0 <= i < len(st.session_state.products):
                            st.session_state.products.pop(i)
                    st.session_state.product_selected = set()
                    st.success("선택한 항목을 삭제했습니다.")
                    st.rerun()

        with btn_col2:
            st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
            if st.button("전체 삭제", use_container_width=True, key="prod_all_delete"):
                st.session_state.products = []
                st.session_state.product_selected = set()
                st.success("전체 항목을 삭제했습니다.")
                st.rerun()

        with btn_col3:
            st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
            if st.button("저장", use_container_width=True, key="prod_save"):
                st.session_state._save_clicked = True

        with btn_col4:
            st.write("")
    else:
        title_col, btn_col1, btn_col2 = st.columns([5, 1, 1])
        with title_col:
            st.subheader("품목 목록")
        with btn_col1:
            st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
            if st.button("수정", use_container_width=True, key="prod_edit"):
                st.session_state.product_edit_mode = True
                # 품목 목록 탭 인덱스 저장 (인덱스 1)
                st.session_state.current_tab_index = 1
                st.rerun()
        with btn_col2:
            st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
            if st.button("삭제", use_container_width=True, key="prod_delete"):
                if not st.session_state.product_selected:
                    st.info("삭제할 항목을 선택하세요.")
                else:
                    for i in sorted(
                        st.session_state.product_selected, reverse=True
                    ):
                        if 0 <= i < len(st.session_state.products):
                            st.session_state.products.pop(i)
                    st.session_state.product_selected = set()
                    st.success("선택한 항목을 삭제했습니다.")
                    st.rerun()

    # 디버깅: 세션 상태 확인
    if len(st.session_state.products) == 0:
        st.warning("등록된 품목이 없습니다")
        st.info("💡 품목 등록 페이지에서 품목을 먼저 등록해주세요.")
    elif len(filtered_products) == 0:
        st.warning("검색 결과가 없습니다")
        st.info(f"💡 전체 등록된 품목 수: {len(st.session_state.products)}개")
        # 검색 조건 초기화 안내
        reset_col1, reset_col2 = st.columns([1, 1])
        with reset_col1:
            if st.button(
                "검색 조건 초기화",
                key="reset_search",
                use_container_width=True,
            ):
                st.session_state.product_search = ""
                st.session_state.unit_search = "전체"
                st.session_state.status_search = "전체"
                st.rerun()
        with reset_col2:
            st.write("")
    else:
        if (
            product_search
            or (unit_search and unit_search != "전체")
            or (status_search and status_search != "전체")
        ):
            st.info(f"검색 결과: {len(filtered_products)}개")

        if not st.session_state.product_edit_mode:
            # 읽기 모드: 표 형식으로 표시
            products_data = []
            for idx, pr in enumerate(filtered_products, start=1):
                products_data.append({
                    "번호": str(idx),
                    "코드번호": pr.get("code", "-"),
                    "품목명": pr.get("name", "-"),
                    "카테고리": pr.get("category", "-"),
                    "단위": pr.get("unit", "-"),
                    "상태": pr.get("status", "-"),
                    "안전재고": str(pr.get("safety", 0))
                })
            
            if products_data:
                df_products = pd.DataFrame(products_data)
                st.dataframe(
                    df_products,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "번호": st.column_config.TextColumn("번호", width="small"),
                        "코드번호": st.column_config.TextColumn("코드번호", width="small"),
                        "품목명": st.column_config.TextColumn("품목명", width="medium"),
                        "카테고리": st.column_config.TextColumn("카테고리", width="small"),
                        "단위": st.column_config.TextColumn("단위", width="small"),
                        "상태": st.column_config.TextColumn("상태", width="small"),
                        "안전재고": st.column_config.TextColumn("안전재고", width="small")
                    }
                )
        else:
            # 수정 모드: 표 형식으로 편집 가능하게
            # 편집 가능한 표 형식으로 표시
            products_data = []
            
            for idx, pr in enumerate(filtered_products, start=1):
                # code 기준으로 원본 인덱스 찾기
                original_idx = next(
                    (
                        i
                        for i, p in enumerate(st.session_state.products)
                        if p.get("code") == pr.get("code")
                    ),
                    None,
                )
                if original_idx is None:
                    continue
                
                # 체크박스 상태 확인
                is_checked = original_idx in st.session_state.product_selected
                
                products_data.append({
                    "선택": is_checked,
                    "번호": str(idx),
                    "코드번호": pr.get("code", "-"),
                    "품목명": pr.get("name", "-"),
                    "카테고리": pr.get("category", "-"),
                    "단위": pr.get("unit", "-"),
                    "상태": pr.get("status", "-"),
                    "안전재고": int(pr.get("safety", 0)),
                    "_original_idx": original_idx  # 원본 인덱스 저장용 (표시 안 함)
                })
            
            if products_data:
                df_products = pd.DataFrame(products_data)
                
                # 편집 가능한 표
                edited_df = st.data_editor(
                    df_products,
                    use_container_width=True,
                    hide_index=True,
                    key="product_data_editor",
                    column_config={
                        "선택": st.column_config.CheckboxColumn("선택", width="small"),
                        "번호": st.column_config.TextColumn("번호", width="small", disabled=True),
                        "코드번호": st.column_config.TextColumn("코드번호", width="small"),
                        "품목명": st.column_config.TextColumn("품목명", width="medium"),
                        "카테고리": st.column_config.TextColumn("카테고리", width="small", disabled=True),
                        "단위": st.column_config.SelectboxColumn(
                            "단위",
                            width="small",
                            options=["병", "박스", "kg", "갯수", "기타"]
                        ),
                        "상태": st.column_config.SelectboxColumn(
                            "상태",
                            width="small",
                            options=["사용", "단종"]
                        ),
                        "안전재고": st.column_config.NumberColumn("안전재고", width="small", min_value=0),
                        "_original_idx": st.column_config.NumberColumn("_original_idx", width="small", disabled=True)
                    },
                    num_rows="dynamic"
                )
                
                # 체크박스 상태 업데이트
                for _, row in edited_df.iterrows():
                    original_idx = int(row["_original_idx"])
                    if row["선택"]:
                        st.session_state.product_selected.add(original_idx)
                    else:
                        st.session_state.product_selected.discard(original_idx)
                
                # 저장 버튼이 클릭되었을 때 처리
                if st.session_state.get("_save_clicked", False):
                    st.session_state._save_clicked = False  # 플래그 리셋
                    has_error = False
                    
                    # st.data_editor의 최신 반환값 직접 사용 (편집된 내용 반영)
                    for _, row in edited_df.iterrows():
                        original_idx = int(row["_original_idx"])
                        if 0 <= original_idx < len(st.session_state.products):
                            new_code = str(row["코드번호"]).strip()
                            new_name = str(row["품목명"]).strip()
                            new_unit = str(row["단위"]).strip()
                            new_status = str(row["상태"]).strip()
                            new_safety = int(row["안전재고"]) if pd.notna(row["안전재고"]) else 0
                            
                            # 코드번호 중복 체크
                            if any(
                                p["code"] == new_code and i != original_idx
                                for i, p in enumerate(st.session_state.products)
                            ):
                                st.error(f"'{new_code}'는 이미 존재하는 코드번호입니다.")
                                has_error = True
                            else:
                                st.session_state.products[original_idx] = {
                                    "code": new_code,
                                    "category": st.session_state.products[original_idx]["category"],
                                    "name": new_name,
                                    "unit": new_unit,
                                    "status": new_status,
                                    "safety": new_safety,
                                }
                    
                    if not has_error:
                        st.session_state.product_edit_mode = False
                        st.session_state._edited_products_data = None
                        st.session_state.current_tab_index = 1
                        st.success("저장되었습니다.")
                        st.rerun()

# -------------------------------
# 거래처 목록 탭
# -------------------------------
with partner_tab:
    # 검색 섹션 (Form 형태)
    st.markdown("### 🔍 검색")
    with st.form("partner_search_form", clear_on_submit=False):
        partner_search = st.text_input(
            "검색",
            key="partner_search",
            placeholder="거래처 코드, 거래처명, 사업자번호, 대표자 또는 주소 입력",
        )
        search_submitted = st.form_submit_button(
            "검색", use_container_width=True, type="primary"
        )

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # 필터링된 거래처 목록
    filtered_partners = st.session_state.partners
    if partner_search and partner_search.strip():
        search_term = partner_search.strip().lower()
        filtered_partners = [
            p
            for p in filtered_partners
            if search_term in p["code"].lower()
            or search_term in p["name"].lower()
            or search_term in p.get("business_number", "").lower()
            or search_term in p.get("representative", "").lower()
            or search_term in p.get("address", "").lower()
        ]

    # 버튼 영역 (form 밖)
    if st.session_state.partner_edit_mode:
        title_col, btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(
            [5, 1, 1, 1, 1]
        )
        with title_col:
            st.subheader("거래처 목록")
        with btn_col1:
            st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
            if st.button("선택 삭제", use_container_width=True, key="partner_select_delete"):
                if not st.session_state.partner_selected:
                    st.info("삭제할 항목을 선택하세요.")
                else:
                    for i in sorted(
                        st.session_state.partner_selected, reverse=True
                    ):
                        if 0 <= i < len(st.session_state.partners):
                            st.session_state.partners.pop(i)
                    st.session_state.partner_selected = set()
                    st.success("선택한 항목을 삭제했습니다.")
                    st.rerun()

        with btn_col2:
            st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
            if st.button("전체 삭제", use_container_width=True, key="partner_all_delete"):
                st.session_state.partners = []
                st.session_state.partner_selected = set()
                st.success("전체 항목을 삭제했습니다.")
                st.rerun()

        with btn_col3:
            st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
            if st.button("저장", use_container_width=True, key="partner_save"):
                st.session_state._partner_save_clicked = True

        with btn_col4:
            st.write("")
    else:
        title_col, btn_col = st.columns([5, 1])
        with title_col:
            st.subheader("거래처 목록")
        with btn_col:
            st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
            if st.button("수정", use_container_width=True, key="partner_edit"):
                # 거래처 목록 탭 인덱스 저장 (인덱스 2) - 먼저 설정
                st.session_state.current_tab_index = 2
                st.session_state.partner_edit_mode = True
                st.rerun()

    if len(st.session_state.partners) == 0:
        st.warning("등록된 거래처가 없습니다")
    elif len(filtered_partners) == 0:
        st.warning("검색 결과가 없습니다")
    else:
        if partner_search:
            st.info(f"검색 결과: {len(filtered_partners)}개")
        
        if not st.session_state.partner_edit_mode:
            # 읽기 모드: 표 형식으로 표시
            partners_data = []
            for idx, partner in enumerate(filtered_partners, start=1):
                partners_data.append({
                    "번호": str(idx),
                    "거래처 코드": partner.get("code", "-"),
                    "거래처명": partner.get("name", "-"),
                    "사업자번호": partner.get("business_number", "-"),
                    "대표자": partner.get("representative", "-"),
                    "주소": partner.get("address", "-")
                })
            
            if partners_data:
                df_partners = pd.DataFrame(partners_data)
                st.dataframe(
                    df_partners,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "번호": st.column_config.TextColumn("번호", width="small"),
                        "거래처 코드": st.column_config.TextColumn("거래처 코드", width="small"),
                        "거래처명": st.column_config.TextColumn("거래처명", width="medium"),
                        "사업자번호": st.column_config.TextColumn("사업자번호", width="medium"),
                        "대표자": st.column_config.TextColumn("대표자", width="small"),
                        "주소": st.column_config.TextColumn("주소", width="medium")
                    }
                )
        else:
            # 수정 모드: 표 형식으로 편집 가능하게
            partners_data = []
            
            for idx, partner in enumerate(filtered_partners, start=1):
                # code 기준으로 원본 인덱스 찾기
                original_idx = next(
                    (
                        i
                        for i, p in enumerate(st.session_state.partners)
                        if p.get("code") == partner.get("code")
                    ),
                    None,
                )
                if original_idx is None:
                    continue
                
                # 체크박스 상태 확인
                is_checked = original_idx in st.session_state.partner_selected
                
                partners_data.append({
                    "선택": is_checked,
                    "번호": str(idx),
                    "거래처 코드": partner.get("code", "-"),
                    "거래처명": partner.get("name", "-"),
                    "사업자번호": partner.get("business_number", "-"),
                    "대표자": partner.get("representative", "-"),
                    "주소": partner.get("address", "-"),
                    "_original_idx": original_idx  # 원본 인덱스 저장용 (표시 안 함)
                })
            
            if partners_data:
                df_partners = pd.DataFrame(partners_data)
                
                # 편집 가능한 표
                edited_df = st.data_editor(
                    df_partners,
                    use_container_width=True,
                    hide_index=True,
                    key="partner_data_editor",
                    column_config={
                        "선택": st.column_config.CheckboxColumn("선택", width="small"),
                        "번호": st.column_config.TextColumn("번호", width="small", disabled=True),
                        "거래처 코드": st.column_config.TextColumn("거래처 코드", width="small"),
                        "거래처명": st.column_config.TextColumn("거래처명", width="medium"),
                        "사업자번호": st.column_config.TextColumn("사업자번호", width="medium"),
                        "대표자": st.column_config.TextColumn("대표자", width="small"),
                        "주소": st.column_config.TextColumn("주소", width="medium"),
                        "_original_idx": st.column_config.NumberColumn("_original_idx", width="small", disabled=True)
                    },
                    num_rows="dynamic"
                )
                
                # 체크박스 상태 업데이트
                for _, row in edited_df.iterrows():
                    original_idx = int(row["_original_idx"])
                    if row["선택"]:
                        st.session_state.partner_selected.add(original_idx)
                    else:
                        st.session_state.partner_selected.discard(original_idx)
                
                # 저장 버튼이 클릭되었을 때 처리
                if st.session_state.get("_partner_save_clicked", False):
                    st.session_state._partner_save_clicked = False  # 플래그 리셋
                    has_error = False
                    
                    # st.data_editor의 최신 반환값 직접 사용 (편집된 내용 반영)
                    for _, row in edited_df.iterrows():
                        original_idx = int(row["_original_idx"])
                        if 0 <= original_idx < len(st.session_state.partners):
                            new_code = str(row["거래처 코드"]).strip()
                            new_name = str(row["거래처명"]).strip()
                            new_bus = str(row["사업자번호"]).strip() if pd.notna(row["사업자번호"]) else ""
                            new_rep = str(row["대표자"]).strip() if pd.notna(row["대표자"]) else ""
                            new_addr = str(row["주소"]).strip() if pd.notna(row["주소"]) else ""
                            
                            # 코드번호 중복 체크
                            if any(
                                p["code"] == new_code and i != original_idx
                                for i, p in enumerate(st.session_state.partners)
                            ):
                                st.error(f"'{new_code}'는 이미 존재하는 거래처 코드입니다.")
                                has_error = True
                            elif new_bus and not re.match(r"^[0-9\-]+$", new_bus):
                                st.error(
                                    f"'{new_bus}'는 올바른 사업자번호 형식이 아닙니다. 숫자와 하이픈(-)만 입력 가능합니다."
                                )
                                has_error = True
                            elif new_rep and not re.match(
                                r"^[가-힣a-zA-Z\s]+$", new_rep
                            ):
                                st.error(
                                    f"'{new_rep}'는 올바른 이름 형식이 아닙니다. 한글과 영문만 입력 가능합니다."
                                )
                                has_error = True
                            else:
                                st.session_state.partners[original_idx] = {
                                    "code": new_code,
                                    "name": new_name,
                                    "business_number": new_bus,
                                    "representative": new_rep,
                                    "address": new_addr,
                                }
                    
                    if not has_error:
                        st.session_state.partner_edit_mode = False
                        st.session_state.current_tab_index = 2
                        st.success("저장되었습니다.")
                        st.rerun()

# -------------------------------
# 관리자 목록 탭
# -------------------------------
with admin_tab:
    # 검색 섹션 (Form 형태 - 통합 검색)
    st.markdown("### 🔍 검색 및 필터")
    with st.form("admin_search_form", clear_on_submit=False):
        admin_search = st.text_input(
            "검색",
            key="admin_search",
            placeholder="사번번호, 이름, 이메일, 전화번호, 성별, 직급, 관리종류, 재직현황 등 모든 항목으로 검색 가능",
        )
        search_admin_col1, search_admin_col2, search_admin_col3, search_admin_col4 = st.columns(
            [1, 1, 1, 1]
        )
        with search_admin_col1:
            admin_gender_search = st.selectbox(
                "성별 필터", options=["전체", "남성", "여성"], key="admin_gender_search"
            )
        with search_admin_col2:
            admin_position_search = st.selectbox(
                "직급 필터",
                options=["전체", "직원", "매니저", "파트타이머"],
                key="admin_position_search",
            )
        with search_admin_col3:
            admin_mgmt_search = st.selectbox(
                "관리 종류 필터",
                options=["전체", "출/입고 관리", "청소", "손님 응대", "음료 제조", "음식 제조", "기타"],
                key="admin_mgmt_search",
            )
        with search_admin_col4:
            admin_status_search = st.selectbox(
                "재직현황 필터",
                options=["전체", "재직", "퇴사", "휴직"],
                key="admin_status_search",
            )
        search_submitted = st.form_submit_button(
            "검색", use_container_width=True, type="primary"
        )

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # 필터링된 관리자 목록
    filtered_admins = st.session_state.admins
    # 통합 검색 (모든 필드 검색)
    if admin_search and admin_search.strip():
        search_term = admin_search.strip().lower()
        filtered_admins = [
            a
            for a in filtered_admins
            if search_term in a["emp_no"].lower()
            or search_term in a["name"].lower()
            or search_term in a.get("email", "").lower()
            or search_term in a.get("phone", "").lower()
            or search_term in a.get("gender", "").lower()
            or search_term in a.get("position", "").lower()
            or search_term in a.get("management_type", "").lower()
            or search_term in a.get("status", "").lower()
        ]
    if admin_gender_search and admin_gender_search != "전체":
        filtered_admins = [
            a for a in filtered_admins if a["gender"] == admin_gender_search
        ]
    if admin_position_search and admin_position_search != "전체":
        filtered_admins = [
            a for a in filtered_admins if a["position"] == admin_position_search
        ]
    if admin_mgmt_search and admin_mgmt_search != "전체":
        filtered_admins = [
            a
            for a in filtered_admins
            if a["management_type"] == admin_mgmt_search
        ]
    if admin_status_search and admin_status_search != "전체":
        filtered_admins = [
            a for a in filtered_admins if a["status"] == admin_status_search
        ]

    with st.form("admin_list_form"):
        if st.session_state.admin_edit_mode:
            title_col, btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(
                [5, 1, 1, 1, 1]
            )
            with title_col:
                st.subheader("관리자 목록")
            with btn_col1:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("선택 삭제", use_container_width=True):
                    if not st.session_state.admin_selected:
                        st.info("삭제할 항목을 선택하세요.")
                    else:
                        for i in sorted(
                            st.session_state.admin_selected, reverse=True
                        ):
                            if 0 <= i < len(st.session_state.admins):
                                st.session_state.admins.pop(i)
                        st.session_state.admin_selected = set()
                        st.success("선택한 항목을 삭제했습니다.")

            with btn_col2:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("전체 삭제", use_container_width=True):
                    st.session_state.admins = []
                    st.session_state.admin_selected = set()
                    st.success("전체 항목을 삭제했습니다.")

            with btn_col3:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("저장", use_container_width=True):
                    has_error = False
                    for filtered_admin in filtered_admins:
                        # 원본 인덱스 찾기 (emp_no 기준)
                        original_idx = next(
                            (
                                i
                                for i, a in enumerate(st.session_state.admins)
                                if a.get("emp_no") == filtered_admin.get("emp_no")
                            ),
                            None,
                        )
                        if original_idx is None:
                            continue
                        
                        new_emp_no = (
                            st.session_state.get(
                                f"admin_emp_no_{original_idx}", filtered_admin["emp_no"]
                            ).strip()
                        )
                        new_name = (
                            st.session_state.get(
                                f"admin_name_{original_idx}", filtered_admin["name"]
                            ).strip()
                        )
                        new_gender = st.session_state.get(
                            f"admin_gender_{original_idx}", filtered_admin["gender"]
                        )
                        new_email = (
                            st.session_state.get(
                                f"admin_email_{original_idx}", filtered_admin.get("email", "")
                            ).strip()
                        )
                        new_phone = (
                            st.session_state.get(
                                f"admin_phone_{original_idx}", filtered_admin.get("phone", "")
                            ).strip()
                        )
                        new_position = st.session_state.get(
                            f"admin_position_{original_idx}", filtered_admin["position"]
                        )
                        new_mgmt_type = st.session_state.get(
                            f"admin_mgmt_type_{original_idx}", filtered_admin["management_type"]
                        )
                        new_status = st.session_state.get(
                            f"admin_status_{original_idx}", filtered_admin["status"]
                        )

                        if any(
                            a["emp_no"] == new_emp_no and i != original_idx
                            for i, a in enumerate(st.session_state.admins)
                        ):
                            st.error(f"'{new_emp_no}'는 이미 존재하는 사번번호입니다.")
                            has_error = True
                        else:
                            st.session_state.admins[original_idx] = {
                                "emp_no": new_emp_no,
                                "name": new_name,
                                "gender": new_gender,
                                "email": new_email,
                                "phone": new_phone,
                                "position": new_position,
                                "management_type": new_mgmt_type,
                                "status": new_status,
                            }
                    if not has_error:
                        st.session_state.admin_edit_mode = False
                        st.session_state.current_tab_index = 3
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
                    # 관리자 목록 탭 인덱스 저장 (인덱스 3)
                    st.session_state.current_tab_index = 3
                    st.rerun()

        if len(st.session_state.admins) == 0:
            st.warning("등록된 관리자가 없습니다")
            st.form_submit_button("", use_container_width=True, help="")
        elif len(filtered_admins) == 0:
            st.warning("검색 결과가 없습니다")
            st.form_submit_button("", use_container_width=True, help="")
        else:
            if (
                admin_search
                or (admin_gender_search and admin_gender_search != "전체")
                or (admin_position_search and admin_position_search != "전체")
                or (admin_mgmt_search and admin_mgmt_search != "전체")
                or (admin_status_search and admin_status_search != "전체")
            ):
                st.info(f"검색 결과: {len(filtered_admins)}개")
            
            if not st.session_state.admin_edit_mode:
                # 읽기 모드: 표 형식으로 표시
                admins_data = []
                for idx, admin in enumerate(filtered_admins, start=1):
                    admins_data.append({
                        "번호": str(idx),
                        "사번번호": admin.get("emp_no", "-"),
                        "이름": admin.get("name", "-"),
                        "성별": admin.get("gender", "-"),
                        "이메일": admin.get("email", "-"),
                        "전화번호": admin.get("phone", "-"),
                        "직급": admin.get("position", "-"),
                        "관리 종류": admin.get("management_type", "-"),
                        "재직현황": admin.get("status", "-")
                    })
                
                if admins_data:
                    df_admins = pd.DataFrame(admins_data)
                    st.dataframe(
                        df_admins,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "번호": st.column_config.TextColumn("번호", width="small"),
                            "사번번호": st.column_config.TextColumn("사번번호", width="medium"),
                            "이름": st.column_config.TextColumn("이름", width="small"),
                            "성별": st.column_config.TextColumn("성별", width="small"),
                            "이메일": st.column_config.TextColumn("이메일", width="medium"),
                            "전화번호": st.column_config.TextColumn("전화번호", width="medium"),
                            "직급": st.column_config.TextColumn("직급", width="small"),
                            "관리 종류": st.column_config.TextColumn("관리 종류", width="medium"),
                            "재직현황": st.column_config.TextColumn("재직현황", width="small")
                        }
                    )
            else:
                # 수정 모드: 기존 방식 (편집 가능한 필드)
                h1, h2, h3, h4, h5, h6, h7, h8, h9 = st.columns(
                    [1, 1.5, 0.8, 1.5, 1.5, 1.2, 1.5, 1, 0.8]
                )
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
                    # 원본 인덱스 찾기 (emp_no 기준)
                    original_idx = next(
                        (
                            i
                            for i, a in enumerate(st.session_state.admins)
                            if a.get("emp_no") == filtered_admin.get("emp_no")
                        ),
                        None,
                    )
                    if original_idx is None:
                        continue

                    admin = st.session_state.admins[original_idx]
                    c1, c2, c3, c4, c5, c6, c7, c8, c9 = st.columns(
                        [1, 1.5, 0.8, 1.5, 1.5, 1.2, 1.5, 1, 0.8]
                    )
                    with c1:
                        checked = st.checkbox("", key=f"admin_sel_{original_idx}")
                        if checked:
                            st.session_state.admin_selected.add(original_idx)
                        else:
                            st.session_state.admin_selected.discard(original_idx)
                    with c2:
                        st.text_input(
                            "사번번호",
                            value=admin["emp_no"],
                            key=f"admin_emp_no_{original_idx}",
                            disabled=not st.session_state.admin_edit_mode,
                            label_visibility="collapsed",
                        )
                    with c3:
                        st.text_input(
                            "이름",
                            value=admin["name"],
                            key=f"admin_name_{original_idx}",
                            disabled=not st.session_state.admin_edit_mode,
                            label_visibility="collapsed",
                        )
                    with c4:
                        if st.session_state.admin_edit_mode:
                            st.selectbox(
                                "성별",
                                options=["남성", "여성"],
                                index=(0 if admin["gender"] == "남성" else 1),
                                key=f"admin_gender_{original_idx}",
                                label_visibility="collapsed",
                            )
                        else:
                            st.text_input(
                                "성별",
                                value=admin["gender"],
                                key=f"admin_gender_{original_idx}",
                                disabled=True,
                                label_visibility="collapsed",
                            )
                    with c5:
                        if st.session_state.admin_edit_mode:
                            col_email, col_phone = st.columns(2)
                            with col_email:
                                st.text_input(
                                    "이메일",
                                    value=admin["email"],
                                    key=f"admin_email_{original_idx}",
                                    label_visibility="collapsed",
                                )
                            with col_phone:
                                st.text_input(
                                    "전화번호",
                                    value=admin["phone"],
                                    key=f"admin_phone_{original_idx}",
                                    label_visibility="collapsed",
                                )
                        else:
                            st.text_input(
                                "연락처",
                                value=f"{admin['email']} / {admin['phone']}",
                                key=f"admin_contact_{original_idx}",
                                disabled=True,
                                label_visibility="collapsed",
                            )
                    with c6:
                        if st.session_state.admin_edit_mode:
                            position_options = ["직원", "매니저", "파트타이머"]
                            pos_index = (
                                position_options.index(admin["position"])
                                if admin["position"] in position_options
                                else 0
                            )
                            st.selectbox(
                                "직급",
                                options=position_options,
                                index=pos_index,
                                key=f"admin_position_{original_idx}",
                                label_visibility="collapsed",
                            )
                        else:
                            st.text_input(
                                "직급",
                                value=admin["position"],
                                key=f"admin_position_{original_idx}",
                                disabled=True,
                                label_visibility="collapsed",
                            )
                    with c7:
                        if st.session_state.admin_edit_mode:
                            mgmt_options = [
                                "출/입고 관리",
                                "청소",
                                "손님 응대",
                                "음료 제조",
                                "음식 제조",
                                "기타",
                            ]
                            mgmt_index = (
                                mgmt_options.index(admin["management_type"])
                                if admin["management_type"] in mgmt_options
                                else 0
                            )
                            st.selectbox(
                                "관리 종류",
                                options=mgmt_options,
                                index=mgmt_index,
                                key=f"admin_mgmt_type_{original_idx}",
                                label_visibility="collapsed",
                            )
                        else:
                            st.text_input(
                                "관리 종류",
                                value=admin["management_type"],
                                key=f"admin_mgmt_type_{original_idx}",
                                disabled=True,
                                label_visibility="collapsed",
                            )
                    with c8:
                        if st.session_state.admin_edit_mode:
                            status_options = ["재직", "퇴사", "휴직"]
                            status_index = (
                                status_options.index(admin["status"])
                                if admin["status"] in status_options
                                else 0
                            )
                            st.selectbox(
                                "재직현황",
                                options=status_options,
                                index=status_index,
                                key=f"admin_status_{original_idx}",
                                label_visibility="collapsed",
                            )
                        else:
                            st.text_input(
                                "재직현황",
                                value=admin["status"],
                                key=f"admin_status_{original_idx}",
                                disabled=True,
                                label_visibility="collapsed",
                            )
                    with c9:
                        st.write("")
