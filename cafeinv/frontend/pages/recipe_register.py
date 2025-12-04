import os, sys
import streamlit as st
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
st.set_page_config(page_title="레시피 등록", page_icon="📖", layout="wide")
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
</style>
""", unsafe_allow_html=True)

# -------------------------------
# 세션 상태 초기화
# -------------------------------
if "products" not in st.session_state:
    st.session_state.products = []
if "categories" not in st.session_state:
    st.session_state.categories = []  # 기본정보의 품목 카테고리 (품목 등록용)
if "menu_categories" not in st.session_state:
    st.session_state.menu_categories = []  # 레시피 메뉴 카테고리 (레시피 등록용, 별도 관리)
if "last_registered_menu_category" not in st.session_state:
    st.session_state.last_registered_menu_category = None  # 최근 등록한 메뉴 카테고리
if "recipes" not in st.session_state:
    st.session_state.recipes = {}  # {menu_name: {"category": "", "price": 0, "ingredients": [...], "options": [...]}}
if "received_items" not in st.session_state:
    st.session_state.received_items = []

# -------------------------------
# 유틸: 최근 입고 단가 계산
# -------------------------------
def get_recent_price(product_code):
    """최근 입고 내역에서 해당 품목의 최근 단가를 가져옴"""
    prices = []
    for item in st.session_state.received_items:
        if item.get("product_code") == product_code and item.get("actual_price", 0) > 0:
            prices.append(item.get("actual_price", 0))
    if prices:
        return prices[-1]  # 가장 최근 입고 단가
    return 0

# -------------------------------
# 헤더 & 뒤로가기 버튼
# -------------------------------
title_col, button_col = st.columns([4, 1])
with title_col:
    st.title("레시피 관리")
    st.write("메뉴별 레시피를 등록하고 관리합니다. 판매와 동시에 원재료 재고를 정확하게 차감하기 위한 핵심 기능입니다.")
with button_col:
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
    if st.button("← 뒤로가기", use_container_width=True, key="back_button"):
        st.switch_page("pages/info.py")

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# -------------------------------
# 탭 구조
# -------------------------------
category_register_tab, category_list_tab, register_tab, list_tab = st.tabs(
    ["메뉴 카테고리 등록", "메뉴 카테고리 목록", "레시피 등록", "레시피 목록 조회/수정"]
)

# -------------------------------
# 메뉴 카테고리 등록 탭
# -------------------------------
with category_register_tab:
    st.markdown("#### 메뉴 카테고리 등록")
    st.markdown(
        '<p style="color: #666; font-size: 12px; margin-top: -10px; margin-bottom: 16px;">💡 레시피 메뉴를 분류하기 위한 카테고리를 등록합니다. (예: 커피, 라떼, 에이드, 디저트 등)</p>',
        unsafe_allow_html=True,
    )
    
    # 카테고리 등록 폼
    with st.form("menu_category_register_form", clear_on_submit=True):
        st.markdown("**새 카테고리 등록**")
        cat_col1, cat_col2, cat_col3 = st.columns([2, 3, 1])
        with cat_col1:
            st.caption("코드번호")
            cat_code = st.text_input(
                "코드번호",
                key="menu_cat_code_input",
                label_visibility="collapsed",
                placeholder="예: menu_cat_001",
            )
        with cat_col2:
            st.caption("카테고리명")
            cat_name = st.text_input(
                "카테고리명",
                key="menu_cat_name_input",
                label_visibility="collapsed",
                placeholder="예: 커피, 라떼, 에이드",
            )
        with cat_col3:
            st.markdown("<div style='height: 37px'></div>", unsafe_allow_html=True)
            cat_submitted = st.form_submit_button(
                "등록", use_container_width=True, type="primary"
            )
        
        if cat_submitted:
            if not cat_code or not cat_code.strip():
                st.warning("코드번호를 입력하세요.")
            elif not cat_name or not cat_name.strip():
                st.warning("카테고리명을 입력하세요.")
            else:
                # 중복 체크 (메뉴 카테고리만 확인)
                existing_codes = [
                    c.get("code", "") for c in st.session_state.menu_categories
                ]
                existing_names = [
                    c.get("name", "") for c in st.session_state.menu_categories
                ]
                
                if cat_code.strip() in existing_codes:
                    st.error(f"이미 등록된 코드번호입니다: {cat_code.strip()}")
                elif cat_name.strip() in existing_names:
                    st.error(f"이미 등록된 카테고리명입니다: {cat_name.strip()}")
                else:
                    new_category = {"code": cat_code.strip(), "name": cat_name.strip()}
                    st.session_state.menu_categories.append(new_category)
                    st.session_state.last_registered_menu_category = new_category
                    st.success(
                        f"'{cat_name.strip()}' 메뉴 카테고리가 성공적으로 등록되었습니다."
                    )
                    
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    
    # 검색 기능 추가
    st.markdown("### 🔍 카테고리 검색")
    
    # 검색어 및 토글 상태 초기화 (위젯 생성 전에 해야 함)
    if "menu_cat_register_search_term" not in st.session_state:
        st.session_state.menu_cat_register_search_term = ""
    if "menu_cat_register_show_existing" not in st.session_state:
        st.session_state.menu_cat_register_show_existing = False
    
    # 검색창, 검색 버튼, 기존 카테고리 토글을 한 줄에 배치
    search_col1, search_col2, search_col3 = st.columns([3, 1, 1])
    
    with search_col1:
        search_input = st.text_input(
            "검색",
            key="menu_cat_register_search_input",
            placeholder="코드번호 또는 카테고리명으로 검색",
            label_visibility="collapsed",
            value=st.session_state.menu_cat_register_search_term
        )
    
    with search_col2:
        st.markdown("<div style='height: 37px'></div>", unsafe_allow_html=True)
        if st.button("검색", key="menu_cat_register_search_btn", use_container_width=True, type="primary"):
            st.session_state.menu_cat_register_search_term = search_input.strip() if search_input else ""
            st.rerun()
    
    with search_col3:
        st.markdown("<div style='height: 37px'></div>", unsafe_allow_html=True)
        # checkbox는 자동으로 session_state를 업데이트하므로 직접 할당하지 않음
        st.checkbox(
            "기존 카테고리 보기",
            key="menu_cat_register_show_existing"
        )
    
    # 검색 결과 필터링
    display_categories = st.session_state.menu_categories
    if st.session_state.menu_cat_register_search_term:
        search_term_lower = st.session_state.menu_cat_register_search_term.lower()
        display_categories = [
            c for c in st.session_state.menu_categories
            if search_term_lower in c.get("code", "").lower()
            or search_term_lower in c.get("name", "").lower()
        ]
    
    # 검색어가 있으면 검색 결과 표시
    if st.session_state.menu_cat_register_search_term:
        if len(display_categories) > 0:
            st.info(f"검색 결과: {len(display_categories)}개")
        else:
            st.warning("검색 결과가 없습니다.")
    
    # 검색 조건 초기화 버튼
    if st.session_state.menu_cat_register_search_term:
        if st.button("검색 조건 초기화", key="menu_cat_register_search_reset", use_container_width=False):
            st.session_state.menu_cat_register_search_term = ""
            st.rerun()
    
    # 최근 등록한 메뉴 카테고리 표시
    if st.session_state.last_registered_menu_category:
        st.markdown("---")
        st.markdown("#### 📋 최근 등록한 메뉴 카테고리")
        last_cat = st.session_state.last_registered_menu_category
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**코드번호:** {last_cat.get('code', '-')}")
        with col2:
            st.write(f"**카테고리명:** {last_cat.get('name', '-')}")
    
    # 기존 카테고리 목록 (토글로 표시/숨김)
    if st.session_state.menu_cat_register_show_existing:
        st.markdown("---")
        st.markdown("#### 📚 등록된 전체 카테고리")
        
        if len(display_categories) == 0:
            st.info("등록된 카테고리가 없습니다.")
        else:
            # 카테고리 데이터를 DataFrame으로 변환
            categories_data = []
            for idx, cat in enumerate(display_categories, start=1):
                categories_data.append({
                    "번호": str(idx),
                    "코드번호": cat.get('code', '-'),
                    "카테고리명": cat.get('name', '-')
                })
            
            df_categories = pd.DataFrame(categories_data)
            
            # 표 형식으로 표시
            st.dataframe(
                df_categories,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "번호": st.column_config.TextColumn("번호", width="small"),
                    "코드번호": st.column_config.TextColumn("코드번호", width="medium"),
                    "카테고리명": st.column_config.TextColumn("카테고리명", width="large")
                }
            )

# -------------------------------
# 메뉴 카테고리 목록 조회 탭
# -------------------------------
with category_list_tab:
    st.markdown("#### 메뉴 카테고리 목록 조회")
    st.markdown(
        '<p style="color: #666; font-size: 12px; margin-top: -10px; margin-bottom: 16px;">💡 등록한 메뉴 카테고리를 검색 및 확인할 수 있습니다.</p>',
        unsafe_allow_html=True,
    )
    
    # 검색 섹션 (Form 형태)
    with st.form("menu_category_search_form", clear_on_submit=False):
        st.caption("코드번호 또는 카테고리명으로 검색")
        cat_search = st.text_input(
            "검색",
            key="menu_cat_search",
                                   placeholder="코드번호 또는 카테고리명 입력",
            label_visibility="collapsed",
        )
        search_submitted = st.form_submit_button(
            "검색", use_container_width=True, type="primary"
        )
        
        # 검색어를 session_state에 저장
        if search_submitted:
            if cat_search and cat_search.strip():
                st.session_state.menu_cat_search_term = cat_search.strip()
            else:
                st.session_state.menu_cat_search_term = ""
    
    # 검색어 초기화 (세션 상태에 없으면)
    if "menu_cat_search_term" not in st.session_state:
        st.session_state.menu_cat_search_term = ""
    
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    
    # 필터링 (session_state의 검색어 사용)
    filtered_categories = st.session_state.menu_categories
    if st.session_state.menu_cat_search_term:
        search_term = st.session_state.menu_cat_search_term.lower()
        filtered_categories = [
            c
            for c in st.session_state.menu_categories
            if search_term in c.get("code", "").lower()
            or search_term in c.get("name", "").lower()
        ]
    
    # 검색 조건 초기화 버튼
    if st.session_state.menu_cat_search_term:
        if st.button(
            "검색 조건 초기화",
            key="menu_cat_search_reset",
            use_container_width=False,
        ):
            st.session_state.menu_cat_search_term = ""
            
    
    # 세션 상태 초기화 (수정 모드, 선택 상태)
    if "menu_cat_edit_mode" not in st.session_state:
        st.session_state.menu_cat_edit_mode = False
    if "menu_cat_selected" not in st.session_state:
        st.session_state.menu_cat_selected = set()
    
    # 등록된 카테고리 목록 표시
    with st.form("menu_category_list_form"):
        if st.session_state.menu_cat_edit_mode:
            title_col, btn_col1, btn_col2, btn_col3 = st.columns([5, 1, 1, 1])
            with title_col:
                st.subheader("메뉴 카테고리 목록")
            with btn_col1:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("선택 삭제", use_container_width=True):
                    if not st.session_state.menu_cat_selected:
                        st.info("삭제할 항목을 선택하세요.")
                    else:
                        # 선택된 항목 삭제 (인덱스 기준)
                        indices_to_delete = sorted(
                            st.session_state.menu_cat_selected, reverse=True
                        )
                        for idx in indices_to_delete:
                            if 0 <= idx < len(st.session_state.menu_categories):
                                cat = st.session_state.menu_categories[idx]
                                # 사용 중인 레시피 확인
                                used_in_recipes = []
                                for (
                                    menu_name,
                                    recipe_data,
                                ) in st.session_state.recipes.items():
                                    if recipe_data.get("category") == cat.get("name"):
                                        used_in_recipes.append(menu_name)
                                
                                if used_in_recipes:
                                    st.warning(
                                        f"'{cat.get('name')}' 카테고리는 다음 레시피에서 사용 중입니다:\n"
                                        + "\n".join(
                                            [f"- {menu}" for menu in used_in_recipes]
                                        )
                                        + "\n\n먼저 해당 레시피의 카테고리를 변경한 후 삭제하세요."
                                    )
                                else:
                                    st.session_state.menu_categories.pop(idx)
                        st.session_state.menu_cat_selected = set()
                        st.success("선택한 항목을 삭제했습니다.")
                        
            with btn_col2:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("전체 삭제", use_container_width=True):
                    # 사용 중인 카테고리 확인
                    used_categories = set()
                    for (
                        menu_name,
                        recipe_data,
                    ) in st.session_state.recipes.items():
                        cat_name = recipe_data.get("category")
                        if cat_name:
                            used_categories.add(cat_name)
                    
                    if used_categories:
                        st.warning(
                            "다음 카테고리는 레시피에서 사용 중입니다:\n"
                            + "\n".join([f"- {cat}" for cat in used_categories])
                            + "\n\n먼저 해당 레시피의 카테고리를 변경한 후 삭제하세요."
                        )
                    else:
                        st.session_state.menu_categories = []
                        st.session_state.menu_cat_selected = set()
                        st.success("전체 항목을 삭제했습니다.")
                        
            with btn_col3:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("저장", use_container_width=True):
                    # 모든 항목 저장 및 중복 체크
                    has_error = False
                    for idx, cat in enumerate(st.session_state.menu_categories):
                        new_code = (
                            st.session_state.get(
                                f"menu_cat_code_{idx}", cat.get("code", "")
                            )
                            .strip()
                        )
                        new_name = (
                            st.session_state.get(
                                f"menu_cat_name_{idx}", cat.get("name", "")
                            )
                            .strip()
                        )
                        
                        if not new_code or not new_name:
                            st.error("코드번호와 카테고리명을 모두 입력하세요.")
                            has_error = True
                            break
                        
                        # 중복 체크 (자기 자신 제외)
                        if any(
                            c["code"] == new_code and i != idx
                            for i, c in enumerate(st.session_state.menu_categories)
                        ):
                            st.error(f"'{new_code}'는 이미 존재하는 코드번호입니다.")
                            has_error = True
                            break
                        if any(
                            c["name"] == new_name and i != idx
                            for i, c in enumerate(st.session_state.menu_categories)
                        ):
                            st.error(f"'{new_name}'는 이미 존재하는 카테고리명입니다.")
                            has_error = True
                            break
                    
                    if not has_error:
                        # 모든 항목 업데이트
                        for idx, cat in enumerate(st.session_state.menu_categories):
                            new_code = (
                                st.session_state.get(
                                    f"menu_cat_code_{idx}", cat.get("code", "")
                                )
                                .strip()
                            )
                            new_name = (
                                st.session_state.get(
                                    f"menu_cat_name_{idx}", cat.get("name", "")
                                )
                                .strip()
                            )
                            old_name = cat.get("name")
                            
                            st.session_state.menu_categories[idx] = {
                                "code": new_code,
                                "name": new_name,
                            }
                            
                            # 레시피의 카테고리명도 업데이트
                            if old_name != new_name:
                                for (
                                    menu_name,
                                    recipe_data,
                                ) in st.session_state.recipes.items():
                                    if recipe_data.get("category") == old_name:
                                        st.session_state.recipes[menu_name][
                                            "category"
                                        ] = new_name
                        
                        st.session_state.menu_cat_edit_mode = False
                        st.success("저장되었습니다.")
                        
        else:
            title_col, btn_col = st.columns([5, 1])
            with title_col:
                st.subheader("메뉴 카테고리 목록")
            with btn_col:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("수정", use_container_width=True):
                    st.session_state.menu_cat_edit_mode = True
                    
        
        if len(st.session_state.menu_categories) == 0:
            st.warning(
                "등록된 메뉴 카테고리가 없습니다. '메뉴 카테고리 등록' 탭에서 카테고리를 등록하세요."
            )
            st.form_submit_button("", use_container_width=True, help="")
        elif len(filtered_categories) == 0:
            st.warning("검색 결과가 없습니다.")
            st.form_submit_button("", use_container_width=True, help="")
        else:
            if st.session_state.menu_cat_search_term:
                st.info(f"검색 결과: {len(filtered_categories)}개")
            
            # 수정 모드가 아닐 때는 표 형식으로 표시
            if not st.session_state.menu_cat_edit_mode:
                # 카테고리 데이터를 DataFrame으로 변환
                categories_data = []
                for idx, cat in enumerate(filtered_categories, start=1):
                    categories_data.append({
                        "번호": str(idx),
                        "코드번호": cat.get('code', '-'),
                        "카테고리명": cat.get('name', '-')
                    })
                
                df_categories = pd.DataFrame(categories_data)
                
                # 표 형식으로 표시
                st.dataframe(
                    df_categories,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "번호": st.column_config.TextColumn("번호", width="small"),
                        "코드번호": st.column_config.TextColumn("코드번호", width="medium"),
                        "카테고리명": st.column_config.TextColumn("카테고리명", width="large")
                    }
                )
            else:
                # 수정 모드일 때는 기존 방식 유지
                st.markdown(
                    """
            <div style="max-height: 400px; overflow-y: auto;">
                """,
                    unsafe_allow_html=True,
                )
            
            for filtered_cat in filtered_categories:
                # 원본 인덱스 찾기
                original_idx = next(
                    i
                    for i, c in enumerate(st.session_state.menu_categories)
                    if c == filtered_cat
                )
                row = st.session_state.menu_categories[original_idx]
                cat_col1, cat_col2, cat_col3 = st.columns([2, 3, 1])
                with cat_col1:
                    st.caption("코드번호")
                    st.text_input(
                        "코드번호",
                        value=row["code"],
                        key=f"menu_cat_code_{original_idx}",
                        disabled=not st.session_state.menu_cat_edit_mode,
                        label_visibility="collapsed",
                    )
                with cat_col2:
                    st.caption("카테고리명")
                    st.text_input(
                        "카테고리명",
                        value=row["name"],
                        key=f"menu_cat_name_{original_idx}",
                        disabled=not st.session_state.menu_cat_edit_mode,
                        label_visibility="collapsed",
                    )
                with cat_col3:
                    st.caption("\u00A0")
                    st.markdown(
                        "<div style='height: 37px'></div>", unsafe_allow_html=True
                    )
                    checked = st.checkbox("", key=f"menu_cat_sel_{original_idx}")
                    if checked:
                        st.session_state.menu_cat_selected.add(original_idx)
                    else:
                        st.session_state.menu_cat_selected.discard(original_idx)
            
            st.markdown("</div>", unsafe_allow_html=True)

# -------------------------------
# 레시피 등록/수정 탭
# -------------------------------
with register_tab:
    st.markdown("#### 레시피 등록")
    st.markdown(
        '<p style="color: #666; font-size: 12px; margin-top: -10px; margin-bottom: 16px;">💡새로운 레시피를 등록합니다. 메뉴명은 POS에서 판매되는 메뉴명과 정확히 일치해야 합니다.</p>',
        unsafe_allow_html=True,
    )
    
    # 기본 제공 재료 (물, 얼음) - 항상 사용 가능
    default_ingredients = [
        {"code": "WATER", "name": "물", "unit": "ml"},
        {"code": "ICE", "name": "얼음", "unit": "g"},
    ]
    
    # 전체 재료 목록 (기본 제공 + 등록된 품목)
    all_available_products = default_ingredients + st.session_state.products
    
    # -------------------------------
    # 재료 리스트 초기화
    # -------------------------------
    if "recipe_ingredients" not in st.session_state:
        st.session_state.recipe_ingredients = []

    # -------------------------------

    # 레시피 기본 정보 입력
    st.markdown("#### 레시피 기본 정보 입력")
    
    # 기본 정보 초기화 (새로 등록하는 경우만)
    if "recipe_menu_name_temp" not in st.session_state:
        st.session_state.recipe_menu_name_temp = ""
    if "recipe_category_temp" not in st.session_state:
        st.session_state.recipe_category_temp = ""
    if "recipe_price_temp" not in st.session_state:
        st.session_state.recipe_price_temp = 0
    
    # 입력 필드들 (카테고리 먼저 배치)
    # 카테고리 선택
    category_options = ["선택하세요"] + [
        c["name"] for c in st.session_state.menu_categories
    ]
    current_category = st.session_state.recipe_category_temp if "recipe_category_temp" in st.session_state else ""
    category_index = (
        category_options.index(current_category)
        if current_category in category_options
        else 0
    )
    category = st.selectbox(
        "메뉴 카테고리",
        options=category_options,
        index=category_index,
        key="recipe_category_select",
    )
    # 카테고리를 session_state에 실시간 저장
    st.session_state.recipe_category_temp = category if category != "선택하세요" else ""
    
    # 메뉴명과 판매 가격
    info_col1, info_col2 = st.columns([2, 1])
    
    with info_col1:
        # 메뉴명 입력
        menu_name_value = st.session_state.recipe_menu_name_temp if "recipe_menu_name_temp" in st.session_state else ""
        
        menu_name = st.text_input(
            "메뉴명 (필수)",
            key="recipe_menu_name",
            value=menu_name_value,
            placeholder="예: 아이스 아메리카노, 딸기라떼 등 (POS에서 판매되는 메뉴명과 정확히 일치)",
        )
        # 메뉴명을 session_state에 실시간 저장
        st.session_state.recipe_menu_name_temp = menu_name

    with info_col2:
        # 판매 가격 입력
        price_value = st.session_state.recipe_price_temp if "recipe_price_temp" in st.session_state else 0
        price_str = f"{int(price_value):,}" if price_value > 0 else ""
        price_input = st.text_input(
            "판매 가격 (원)",
            key="recipe_price_input",
            value=price_str,
            placeholder="예: 4500",
        )
        # 가격 파싱 및 저장
        if price_input:
            price_clean = "".join(
                filter(str.isdigit, price_input.replace(",", ""))
            )
            menu_price = int(price_clean) if price_clean else 0
        else:
            menu_price = 0
        st.session_state.recipe_price_temp = menu_price
        st.session_state.recipe_menu_price = menu_price
    
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    
    # 재료 추가 기능 (form 밖)
    st.markdown("#### 재료 추가")
    st.info("음료 한 잔을 만들 때 필요한 모든 재료를 추가하세요. 예: 아메리카노 = 원두 20g + 물 200ml + 컵 1개")
    
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    
    # 재료 검색 (별도 줄)
    if "new_ingredient_search" not in st.session_state:
        st.session_state.new_ingredient_search = ""
    
    if len(all_available_products) > 0:
        search_term_new = st.text_input(
            "🔍 재료 검색",
            value=st.session_state.new_ingredient_search,
            key="new_ingredient_search_input",
            placeholder="재료명 또는 코드번호로 검색",
            help="재료를 빠르게 찾기 위한 검색 기능입니다."
        )
        st.session_state.new_ingredient_search = search_term_new
        
        # 검색어로 필터링
        if search_term_new:
            search_term_lower = search_term_new.lower()
            filtered_products_new = [
                p
                for p in all_available_products
                if search_term_lower in p["name"].lower()
                or search_term_lower in p.get("code", "").lower()
            ]
        else:
            filtered_products_new = all_available_products
        
        if len(filtered_products_new) > 0:
            product_options_new = [
                f"{p['name']} ({p.get('code', '')})"
                for p in filtered_products_new
            ]
        else:
            product_options_new = []
            st.warning("검색 결과가 없습니다.")
    else:
        selected_product_new = None
        filtered_products_new = []
        product_options_new = []
        st.warning("등록된 품목이 없습니다.")
    
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    
    # 재료 선택, 소모량, 단위, 추가 버튼을 한 줄에 배치
    if len(product_options_new) > 0 or len(all_available_products) > 0:
        # 모든 요소를 한 줄에 배치 (레이블 포함)
        add_ingredient_col1, add_ingredient_col2, add_ingredient_col3, add_ingredient_col4 = st.columns(
            [2.5, 1.8, 1.2, 1]
        )

        with add_ingredient_col1:
            st.markdown("**재료 선택**")
            if len(product_options_new) > 0:
                selected_option_new = st.selectbox(
                    "재료를 선택하세요",
                    options=product_options_new,
                    key="new_ingredient_select",
                    index=0,
                    label_visibility="collapsed",
                )
                selected_idx_new = product_options_new.index(selected_option_new)
                selected_product_new = filtered_products_new[selected_idx_new]
            else:
                selected_product_new = None
    
        with add_ingredient_col2:
            st.markdown("**소모량**")
            if "new_ingredient_qty" not in st.session_state:
                st.session_state.new_ingredient_qty = 0.0
            qty_new = st.number_input(
                "소모량을 입력하세요",
                min_value=0.0,
                step=0.1,
                value=st.session_state.new_ingredient_qty,
                key="new_ingredient_qty_input",
                label_visibility="collapsed",
            )
            st.session_state.new_ingredient_qty = qty_new
    
        with add_ingredient_col3:
            st.markdown("**단위**")
            if selected_product_new:
                product_unit_new = selected_product_new.get("unit", "g")
            else:
                product_unit_new = "g"
            
            unit_options = ["g", "ml", "개", "컵", "스푼"]
            if "new_ingredient_unit" not in st.session_state:
                st.session_state.new_ingredient_unit = (
                    product_unit_new if product_unit_new in unit_options else "g"
                )
            
            unit_new = st.selectbox(
                "단위를 선택하세요",
                options=unit_options,
                index=unit_options.index(st.session_state.new_ingredient_unit)
                if st.session_state.new_ingredient_unit in unit_options
                else 0,
                key="new_ingredient_unit_select",
                label_visibility="collapsed",
            )
            st.session_state.new_ingredient_unit = unit_new
            if selected_product_new and product_unit_new:
                st.caption(f"기본 단위: {product_unit_new}")
    
        with add_ingredient_col4:
            st.markdown("**추가**")
            if st.button(
                "➕ 추가",
                key="add_ingredient_btn",
                use_container_width=True,
                type="primary",
            ):
                if selected_product_new and qty_new > 0:
                    new_ingredient = {
                        "ingredient_code": selected_product_new.get("code", ""),
                        "ingredient_name": selected_product_new["name"],
                        "qty": qty_new,
                        "unit": unit_new,
                    }
                    st.session_state.recipe_ingredients.append(new_ingredient)
                    # 검색어 및 입력값 초기화
                    st.session_state.new_ingredient_search = ""
                    st.session_state.new_ingredient_qty = 0.0
                    st.session_state.new_ingredient_unit = (
                        product_unit_new if product_unit_new in unit_options else "g"
                    )
                    st.rerun()
                else:
                    st.warning("재료를 선택하고 소모량을 입력하세요.")
    
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    
    # 재료 목록 표시 및 편집
    if len(st.session_state.recipe_ingredients) == 0:
        st.info("위에서 재료를 추가하세요.")
    else:
        st.markdown("#### 등록된 재료 목록")
        
        # 재료 목록을 카드 형태로 표시 (간결하게)
        for idx, ingredient in enumerate(st.session_state.recipe_ingredients):
            # 수정 모드인지 확인
            is_editing = (
                "editing_ingredient_idx" in st.session_state
                and st.session_state.editing_ingredient_idx == idx
            )
            
            if is_editing:
                # 수정 모드: 노란색 배경 카드
                st.markdown(f"""
                <div style="background-color: #fff3cd; border: 2px solid #ffc107; border-radius: 8px; padding: 16px; margin-bottom: 12px;">
                    <div style="margin-bottom: 12px;">
                        <strong style="font-size: 15px; color: #856404;">✏️ 재료 수정 중</strong>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 수정 입력 필드들 (간결하게)
                edit_col1, edit_col2 = st.columns([2, 1])
                
                with edit_col1:
                    # 재료 선택
                    if len(all_available_products) > 0:
                        current_sel = (
                            f"{ingredient.get('ingredient_name', '')} ({ingredient.get('ingredient_code', '')})"
                        )
                        product_options_edit = [
                            f"{p['name']} ({p.get('code', '')})"
                            for p in all_available_products
                        ]
                        try:
                            default_idx_edit = (
                                product_options_edit.index(current_sel)
                                if current_sel in product_options_edit
                                else 0
                            )
                        except Exception:
                            default_idx_edit = 0
                        
                        selected_option_edit = st.selectbox(
                            "재료",
                            options=product_options_edit,
                            key=f"ingredient_edit_select_{idx}",
                            index=default_idx_edit,
                        )
                        selected_idx_edit = product_options_edit.index(selected_option_edit)
                        selected_product_edit = all_available_products[selected_idx_edit]
                        st.session_state.recipe_ingredients[idx]["ingredient_code"] = selected_product_edit.get("code", "")
                        st.session_state.recipe_ingredients[idx]["ingredient_name"] = selected_product_edit["name"]
                
                with edit_col2:
                    # 소모량
                    qty_edit = st.number_input(
                        "소모량",
                        min_value=0.0,
                        step=0.1,
                        value=float(ingredient.get("qty", 0)),
                        key=f"ingredient_edit_qty_{idx}",
                    )
                    st.session_state.recipe_ingredients[idx]["qty"] = qty_edit
                
                # 단위
                unit_options = ["g", "ml", "개", "컵", "스푼"]
                current_unit_edit = ingredient.get("unit", "g")
                unit_index_edit = (
                    unit_options.index(current_unit_edit)
                    if current_unit_edit in unit_options
                    else 0
                )
                unit_edit = st.selectbox(
                    "단위",
                    options=unit_options,
                    index=unit_index_edit,
                    key=f"ingredient_edit_unit_{idx}",
                )
                st.session_state.recipe_ingredients[idx]["unit"] = unit_edit
                
                # 저장/취소 버튼
                btn_col1, btn_col2 = st.columns([1, 1])
                with btn_col1:
                    if st.button("✅ 저장", key=f"ingredient_save_{idx}", use_container_width=True, type="primary"):
                        del st.session_state.editing_ingredient_idx
                        st.rerun()
                with btn_col2:
                    if st.button("❌ 취소", key=f"ingredient_cancel_{idx}", use_container_width=True):
                        del st.session_state.editing_ingredient_idx
                        st.rerun()
                
            else:
                # 일반 모드: 재료 정보와 버튼을 한 줄에
                info_col1, info_col2, info_col3 = st.columns([3, 1, 1])
                
                with info_col1:
                    st.markdown(f"""
                    <div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 12px; margin-bottom: 8px;">
                        <strong style="font-size: 15px;">{ingredient.get('ingredient_name', '재료 미선택')}</strong>
                        <span style="color: #6c757d; font-size: 13px; margin-left: 12px;">
                            코드: <code style="background-color: #e9ecef; padding: 2px 6px; border-radius: 3px;">{ingredient.get('ingredient_code', '-')}</code>
                            | 소모량: <strong style="color: #0d6efd;">{ingredient.get('qty', 0)}{ingredient.get('unit', 'g')}</strong>
                        </span>
                    </div>
                    """, unsafe_allow_html=True)
                
                with info_col2:
                    if st.button("✏️ 수정", key=f"ingredient_edit_{idx}", use_container_width=True, type="secondary"):
                        st.session_state.editing_ingredient_idx = idx
                        st.rerun()
                
                with info_col3:
                    if st.button("🗑️ 삭제", key=f"ingredient_delete_{idx}", use_container_width=True, type="secondary"):
                        st.session_state.recipe_ingredients.pop(idx)
                        if (
                            "editing_ingredient_idx" in st.session_state
                            and st.session_state.editing_ingredient_idx >= len(st.session_state.recipe_ingredients)
                        ):
                            del st.session_state.editing_ingredient_idx
                        st.rerun()
                            
                st.markdown("---")

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    
    # 레시피 등록 버튼
    if st.button("레시피 등록", use_container_width=True, type="primary"):
        # 기본 정보 가져오기
        menu_name = st.session_state.get("recipe_menu_name_temp", "")
        category = st.session_state.get("recipe_category_temp", "")
        menu_price = st.session_state.get("recipe_price_temp", 0)
        
        if not menu_name or not menu_name.strip():
            st.warning("메뉴명을 입력하세요.")
        elif menu_name.strip() in st.session_state.recipes:
            st.warning(f"'{menu_name.strip()}' 메뉴명은 이미 등록되어 있습니다.")
        elif len(st.session_state.recipe_ingredients) == 0:
            st.warning("최소 1개 이상의 재료를 추가하세요.")
        else:
            # 모든 재료가 선택되었는지 확인
            all_valid = True
            for ing in st.session_state.recipe_ingredients:
                if (
                    not ing.get("ingredient_code")
                    or not ing.get("ingredient_name")
                ):
                    all_valid = False
                    break

            if not all_valid:
                st.warning("모든 재료를 선택하세요.")
            else:
                # 레시피 저장
                recipe_data = {
                    "category": category if category != "선택하세요" else "",
                    "price": menu_price,
                    "ingredients": [],
                    "options": [],
                }

                for ing in st.session_state.recipe_ingredients:
                    recipe_data["ingredients"].append(
                        {
                            "ingredient_code": ing["ingredient_code"],
                            "ingredient_name": ing["ingredient_name"],
                            "qty": ing["qty"],
                            "unit": ing.get("unit", "g"),
                        }
                    )

                # 옵션 관련 필드 (하위 호환성을 위해 빈 배열로 설정)
                recipe_data["option_groups"] = []
                recipe_data["options"] = []

                menu_name_final = menu_name.strip()
                st.session_state.recipes[menu_name_final] = recipe_data

                # 세션 상태 정리
                st.session_state.recipe_ingredients = []
                if "recipe_menu_name_temp" in st.session_state:
                    del st.session_state.recipe_menu_name_temp
                if "recipe_category_temp" in st.session_state:
                    del st.session_state.recipe_category_temp
                if "recipe_price_temp" in st.session_state:
                    del st.session_state.recipe_price_temp

                st.success(f"'{menu_name_final}' 레시피가 성공적으로 등록되었습니다.")
                st.rerun()

