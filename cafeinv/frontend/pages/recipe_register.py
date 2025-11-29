import os, sys
import streamlit as st

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
    ["메뉴 카테고리 등록", "메뉴 카테고리 목록", "레시피 등록/수정", "레시피 목록 조회"]
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
                    st.session_state.menu_categories.append(
                        {"code": cat_code.strip(), "name": cat_name.strip()}
                    )
                    st.success(
                        f"'{cat_name.strip()}' 메뉴 카테고리가 성공적으로 등록되었습니다."
                    )
                    

# -------------------------------
# 메뉴 카테고리 목록 조회 탭
# -------------------------------
with category_list_tab:
    st.markdown("#### 메뉴 카테고리 목록 조회")

    # 검색 섹션 (Form 형태)
    st.markdown("### 🔍 검색")
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
    # 복사 모드 플래그
    copy_mode = st.session_state.get("recipe_copy_mode", False)

    # 수정 모드 확인
    edit_mode = "recipe_menu_name_edit" in st.session_state
    if edit_mode:
        edit_menu_name = st.session_state.recipe_menu_name_edit
        edit_recipe = st.session_state.recipes.get(edit_menu_name, {})
        st.info(f"수정 모드: '{edit_menu_name}' 레시피를 수정 중입니다.")

        # 복사 모드 안내
        if copy_mode:
            st.info("복사 모드: 기존 레시피를 복사하여 새 레시피를 만듭니다.")

    # 기본 제공 재료 (물, 얼음) - 항상 사용 가능
    default_ingredients = [
        {"code": "WATER", "name": "물", "unit": "ml"},
        {"code": "ICE", "name": "얼음", "unit": "g"},
    ]

    # 전체 재료 목록 (기본 제공 + 등록된 품목)
    all_available_products = default_ingredients + st.session_state.products

    # -------------------------------
    # 재료 리스트 초기화 (수정된 부분)
    # -------------------------------
    if "recipe_ingredients" not in st.session_state:
        st.session_state.recipe_ingredients = []

    if edit_mode and not copy_mode:
        # 다른 메뉴를 새로 선택했을 때만 기존 재료를 불러오기
        if st.session_state.get("current_edit_menu_name") != edit_menu_name:
            st.session_state.recipe_ingredients = edit_recipe.get(
                "ingredients", []
            ).copy()
            st.session_state.current_edit_menu_name = edit_menu_name

    # -------------------------------
    # 옵션 그룹 리스트 초기화 (수정된 부분)
    # -------------------------------
    if "recipe_option_groups" not in st.session_state:
        st.session_state.recipe_option_groups = []

    if edit_mode and not copy_mode:
        if st.session_state.get("current_edit_menu_name") != edit_menu_name:
            existing_options = edit_recipe.get("options", [])
            existing_groups = edit_recipe.get("option_groups", [])
            if existing_options and not existing_groups:
                # 기존 단순 옵션을 "추가 옵션" 그룹으로 변환
                st.session_state.recipe_option_groups = [
                    {
                        "group_name": "추가 옵션",
                        "required": False,
                        "options": existing_options,
                    }
                ]
            else:
                st.session_state.recipe_option_groups = (
                    existing_groups.copy() if existing_groups else []
                )
            st.session_state.current_edit_menu_name = edit_menu_name

    # 레시피 기본 정보 입력 (form 안에)
    with st.form("recipe_register_form", clear_on_submit=False):
        st.markdown("#### 레시피 기본 정보 입력")

        # 메뉴명 입력
        if edit_mode and not copy_mode:
            default_menu_name = edit_menu_name
            menu_name_disabled = True
        else:
            default_menu_name = ""
            menu_name_disabled = False

        menu_name = st.text_input(
            "메뉴명 (필수)",
            key="recipe_menu_name",
            value=default_menu_name,
            disabled=menu_name_disabled,
            placeholder="예: 아이스 아메리카노, 딸기라떼 등 (POS에서 판매되는 메뉴명과 정확히 일치)",
        )

        # 카테고리 선택 (메뉴 카테고리 사용)
        category_options = ["선택하세요"] + [
            c["name"] for c in st.session_state.menu_categories
        ]
        default_category = edit_recipe.get("category", "") if edit_mode else ""
        category_index = (
            category_options.index(default_category)
            if default_category in category_options
            else 0
        )
        category = st.selectbox(
            "메뉴 카테고리",
            options=category_options,
            index=category_index,
            key="recipe_category_select",
        )

        # 판매 가격 입력
        default_price = edit_recipe.get("price", 0) if edit_mode else 0
        price_str = f"{int(default_price):,}" if default_price > 0 else ""
        price_input = st.text_input(
            "판매 가격 (원)",
            key="recipe_price_input",
            value=price_str,
            placeholder="예: 4500",
        )

        # 가격 파싱
        if price_input:
            price_clean = "".join(
                filter(str.isdigit, price_input.replace(",", ""))
            )
            menu_price = int(price_clean) if price_clean else 0
        else:
            menu_price = 0

        # 가격을 session_state에 저장
        st.session_state.recipe_menu_price = menu_price

        # 등록/수정 버튼 (form 안에)
        submit_col1, submit_col2 = st.columns([1, 1])
        with submit_col1:
            if edit_mode and not copy_mode:
                submitted = st.form_submit_button(
                    "레시피 수정", use_container_width=True, type="primary"
                )
            else:
                submitted = st.form_submit_button(
                    "레시피 등록", use_container_width=True, type="primary"
                )
        with submit_col2:
            if edit_mode:
                cancel_submitted = st.form_submit_button(
                    "취소", use_container_width=True
                )
                if cancel_submitted:
                    if "recipe_menu_name_edit" in st.session_state:
                        del st.session_state.recipe_menu_name_edit
                    if "recipe_copy_mode" in st.session_state:
                        del st.session_state.recipe_copy_mode
                    if "current_edit_menu_name" in st.session_state:
                        del st.session_state.current_edit_menu_name
                    st.session_state.recipe_ingredients = []
                    st.session_state.recipe_option_groups = []
                    

        if submitted:
            if not menu_name or not menu_name.strip():
                st.warning("메뉴명을 입력하세요.")
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

                    # 옵션 그룹 저장
                    recipe_data["option_groups"] = []
                    for group in st.session_state.recipe_option_groups:
                        if group.get("group_name"):
                            group_data = {
                                "group_name": group["group_name"],
                                "required": group.get("required", False),
                                "options": [],
                            }
                            for opt in group.get("options", []):
                                if (
                                    opt.get("option_name")
                                    and opt.get("ingredient_code")
                                ):
                                    group_data["options"].append(
                                        {
                                            "option_name": opt["option_name"],
                                            "additional_price": opt.get(
                                                "additional_price", 0
                                            ),
                                            "ingredient_code": opt[
                                                "ingredient_code"
                                            ],
                                            "ingredient_name": opt[
                                                "ingredient_name"
                                            ],
                                            "qty": opt["qty"],
                                            "unit": opt.get("unit", "g"),
                                        }
                                    )
                            if group_data["options"]:
                                recipe_data["option_groups"].append(group_data)

                    # 하위 호환성: 기존 options 필드도 유지 (단순 옵션)
                    recipe_data["options"] = []

                    menu_name_final = menu_name.strip()
                    st.session_state.recipes[menu_name_final] = recipe_data

                    # 수정 모드인 경우 기존 레시피 삭제 (이름이 변경된 경우)
                    if edit_mode and edit_menu_name != menu_name_final:
                        if edit_menu_name in st.session_state.recipes:
                            del st.session_state.recipes[edit_menu_name]

                    # 세션 상태 정리
                    if "recipe_menu_name_edit" in st.session_state:
                        del st.session_state.recipe_menu_name_edit
                    if "recipe_copy_mode" in st.session_state:
                        del st.session_state.recipe_copy_mode
                    if "current_edit_menu_name" in st.session_state:
                        del st.session_state.current_edit_menu_name
                    st.session_state.recipe_ingredients = []
                    st.session_state.recipe_option_groups = []

                    action_text = "수정" if edit_mode and not copy_mode else "등록"
                    st.success(f"'{menu_name_final}' 레시피가 성공적으로 {action_text}되었습니다.")
                    

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # 재료 추가 기능 (form 밖)
    st.markdown("#### 재료 추가")
    st.info("음료 한 잔을 만들 때 필요한 모든 재료를 추가하세요. 예: 아메리카노 = 원두 20g + 물 200ml + 컵 1개")

    # 재료 추가 영역
    add_ingredient_col1, add_ingredient_col2, add_ingredient_col3, add_ingredient_col4 = st.columns(
        [3, 2, 1.5, 1]
    )

    with add_ingredient_col1:
        st.caption("재료 선택")
        if len(all_available_products) > 0:
            # 재료 검색
            if "new_ingredient_search" not in st.session_state:
                st.session_state.new_ingredient_search = ""

            search_term_new = st.text_input(
                "재료 검색",
                value=st.session_state.new_ingredient_search,
                key="new_ingredient_search_input",
                placeholder="재료명 또는 코드번호로 검색",
                label_visibility="collapsed",
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
                selected_option_new = st.selectbox(
                    "재료",
                    options=product_options_new,
                    key="new_ingredient_select",
                    index=0,
                    label_visibility="collapsed",
                )
                selected_idx_new = product_options_new.index(selected_option_new)
                selected_product_new = filtered_products_new[selected_idx_new]
            else:
                selected_product_new = None
                st.warning("검색 결과가 없습니다.")
        else:
            selected_product_new = None
            st.warning("등록된 품목이 없습니다.")

    with add_ingredient_col2:
        st.caption("소모량")
        if "new_ingredient_qty" not in st.session_state:
            st.session_state.new_ingredient_qty = 0.0
        qty_new = st.number_input(
            "소모량",
            min_value=0.0,
            step=0.1,
            value=st.session_state.new_ingredient_qty,
            key="new_ingredient_qty_input",
            label_visibility="collapsed",
        )
        st.session_state.new_ingredient_qty = qty_new

    with add_ingredient_col3:
        st.caption("단위")
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
            "단위",
            options=unit_options,
            index=unit_options.index(st.session_state.new_ingredient_unit)
            if st.session_state.new_ingredient_unit in unit_options
            else 0,
            key="new_ingredient_unit_select",
            label_visibility="collapsed",
        )
        st.session_state.new_ingredient_unit = unit_new
        if product_unit_new:
            st.caption(f"기본: {product_unit_new}")

    with add_ingredient_col4:
        st.caption("추가")
        st.markdown("<div style='height: 37px'></div>", unsafe_allow_html=True)
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
                
            else:
                st.warning("재료를 선택하고 소모량을 입력하세요.")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # 재료 목록 표시 및 편집
    if len(st.session_state.recipe_ingredients) == 0:
        st.info("위에서 재료를 추가하세요.")
    else:
        st.markdown("등록된 재료 목록:")
        st.markdown("---")

        # 재료 목록을 카드 형태로 표시
        for idx, ingredient in enumerate(st.session_state.recipe_ingredients):
            with st.container():
                ing_row_col1, ing_row_col2, ing_row_col3, ing_row_col4, ing_row_col5 = st.columns(
                    [3, 2, 1.5, 1, 1]
                )

                with ing_row_col1:
                    st.markdown(
                        f"**{ingredient.get('ingredient_name', '재료 미선택')}**"
                    )
                    if ingredient.get("ingredient_code"):
                        st.caption(
                            f"코드: {ingredient.get('ingredient_code', '')}"
                        )

                with ing_row_col2:
                    st.markdown(
                        f"소모량: {ingredient.get('qty', 0)}{ingredient.get('unit', 'g')}"
                    )

                with ing_row_col3:
                    # 기본 단위 표시
                    if ingredient.get("ingredient_code"):
                        if ingredient["ingredient_code"] in ["WATER", "ICE"]:
                            selected_product = next(
                                (
                                    p
                                    for p in default_ingredients
                                    if p["code"] == ingredient["ingredient_code"]
                                ),
                                None,
                            )
                        else:
                            selected_product = next(
                                (
                                    p
                                    for p in st.session_state.products
                                    if p["code"] == ingredient["ingredient_code"]
                                ),
                                None,
                            )
                        if selected_product:
                            st.caption(
                                f"기본 단위: {selected_product.get('unit', 'g')}"
                            )

                with ing_row_col4:
                    # 수정 버튼
                    if st.button(
                        "수정",
                        key=f"ingredient_edit_{idx}",
                        use_container_width=True,
                    ):
                        if (
                            "editing_ingredient_idx" not in st.session_state
                            or st.session_state.editing_ingredient_idx != idx
                        ):
                            st.session_state.editing_ingredient_idx = idx
                            

                with ing_row_col5:
                    # 삭제 버튼
                    if st.button(
                        "삭제",
                        key=f"ingredient_delete_{idx}",
                        use_container_width=True,
                    ):
                        st.session_state.recipe_ingredients.pop(idx)
                        if (
                            "editing_ingredient_idx" in st.session_state
                            and st.session_state.editing_ingredient_idx
                            >= len(st.session_state.recipe_ingredients)
                        ):
                            del st.session_state.editing_ingredient_idx
                        
                # 수정 모드
                if (
                    "editing_ingredient_idx" in st.session_state
                    and st.session_state.editing_ingredient_idx == idx
                ):
                    st.markdown("---")
                    edit_col1, edit_col2, edit_col3, edit_col4 = st.columns(
                        [3, 2, 1.5, 1]
                    )

                    with edit_col1:
                        st.caption("재료 재선택")
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
                                label_visibility="collapsed",
                            )
                            selected_idx_edit = product_options_edit.index(
                                selected_option_edit
                            )
                            selected_product_edit = all_available_products[
                                selected_idx_edit
                            ]
                            st.session_state.recipe_ingredients[idx][
                                "ingredient_code"
                            ] = selected_product_edit.get("code", "")
                            st.session_state.recipe_ingredients[idx][
                                "ingredient_name"
                            ] = selected_product_edit["name"]

                    with edit_col2:
                        st.caption("소모량 수정")
                        qty_edit = st.number_input(
                            "소모량",
                            min_value=0.0,
                            step=0.1,
                            value=float(ingredient.get("qty", 0)),
                            key=f"ingredient_edit_qty_{idx}",
                            label_visibility="collapsed",
                        )
                        st.session_state.recipe_ingredients[idx]["qty"] = qty_edit

                    with edit_col3:
                        st.caption("단위 수정")
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
                            label_visibility="collapsed",
                        )
                        st.session_state.recipe_ingredients[idx]["unit"] = unit_edit

                    with edit_col4:
                        st.caption("저장")
                        st.markdown(
                            "<div style='height: 37px'></div>", unsafe_allow_html=True
                        )
                        if st.button(
                            "저장",
                            key=f"ingredient_save_{idx}",
                            use_container_width=True,
                        ):
                            del st.session_state.editing_ingredient_idx
                            

                st.markdown("---")

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # 옵션 레시피 관리 (옵션 그룹 방식) - form 밖
    st.markdown("#### 옵션 레시피 관리")
    st.info(
        "옵션 그룹을 만들어 필수 선택 옵션이나 추가 옵션(샷 추가, 시럽 추가 등)을 관리할 수 있습니다."
    )

    # 옵션 그룹 추가 다이얼로그 플래그 초기화
    if "show_add_option_group_dialog" not in st.session_state:
        st.session_state.show_add_option_group_dialog = False
    if "temp_option_group" not in st.session_state:
        st.session_state.temp_option_group = {
            "group_name": "",
            "required": False,
            "options": [],
        }

    # 옵션 그룹 추가 버튼 (form 밖)
    if st.button(
        "옵션 그룹 추가", key="add_option_group_btn", use_container_width=False
    ):
        st.session_state.show_add_option_group_dialog = True
        st.session_state.temp_option_group = {
            "group_name": "",
            "required": False,
            "options": [],
        }
       

    # 옵션 그룹 추가 다이얼로그 (expander로 구현)
    if st.session_state.show_add_option_group_dialog:
        with st.expander("옵션 그룹 추가", expanded=True):
            st.markdown("### 옵션 그룹 정보 입력")

            group_name_dialog = st.text_input(
                "그룹명",
                value=st.session_state.temp_option_group.get("group_name", ""),
                key="option_group_name_dialog",
                placeholder="예: 원두 선택, 시럽 선택",
            )
            st.session_state.temp_option_group["group_name"] = group_name_dialog

            required_dialog = st.checkbox(
                "필수 선택",
                value=st.session_state.temp_option_group.get("required", False),
                key="option_group_required_dialog",
                help="체크 시 이 그룹에서 반드시 하나를 선택해야 합니다.",
            )
            st.session_state.temp_option_group["required"] = required_dialog

            # 다이얼로그 버튼
            dialog_col1, dialog_col2 = st.columns(2)
            with dialog_col1:
                if st.button(
                    "확인",
                    key="option_group_dialog_confirm",
                    use_container_width=True,
                    type="primary",
                ):
                    if (
                        st.session_state.temp_option_group.get(
                            "group_name", ""
                        ).strip()
                    ):
                        st.session_state.recipe_option_groups.append(
                            st.session_state.temp_option_group.copy()
                        )
                        st.session_state.show_add_option_group_dialog = False
                        
                    else:
                        st.warning("그룹명을 입력하세요.")
            with dialog_col2:
                if st.button(
                    "취소",
                    key="option_group_dialog_cancel",
                    use_container_width=True,
                ):
                    st.session_state.show_add_option_group_dialog = False
                    

    if len(st.session_state.recipe_option_groups) == 0:
        st.info(
            "옵션 그룹을 추가하세요 (선택사항). 예: '원두 선택' 그룹에 'A 원두', 'B 원두' 옵션 추가"
        )
    else:
        st.markdown("옵션 그룹 목록:")
        for group_idx, group in enumerate(st.session_state.recipe_option_groups):
            with st.expander(
                f"옵션 그룹 {group_idx + 1}: {group.get('group_name', '그룹명 미입력')}",
                expanded=True,
            ):
                # 그룹 정보 입력
                group_col1, group_col2, group_col3 = st.columns([3, 2, 1])
                with group_col1:
                    st.caption("그룹명")
                    group_name = st.text_input(
                        "그룹명",
                        value=group.get("group_name", ""),
                        key=f"recipe_option_group_name_{group_idx}",
                        placeholder="예: 원두 선택, 시럽 선택",
                        label_visibility="collapsed",
                    )
                    st.session_state.recipe_option_groups[group_idx][
                        "group_name"
                    ] = group_name

                with group_col2:
                    st.caption("필수 선택")
                    required = st.checkbox(
                        "필수 선택",
                        value=group.get("required", False),
                        key=f"recipe_option_group_required_{group_idx}",
                        help="체크 시 이 그룹에서 반드시 하나를 선택해야 합니다.",
                    )
                    st.session_state.recipe_option_groups[group_idx][
                        "required"
                    ] = required

                with group_col3:
                    st.caption("그룹 삭제")
                    st.markdown(
                        "<div style='height: 37px'></div>", unsafe_allow_html=True
                    )
                    if st.button(
                        "그룹 삭제",
                        key=f"recipe_option_group_delete_{group_idx}",
                        use_container_width=True,
                    ):
                        st.session_state.recipe_option_groups.pop(group_idx)
                        

                st.markdown("---")

                # 그룹 내 옵션 항목 관리
                if st.button(
                    "옵션 항목 추가",
                    key=f"add_option_item_{group_idx}",
                    use_container_width=False,
                ):
                    st.session_state.recipe_option_groups[group_idx][
                        "options"
                    ].append(
                        {
                            "option_name": "",
                            "additional_price": 0,
                            "ingredient_code": "",
                            "ingredient_name": "",
                            "qty": 0,
                            "unit": "g",
                        }
                    )
                    

                if len(group.get("options", [])) == 0:
                    st.info("옵션 항목을 추가하세요.")
                else:
                    st.markdown(
                        f"'{group_name or '그룹명 미입력'}' 그룹의 옵션 항목:"
                    )
                    for opt_idx, option in enumerate(group.get("options", [])):
                        (
                            opt_col1,
                            opt_col2,
                            opt_col3,
                            opt_col4,
                            opt_col5,
                            opt_col6,
                        ) = st.columns([2, 2, 1.5, 1.5, 1.5, 1])

                        with opt_col1:
                            st.caption("옵션명")
                            option_name = st.text_input(
                                "옵션명",
                                value=option.get("option_name", ""),
                                key=f"recipe_option_name_{group_idx}_{opt_idx}",
                                placeholder="예: A 원두, B 원두",
                                label_visibility="collapsed",
                            )
                            st.session_state.recipe_option_groups[group_idx][
                                "options"
                            ][opt_idx]["option_name"] = option_name

                        with opt_col2:
                            st.caption("재료 선택")
                            if len(all_available_products) > 0:
                                product_options = [
                                    f"{p['name']} ({p.get('code', '')})"
                                    for p in all_available_products
                                ]
                                current_selection = (
                                    f"{option.get('ingredient_name', '')} ({option.get('ingredient_code', '')})"
                                )
                                try:
                                    default_idx = (
                                        product_options.index(current_selection)
                                        if current_selection in product_options
                                        else 0
                                    )
                                except Exception:
                                    default_idx = 0

                                selected_option = st.selectbox(
                                    "재료",
                                    options=product_options,
                                    key=f"recipe_option_ingredient_{group_idx}_{opt_idx}",
                                    index=default_idx,
                                    label_visibility="collapsed",
                                )
                                selected_idx = product_options.index(
                                    selected_option
                                )
                                selected_product = all_available_products[
                                    selected_idx
                                ]
                                st.session_state.recipe_option_groups[group_idx][
                                    "options"
                                ][opt_idx]["ingredient_code"] = selected_product.get(
                                    "code", ""
                                )
                                st.session_state.recipe_option_groups[group_idx][
                                    "options"
                                ][opt_idx]["ingredient_name"] = selected_product[
                                    "name"
                                ]
                            else:
                                st.warning("등록된 품목이 없습니다.")

                        with opt_col3:
                            st.caption("추가 소모량")
                            qty = st.number_input(
                                "추가 소모량",
                                min_value=0.0,
                                step=0.1,
                                value=float(option.get("qty", 0)),
                                key=f"recipe_option_qty_{group_idx}_{opt_idx}",
                                label_visibility="collapsed",
                            )
                            st.session_state.recipe_option_groups[group_idx][
                                "options"
                            ][opt_idx]["qty"] = qty

                        with opt_col4:
                            st.caption("단위")
                            unit_options = ["g", "ml", "개", "컵", "스푼"]
                            current_unit = option.get("unit", "g")
                            unit_index = (
                                unit_options.index(current_unit)
                                if current_unit in unit_options
                                else 0
                            )
                            unit = st.selectbox(
                                "단위",
                                options=unit_options,
                                index=unit_index,
                                key=f"recipe_option_unit_{group_idx}_{opt_idx}",
                                label_visibility="collapsed",
                            )
                            st.session_state.recipe_option_groups[group_idx][
                                "options"
                            ][opt_idx]["unit"] = unit

                        with opt_col5:
                            st.caption("추가 금액 (원)")
                            additional_price = st.number_input(
                                "추가 금액",
                                min_value=0,
                                step=100,
                                value=int(option.get("additional_price", 0)),
                                key=f"recipe_option_price_{group_idx}_{opt_idx}",
                                label_visibility="collapsed",
                            )
                            st.session_state.recipe_option_groups[group_idx][
                                "options"
                            ][opt_idx]["additional_price"] = additional_price

                        with opt_col6:
                            st.caption("삭제")
                            st.markdown(
                                "<div style='height: 37px'></div>",
                                unsafe_allow_html=True,
                            )
                            if st.button(
                                "삭제",
                                key=f"recipe_option_item_delete_{group_idx}_{opt_idx}",
                                use_container_width=True,
                            ):
                                st.session_state.recipe_option_groups[group_idx][
                                    "options"
                                ].pop(opt_idx)
                                