# -------------------------------
# 레시피 목록 조회 탭
# -------------------------------
with list_tab:
    st.markdown("#### 레시피 목록 조회 및 검색")
    st.markdown(
        '<p style="color: #666; font-size: 12px; margin-top: -10px; margin-bottom: 16px;">💡 둥록한 레시피 메뉴를 확인 및 수정할 수 있습니다.</p>',
        unsafe_allow_html=True,
    )
    # 검색 및 필터 (Form 형태)
    with st.form("recipe_list_search_form", clear_on_submit=False):
        search_col1, search_col2 = st.columns([2, 1])
        with search_col1:
            search_query = st.text_input(
                "검색",
                key="recipe_list_search",
                                        placeholder="메뉴명, 카테고리, 재료명 등 모든 항목으로 검색 가능",
                label_visibility="collapsed",
            )
        with search_col2:
            category_filter = st.selectbox(
                "카테고리 필터",
                options=["전체"]
                + [c["name"] for c in st.session_state.menu_categories],
                key="recipe_category_filter",
                label_visibility="collapsed",
            )
        search_submitted = st.form_submit_button(
            "검색", use_container_width=True, type="primary"
        )
    
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    
    # 필터링 적용
    filtered_recipes = {}
    for menu_name, recipe_data in st.session_state.recipes.items():
        match = True
        
        # 검색어 필터
        if search_query and search_query.strip():
            search_term = search_query.strip().lower()
            if (
                search_term not in menu_name.lower()
                and search_term not in recipe_data.get("category", "").lower()
            ):
                # 재료명 검색
                found_in_ingredient = False
                for ing in recipe_data.get("ingredients", []):
                    if search_term in ing.get("ingredient_name", "").lower():
                        found_in_ingredient = True
                        break
                if not found_in_ingredient:
                    match = False
        
        # 카테고리 필터
        if category_filter and category_filter != "전체":
            if recipe_data.get("category") != category_filter:
                match = False
        
        if match:
            filtered_recipes[menu_name] = recipe_data
    
    # 레시피 목록 표시
    if len(st.session_state.recipes) == 0:
        st.info("등록된 레시피가 없습니다.")
    elif len(filtered_recipes) == 0:
        st.warning("검색 결과가 없습니다.")
    else:
        if search_query or category_filter != "전체":
            st.info(f"검색 결과: {len(filtered_recipes)}개")
        
        # 레시피 데이터를 DataFrame으로 변환
        recipes_data = []
        for idx, (menu_name, recipe_data) in enumerate(filtered_recipes.items(), start=1):
            recipes_data.append({
                "번호": str(idx),
                "메뉴명": menu_name,
                "카테고리": recipe_data.get("category", "-"),
                "판매가격": f"{recipe_data.get('price', 0):,}원",
                "재료수": len(recipe_data.get("ingredients", []))
            })
        
        df_recipes = pd.DataFrame(recipes_data)
        
        # 표 형식으로 표시
        st.dataframe(
            df_recipes,
            use_container_width=True,
            hide_index=True,
            column_config={
                "번호": st.column_config.TextColumn("번호", width="small"),
                "메뉴명": st.column_config.TextColumn("메뉴명", width="large"),
                "카테고리": st.column_config.TextColumn("카테고리", width="medium"),
                "판매가격": st.column_config.TextColumn("판매가격", width="medium"),
                "재료수": st.column_config.TextColumn("재료수", width="small")
            }
        )
        
        # 각 레시피별 상세보기 및 관리 (expander 사용)
        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
        st.markdown("**레시피 상세보기 및 관리:**")
        
        for menu_name, recipe_data in filtered_recipes.items():
            # 수정 모드 확인
            edit_key = f"recipe_edit_mode_{menu_name}"
            is_editing = st.session_state.get(edit_key, False)
            
            # expander 열림 상태 확인 (수정 모드이거나 명시적으로 열어야 하는 경우)
            expander_open_key = f"expander_open_{menu_name}"
            should_expand = is_editing or st.session_state.get(expander_open_key, False)
            if should_expand and expander_open_key in st.session_state:
                del st.session_state[expander_open_key]  # 한 번만 사용
            
            with st.expander(f"📋 {menu_name} 상세보기", expanded=should_expand):
                if is_editing:
                    # 수정 모드
                    st.markdown("#### ✏️ 레시피 수정")
                    
                    # 임시 데이터 저장용 키
                    temp_menu_name_key = f"edit_menu_name_{menu_name}"
                    temp_category_key = f"edit_category_{menu_name}"
                    temp_price_key = f"edit_price_{menu_name}"
                    temp_ingredients_key = f"edit_ingredients_{menu_name}"
                    
                    # 초기값 설정 (처음 수정 모드 진입 시)
                    if temp_menu_name_key not in st.session_state:
                        st.session_state[temp_menu_name_key] = menu_name
                        st.session_state[temp_category_key] = recipe_data.get('category', '')
                        st.session_state[temp_price_key] = recipe_data.get('price', 0)
                        st.session_state[temp_ingredients_key] = recipe_data.get('ingredients', []).copy()
                    
                    # 카테고리 선택
                    category_options = ["선택하세요"] + [
                        c["name"] for c in st.session_state.menu_categories
                    ]
                    current_category = st.session_state[temp_category_key]
                    category_index = (
                        category_options.index(current_category)
                        if current_category in category_options
                        else 0
                    )
                    new_category = st.selectbox(
                        "메뉴 카테고리",
                        options=category_options,
                        index=category_index,
                        key=f"edit_category_select_{menu_name}",
                    )
                    st.session_state[temp_category_key] = new_category if new_category != "선택하세요" else ""
                    
                    # 메뉴명과 판매 가격
                    edit_info_col1, edit_info_col2 = st.columns([2, 1])
                    with edit_info_col1:
                        new_menu_name = st.text_input(
                            "메뉴명 (필수)",
                            value=st.session_state[temp_menu_name_key],
                            key=f"edit_menu_name_input_{menu_name}",
                            placeholder="예: 아이스 아메리카노",
                        )
                        st.session_state[temp_menu_name_key] = new_menu_name
                    
                    with edit_info_col2:
                        price_value = st.session_state[temp_price_key]
                        price_str = f"{int(price_value):,}" if price_value > 0 else ""
                        new_price_input = st.text_input(
                            "판매 가격 (원)",
                            value=price_str,
                            key=f"edit_price_input_{menu_name}",
                            placeholder="예: 4500",
                        )
                        # 가격 파싱 및 저장
                        if new_price_input:
                            price_clean = "".join(filter(str.isdigit, new_price_input.replace(",", "")))
                            new_price = int(price_clean) if price_clean else 0
                        else:
                            new_price = 0
                        st.session_state[temp_price_key] = new_price
                    
                    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
                    
                    # 재료 목록 수정
                    st.markdown("**재료 목록 수정:**")
                    
                    # 기본 제공 재료
                    default_ingredients = [
                        {"code": "WATER", "name": "물", "unit": "ml"},
                        {"code": "ICE", "name": "얼음", "unit": "g"},
                    ]
                    all_available_products = default_ingredients + st.session_state.products
                    
                    # 재료 목록 표시 및 편집
                    # session_state에서 최신 재료 목록 가져오기
                    ingredients_list = st.session_state[temp_ingredients_key].copy()
                    
                    if len(ingredients_list) > 0:
                        for idx, ing in enumerate(ingredients_list):
                            ing_col1, ing_col2, ing_col3, ing_col4 = st.columns([3, 2, 1, 1])
                            
                            with ing_col1:
                                # 재료 선택
                                product_options = [
                                    f"{p['name']} ({p.get('code', '')})"
                                    for p in all_available_products
                                ]
                                current_sel = f"{ing.get('ingredient_name', '')} ({ing.get('ingredient_code', '')})"
                                try:
                                    default_idx = product_options.index(current_sel) if current_sel in product_options else 0
                                except:
                                    default_idx = 0
                                
                                selected_option = st.selectbox(
                                    "재료",
                                    options=product_options,
                                    index=default_idx,
                                    key=f"edit_ing_select_{menu_name}_{idx}",
                                    label_visibility="collapsed",
                                )
                                selected_idx = product_options.index(selected_option)
                                selected_product = all_available_products[selected_idx]
                                # 재료 변경 시 session_state에서 최신 목록 가져와서 업데이트
                                current_ingredients = st.session_state.get(temp_ingredients_key, []).copy()
                                if idx < len(current_ingredients):
                                    current_ingredients[idx]["ingredient_code"] = selected_product.get("code", "")
                                    current_ingredients[idx]["ingredient_name"] = selected_product["name"]
                                    st.session_state[temp_ingredients_key] = current_ingredients
                            
                            with ing_col2:
                                current_ingredients = st.session_state.get(temp_ingredients_key, []).copy()
                                current_qty = float(current_ingredients[idx].get("qty", 0)) if idx < len(current_ingredients) else 0.0
                                ing_qty = st.number_input(
                                    "소모량",
                                    min_value=0.0,
                                    step=0.1,
                                    value=current_qty,
                                    key=f"edit_ing_qty_{menu_name}_{idx}",
                                    label_visibility="collapsed",
                                )
                                # 소모량 변경 시 session_state 업데이트
                                if idx < len(current_ingredients) and current_ingredients[idx].get("qty", 0) != ing_qty:
                                    current_ingredients[idx]["qty"] = ing_qty
                                    st.session_state[temp_ingredients_key] = current_ingredients
                            
                            with ing_col3:
                                current_ingredients = st.session_state.get(temp_ingredients_key, []).copy()
                                unit_options = ["g", "ml", "개", "컵", "스푼"]
                                current_unit = current_ingredients[idx].get("unit", "g") if idx < len(current_ingredients) else "g"
                                unit_idx = unit_options.index(current_unit) if current_unit in unit_options else 0
                                ing_unit = st.selectbox(
                                    "단위",
                                    options=unit_options,
                                    index=unit_idx,
                                    key=f"edit_ing_unit_{menu_name}_{idx}",
                                    label_visibility="collapsed",
                                )
                                # 단위 변경 시 session_state 업데이트
                                if idx < len(current_ingredients) and current_ingredients[idx].get("unit", "g") != ing_unit:
                                    current_ingredients[idx]["unit"] = ing_unit
                                    st.session_state[temp_ingredients_key] = current_ingredients
                            
                            with ing_col4:
                                if st.button("🗑️", key=f"edit_ing_delete_{menu_name}_{idx}", use_container_width=True):
                                    current_ingredients = st.session_state.get(temp_ingredients_key, []).copy()
                                    current_ingredients.pop(idx)
                                    st.session_state[temp_ingredients_key] = current_ingredients
                                    st.rerun()
                    
                    # 재료 추가
                    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                    add_ing_col1, add_ing_col2, add_ing_col3, add_ing_col4 = st.columns([3, 2, 1, 1])
                    
                    with add_ing_col1:
                        product_options_new = [
                            f"{p['name']} ({p.get('code', '')})"
                            for p in all_available_products
                        ]
                        new_ingredient_select = st.selectbox(
                            "재료 선택",
                            options=product_options_new,
                            index=0,
                            key=f"edit_new_ing_select_{menu_name}",
                            label_visibility="collapsed",
                        )
                        selected_idx_new = product_options_new.index(new_ingredient_select)
                        selected_product_new = all_available_products[selected_idx_new]
                    
                    with add_ing_col2:
                        new_ingredient_qty = st.number_input(
                            "소모량",
                            min_value=0.0,
                            step=0.1,
                            value=0.0,
                            key=f"edit_new_ing_qty_{menu_name}",
                            label_visibility="collapsed",
                        )
                    
                    with add_ing_col3:
                        unit_options = ["g", "ml", "개", "컵", "스푼"]
                        new_ingredient_unit = st.selectbox(
                            "단위",
                            options=unit_options,
                            index=0,
                            key=f"edit_new_ing_unit_{menu_name}",
                            label_visibility="collapsed",
                        )
                    
                    with add_ing_col4:
                        if st.button("➕ 추가", key=f"edit_add_ing_{menu_name}", use_container_width=True):
                            if new_ingredient_qty > 0:
                                new_ing = {
                                    "ingredient_code": selected_product_new.get("code", ""),
                                    "ingredient_name": selected_product_new["name"],
                                    "qty": new_ingredient_qty,
                                    "unit": new_ingredient_unit,
                                }
                                # session_state에서 최신 목록 가져와서 추가
                                current_ingredients = st.session_state.get(temp_ingredients_key, []).copy()
                                current_ingredients.append(new_ing)
                                st.session_state[temp_ingredients_key] = current_ingredients
                                st.rerun()
                    
                    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
                    st.markdown("---")
                    
                    # 저장/취소 버튼
                    save_col1, save_col2 = st.columns([1, 1])
                    with save_col1:
                        if st.button("✅ 저장", key=f"edit_save_{menu_name}", use_container_width=True, type="primary"):
                            # 저장 시 최신 값 가져오기
                            new_menu_name_final = st.session_state.get(temp_menu_name_key, menu_name).strip()
                            final_category = st.session_state.get(temp_category_key, "")
                            final_price = st.session_state.get(temp_price_key, 0)
                            
                            # 재료 목록을 위젯에서 최신 값으로 다시 구성
                            base_ingredients = st.session_state.get(temp_ingredients_key, [])
                            final_ingredients = []
                            # 기본 제공 재료 정의
                            default_ingredients_for_save = [
                                {"code": "WATER", "name": "물", "unit": "ml"},
                                {"code": "ICE", "name": "얼음", "unit": "g"},
                            ]
                            all_available_products_for_save = default_ingredients_for_save + st.session_state.products
                            
                            for idx in range(len(base_ingredients)):
                                # 각 재료의 위젯에서 최신 값 읽기
                                ing_select_key = f"edit_ing_select_{menu_name}_{idx}"
                                ing_qty_key = f"edit_ing_qty_{menu_name}_{idx}"
                                ing_unit_key = f"edit_ing_unit_{menu_name}_{idx}"
                                
                                if ing_select_key in st.session_state:
                                    selected_option = st.session_state[ing_select_key]
                                    product_options = [
                                        f"{p['name']} ({p.get('code', '')})"
                                        for p in all_available_products_for_save
                                    ]
                                    if selected_option in product_options:
                                        selected_idx = product_options.index(selected_option)
                                        selected_product = all_available_products_for_save[selected_idx]
                                        
                                        qty = st.session_state.get(ing_qty_key, 0)
                                        unit = st.session_state.get(ing_unit_key, "g")
                                        
                                        final_ingredients.append({
                                            "ingredient_code": selected_product.get("code", ""),
                                            "ingredient_name": selected_product["name"],
                                            "qty": qty,
                                            "unit": unit,
                                        })
                            
                            # 유효성 검사
                            if not new_menu_name_final:
                                st.warning("메뉴명을 입력하세요.")
                            elif new_menu_name_final != menu_name and new_menu_name_final in st.session_state.recipes:
                                st.warning(f"'{new_menu_name_final}' 메뉴명은 이미 등록되어 있습니다.")
                            elif len(final_ingredients) == 0:
                                st.warning("최소 1개 이상의 재료를 추가하세요.")
                            else:
                                # 레시피 업데이트
                                new_recipe_data = {
                                    "category": final_category if final_category != "선택하세요" else "",
                                    "price": final_price,
                                    "ingredients": final_ingredients,
                                    "options": [],
                                    "option_groups": [],
                                }
                                
                                # 메뉴명이 변경된 경우
                                if new_menu_name_final != menu_name:
                                    # 새 이름으로 저장
                                    st.session_state.recipes[new_menu_name_final] = new_recipe_data
                                    # 기존 레시피 삭제
                                    del st.session_state.recipes[menu_name]
                                else:
                                    # 같은 이름으로 업데이트
                                    st.session_state.recipes[menu_name] = new_recipe_data
                                
                                # 수정 모드 종료 및 임시 데이터 정리
                                del st.session_state[edit_key]
                                del st.session_state[temp_menu_name_key]
                                del st.session_state[temp_category_key]
                                del st.session_state[temp_price_key]
                                del st.session_state[temp_ingredients_key]
                                
                                st.success(f"'{new_menu_name_final}' 레시피가 성공적으로 수정되었습니다.")
                                st.rerun()
                    
                    with save_col2:
                        if st.button("❌ 취소", key=f"edit_cancel_{menu_name}", use_container_width=True):
                            # 수정 모드 종료 및 임시 데이터 정리
                            del st.session_state[edit_key]
                            if temp_menu_name_key in st.session_state:
                                del st.session_state[temp_menu_name_key]
                            if temp_category_key in st.session_state:
                                del st.session_state[temp_category_key]
                            if temp_price_key in st.session_state:
                                del st.session_state[temp_price_key]
                            if temp_ingredients_key in st.session_state:
                                del st.session_state[temp_ingredients_key]
                            st.rerun()
                
                else:
                    # 읽기 모드
                    # 기본 정보
                    info_col1, info_col2, info_col3 = st.columns(3)
                    with info_col1:
                        st.markdown(f"**메뉴명:** {menu_name}")
                    with info_col2:
                        st.markdown(f"**카테고리:** {recipe_data.get('category', '-')}")
                    with info_col3:
                        st.markdown(f"**판매 가격:** {recipe_data.get('price', 0):,}원")
                    
                    st.markdown("**재료 목록:**")
                    ingredients_list = recipe_data.get("ingredients", [])
                    if ingredients_list:
                        # 재료 목록을 표 형식으로 표시
                        ingredients_data = []
                        for ing_idx, ing in enumerate(ingredients_list, start=1):
                            ingredients_data.append({
                                "번호": str(ing_idx),
                                "재료명": ing.get('ingredient_name', '-'),
                                "코드": ing.get('ingredient_code', '-'),
                                "소모량": f"{ing.get('qty', 0)}{ing.get('unit', 'g')}"
                            })
                        
                        df_ingredients = pd.DataFrame(ingredients_data)
                        st.dataframe(
                            df_ingredients,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "번호": st.column_config.TextColumn("번호", width="small"),
                                "재료명": st.column_config.TextColumn("재료명", width="large"),
                                "코드": st.column_config.TextColumn("코드", width="medium"),
                                "소모량": st.column_config.TextColumn("소모량", width="medium")
                            }
                        )
                    else:
                        st.info("등록된 재료가 없습니다.")
                    
                    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
                    st.markdown("---")
                    st.markdown("**레시피 관리:**")
                    
                    # 수정/삭제 버튼
                    action_col1, action_col2 = st.columns([1, 1])
                    with action_col1:
                        if st.button("✏️ 수정", key=f"recipe_edit_{menu_name}", use_container_width=True, type="primary"):
                            st.session_state[edit_key] = True
                            # expander를 자동으로 열기 위해 상태 저장
                            st.session_state[f"expander_open_{menu_name}"] = True
                            st.rerun()
                    with action_col2:
                        if st.button("🗑️ 삭제", key=f"recipe_delete_{menu_name}", use_container_width=True, type="secondary"):
                            del st.session_state.recipes[menu_name]
                            st.success(f"'{menu_name}' 레시피가 삭제되었습니다.")
                            st.rerun()