# -------------------------------
# 레시피 목록 조회 탭
# -------------------------------
with list_tab:
    st.markdown("#### 레시피 목록 조회 및 검색")

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

        for menu_name, recipe_data in filtered_recipes.items():
            with st.expander(f"{menu_name}", expanded=False):
                # 기본 정보
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.markdown(f"메뉴명: {menu_name}")
                with col2:
                    category_name = recipe_data.get("category", "-")
                    st.markdown(f"카테고리: {category_name}")
                with col3:
                    price = recipe_data.get("price", 0)
                    st.markdown(f"판매 가격: {price:,}원")

                st.markdown("재료 목록:")
                for ing in recipe_data.get("ingredients", []):
                    st.write(
                        f"- {ing['ingredient_name']} ({ing['ingredient_code']}): {ing['qty']}{ing.get('unit', 'g')}"
                    )

                # 옵션 그룹 목록
                if recipe_data.get("option_groups"):
                    st.markdown("옵션 그룹 목록:")
                    for group in recipe_data.get("option_groups", []):
                        required_text = (
                            " (필수 선택)" if group.get("required") else ""
                        )
                        st.markdown(f"{group['group_name']}{required_text}:")
                        for opt in group.get("options", []):
                            price_text = (
                                f" (+{opt.get('additional_price', 0):,}원)"
                                if opt.get("additional_price", 0) > 0
                                else ""
                            )
                            st.write(
                                f"  - {opt['option_name']}{price_text}: {opt['ingredient_name']} ({opt['ingredient_code']}) {opt['qty']}{opt.get('unit', 'g')}"
                            )

                # 하위 호환성: 기존 단순 옵션 목록 표시
                if recipe_data.get("options") and not recipe_data.get(
                    "option_groups"
                ):
                    st.markdown("옵션 목록:")
                    for opt in recipe_data.get("options", []):
                        st.write(
                            f"- {opt['option_name']}: {opt['ingredient_name']} ({opt['ingredient_code']}) {opt['qty']}{opt.get('unit', 'g')}"
                        )

                # 액션 버튼
                action_col1, action_col2, action_col3 = st.columns([1, 1, 1])
                with action_col1:
                    if st.button(
                        "수정",
                        key=f"recipe_edit_{menu_name}",
                        use_container_width=True,
                    ):
                        st.session_state.recipe_menu_name_edit = menu_name
                        st.session_state.recipe_copy_mode = False
                        
                with action_col2:
                    if st.button(
                        "복사",
                        key=f"recipe_copy_{menu_name}",
                        use_container_width=True,
                    ):
                        st.session_state.recipe_menu_name_edit = menu_name
                        st.session_state.recipe_copy_mode = True
                        st.session_state.recipe_ingredients = recipe_data.get(
                            "ingredients", []
                        ).copy()
                        st.session_state.recipe_option_groups = recipe_data.get(
                            "option_groups", []
                        ).copy()
                        if "current_edit_menu_name" in st.session_state:
                            del st.session_state.current_edit_menu_name
                        
                    if st.button(
                        "삭제",
                        key=f"recipe_delete_{menu_name}",
                        use_container_width=True,
                    ):
                        del st.session_state.recipes[menu_name]
                        st.success(f"'{menu_name}' 레시피가 삭제되었습니다.")
                       