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
        max-width: 100%;
        padding-top: 1rem;
        padding-right: 4rem;
        padding-left: 4rem;
        padding-bottom: 1rem;
    }
    div[data-testid="stHorizontalBlock"] { padding-left: 1rem; }
</style>
""", unsafe_allow_html=True)

# -------------------------------
# 세션 상태 초기화
# -------------------------------
if "products" not in st.session_state:
    st.session_state.products = []
if "categories" not in st.session_state:
    st.session_state.categories = []
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
register_tab, list_tab = st.tabs(["레시피 등록/수정", "레시피 목록 조회"])

# -------------------------------
# 레시피 등록/수정 탭
# -------------------------------
with register_tab:
    # 수정 모드 확인
    edit_mode = "recipe_menu_name_edit" in st.session_state
    if edit_mode:
        edit_menu_name = st.session_state.recipe_menu_name_edit
        edit_recipe = st.session_state.recipes.get(edit_menu_name, {})
        st.info(f"📝 수정 모드: '{edit_menu_name}' 레시피를 수정 중입니다.")
        
        # 복사 모드 확인
        copy_mode = st.session_state.get("recipe_copy_mode", False)
        if copy_mode:
            st.info("📋 복사 모드: 기존 레시피를 복사하여 새 레시피를 만듭니다.")
    
    # ② 원재료 추가 및 소모량 입력 (form 밖으로 이동)
    st.markdown("#### ② 원재료 추가 및 소모량 입력")
    st.info("💡 레시피에 들어가는 모든 원재료와 비품을 등록하고, 한 잔을 만들 때마다 소모되는 양을 정확히 입력하세요.")
    
    # 재료 입력을 위한 동적 리스트
    if "recipe_ingredients" not in st.session_state or not edit_mode:
        if edit_mode and not st.session_state.get("recipe_copy_mode", False):
            # 수정 모드: 기존 재료 로드
            st.session_state.recipe_ingredients = edit_recipe.get("ingredients", []).copy()
        else:
            st.session_state.recipe_ingredients = []
    
    # 재료 추가 버튼
    if st.button("➕ 재료 추가", key="add_ingredient_btn", use_container_width=False):
        st.session_state.recipe_ingredients.append({
            "ingredient_code": "",
            "ingredient_name": "",
            "qty": 0,
            "unit": "g"
        })
        st.rerun()
    
    # 재료 목록 표시 및 편집
    if len(st.session_state.recipe_ingredients) == 0:
        st.info("재료를 추가하세요.")
    else:
        # 재료 목록 테이블 형태로 표시
        st.markdown("**재료 목록:**")
        for idx, ingredient in enumerate(st.session_state.recipe_ingredients):
            ing_col1, ing_col2, ing_col3, ing_col4, ing_col5 = st.columns([3, 2, 1.5, 1.5, 1])
            
            with ing_col1:
                st.caption("재료 선택")
                if len(st.session_state.products) > 0:
                    product_options = [f"{p['name']} ({p['code']})" for p in st.session_state.products]
                    current_selection = f"{ingredient.get('ingredient_name', '')} ({ingredient.get('ingredient_code', '')})"
                    try:
                        default_idx = product_options.index(current_selection) if current_selection in product_options else 0
                    except:
                        default_idx = 0
                    
                    selected_option = st.selectbox(
                        "재료",
                        options=product_options,
                        key=f"recipe_ingredient_select_{idx}",
                        index=default_idx,
                        label_visibility="collapsed"
                    )
                    selected_idx = product_options.index(selected_option)
                    selected_product = st.session_state.products[selected_idx]
                    st.session_state.recipe_ingredients[idx]["ingredient_code"] = selected_product["code"]
                    st.session_state.recipe_ingredients[idx]["ingredient_name"] = selected_product["name"]
                    # 품목의 기본 단위 자동 표시
                    product_unit = selected_product.get("unit", "g")
                    if not st.session_state.recipe_ingredients[idx].get("unit"):
                        st.session_state.recipe_ingredients[idx]["unit"] = product_unit
                else:
                    st.warning("등록된 품목이 없습니다.")
            
            with ing_col2:
                st.caption("소모량")
                qty = st.number_input("소모량", min_value=0.0, step=0.1, value=float(ingredient.get("qty", 0)),
                                     key=f"recipe_ingredient_qty_{idx}", label_visibility="collapsed")
                st.session_state.recipe_ingredients[idx]["qty"] = qty
            
            with ing_col3:
                st.caption("단위")
                # 품목의 기본 단위 사용
                selected_product_unit = st.session_state.products[product_options.index(selected_option)].get("unit", "g") if len(st.session_state.products) > 0 else "g"
                unit_options = ["g", "ml", "개", "컵", "스푼"]
                current_unit = ingredient.get("unit", selected_product_unit)
                unit_index = unit_options.index(current_unit) if current_unit in unit_options else 0
                unit = st.selectbox("단위", options=unit_options, index=unit_index,
                                   key=f"recipe_ingredient_unit_{idx}", label_visibility="collapsed")
                st.session_state.recipe_ingredients[idx]["unit"] = unit
            
            with ing_col4:
                # 최근 입고 단가 표시
                ingredient_code = st.session_state.recipe_ingredients[idx].get("ingredient_code")
                if ingredient_code:
                    recent_price = get_recent_price(ingredient_code)
                    if recent_price > 0:
                        st.caption(f"최근 단가: {recent_price:,}원")
                    else:
                        st.caption("단가 정보 없음")
                else:
                    st.caption("")
            
            with ing_col5:
                st.caption("삭제")
                st.markdown("<div style='height: 37px'></div>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"recipe_ingredient_delete_{idx}", use_container_width=True):
                    st.session_state.recipe_ingredients.pop(idx)
                    st.rerun()
    
    # ④ 예상 원가 자동 계산 및 표시
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    st.markdown("#### ④ 예상 원가 자동 계산")
    
    total_cost = 0
    cost_breakdown = []
    for ing in st.session_state.recipe_ingredients:
        if ing.get("ingredient_code"):
            recent_price = get_recent_price(ing["ingredient_code"])
            qty = ing.get("qty", 0)
            # 단위 변환 (간단한 예시 - 실제로는 더 정교한 변환이 필요할 수 있음)
            unit_cost = recent_price if recent_price > 0 else 0
            ingredient_cost = unit_cost * qty / 100 if ing.get("unit") in ["g", "ml"] else unit_cost * qty
            total_cost += ingredient_cost
            cost_breakdown.append({
                "name": ing["ingredient_name"],
                "qty": qty,
                "unit": ing.get("unit", "g"),
                "price": recent_price,
                "cost": ingredient_cost
            })
    
    cost_col1, cost_col2 = st.columns([1, 1])
    with cost_col1:
        st.metric("예상 제조 원가", f"{int(total_cost):,}원")
    with cost_col2:
        # menu_price는 form 내부에서 가져와야 하므로 session_state에 저장
        menu_price = st.session_state.get("recipe_menu_price", 0)
        if menu_price > 0:
            margin = menu_price - int(total_cost)
            margin_rate = (margin / menu_price * 100) if menu_price > 0 else 0
            st.metric("예상 마진", f"{margin:,}원 ({margin_rate:.1f}%)")
    
    # 원가 상세 내역
    if cost_breakdown:
        with st.expander("원가 상세 내역", expanded=False):
            for item in cost_breakdown:
                st.write(f"- {item['name']}: {item['qty']}{item['unit']} × {item['price']:,}원 = {item['cost']:,.0f}원")
    
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    
    # ⑥ 옵션 레시피 관리
    st.markdown("#### ⑥ 옵션 레시피 관리")
    st.info("💡 기본 레시피 외에 추가되는 옵션(샷 추가, 시럽 추가, 사이즈 업 등)에 대한 추가 소모량을 관리합니다.")
    
    # 옵션 입력을 위한 동적 리스트
    if "recipe_options" not in st.session_state or not edit_mode:
        if edit_mode and not st.session_state.get("recipe_copy_mode", False):
            st.session_state.recipe_options = edit_recipe.get("options", []).copy()
        else:
            st.session_state.recipe_options = []
    
    if st.button("➕ 옵션 추가", key="add_option_btn", use_container_width=False):
        st.session_state.recipe_options.append({
            "option_name": "",
            "ingredient_code": "",
            "ingredient_name": "",
            "qty": 0,
            "unit": "g"
        })
        st.rerun()
    
    if len(st.session_state.recipe_options) == 0:
        st.info("옵션을 추가하세요 (선택사항).")
    else:
        st.markdown("**옵션 목록:**")
        for idx, option in enumerate(st.session_state.recipe_options):
            opt_col1, opt_col2, opt_col3, opt_col4, opt_col5 = st.columns([2, 2, 2, 1, 1])
            
            with opt_col1:
                st.caption("옵션명")
                option_name = st.text_input("옵션명", value=option.get("option_name", ""),
                                            key=f"recipe_option_name_{idx}", 
                                            placeholder="예: 샷 추가, 시럽 추가",
                                            label_visibility="collapsed")
                st.session_state.recipe_options[idx]["option_name"] = option_name
            
            with opt_col2:
                st.caption("재료 선택")
                if len(st.session_state.products) > 0:
                    product_options = [f"{p['name']} ({p['code']})" for p in st.session_state.products]
                    current_selection = f"{option.get('ingredient_name', '')} ({option.get('ingredient_code', '')})"
                    try:
                        default_idx = product_options.index(current_selection) if current_selection in product_options else 0
                    except:
                        default_idx = 0
                    
                    selected_option = st.selectbox(
                        "재료",
                        options=product_options,
                        key=f"recipe_option_ingredient_{idx}",
                        index=default_idx,
                        label_visibility="collapsed"
                    )
                    selected_idx = product_options.index(selected_option)
                    selected_product = st.session_state.products[selected_idx]
                    st.session_state.recipe_options[idx]["ingredient_code"] = selected_product["code"]
                    st.session_state.recipe_options[idx]["ingredient_name"] = selected_product["name"]
                else:
                    st.warning("등록된 품목이 없습니다.")
            
            with opt_col3:
                st.caption("추가 소모량")
                qty = st.number_input("추가 소모량", min_value=0.0, step=0.1, value=float(option.get("qty", 0)),
                                     key=f"recipe_option_qty_{idx}", label_visibility="collapsed")
                st.session_state.recipe_options[idx]["qty"] = qty
            
            with opt_col4:
                st.caption("단위")
                unit_options = ["g", "ml", "개", "컵", "스푼"]
                current_unit = option.get("unit", "g")
                unit_index = unit_options.index(current_unit) if current_unit in unit_options else 0
                unit = st.selectbox("단위", options=unit_options, index=unit_index,
                                   key=f"recipe_option_unit_{idx}", label_visibility="collapsed")
                st.session_state.recipe_options[idx]["unit"] = unit
            
            with opt_col5:
                st.caption("삭제")
                st.markdown("<div style='height: 37px'></div>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"recipe_option_delete_{idx}", use_container_width=True):
                    st.session_state.recipe_options.pop(idx)
                    st.rerun()
    
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    
    # 등록/수정 버튼 (form 안에)
    with st.form("recipe_register_form", clear_on_submit=False):
        st.markdown("#### ① 레시피 기본 정보 입력")
        
        # 메뉴명 입력
        if edit_mode and not st.session_state.get("recipe_copy_mode", False):
            default_menu_name = edit_menu_name
            menu_name_disabled = True
        else:
            default_menu_name = ""
            menu_name_disabled = False
        
        menu_name = st.text_input("메뉴명 (필수)", key="recipe_menu_name", 
                                 value=default_menu_name, disabled=menu_name_disabled,
                                 placeholder="예: 아이스 아메리카노, 딸기라떼 등 (POS에서 판매되는 메뉴명과 정확히 일치)")
        
        # 카테고리 선택
        category_options = ["선택하세요"] + [c["name"] for c in st.session_state.categories]
        default_category = edit_recipe.get("category", "") if edit_mode else ""
        category_index = category_options.index(default_category) if default_category in category_options else 0
        category = st.selectbox("카테고리", options=category_options, index=category_index, key="recipe_category_select")
        
        # 판매 가격 입력
        default_price = edit_recipe.get("price", 0) if edit_mode else 0
        price_str = f"{int(default_price):,}" if default_price > 0 else ""
        price_input = st.text_input("판매 가격 (원)", key="recipe_price_input", value=price_str,
                                    placeholder="예: 4500")
        
        # 가격 파싱
        if price_input:
            price_clean = ''.join(filter(str.isdigit, price_input.replace(",", "")))
            menu_price = int(price_clean) if price_clean else 0
        else:
            menu_price = 0
        
        # 가격을 session_state에 저장 (원가 계산용)
        st.session_state.recipe_menu_price = menu_price
        
        submit_col1, submit_col2 = st.columns([1, 1])
        with submit_col1:
            if edit_mode and not st.session_state.get("recipe_copy_mode", False):
                submitted = st.form_submit_button("레시피 수정", use_container_width=True, type="primary")
            else:
                submitted = st.form_submit_button("레시피 등록", use_container_width=True, type="primary")
        with submit_col2:
            if edit_mode:
                cancel_submitted = st.form_submit_button("취소", use_container_width=True)
                if cancel_submitted:
                    if "recipe_menu_name_edit" in st.session_state:
                        del st.session_state.recipe_menu_name_edit
                    if "recipe_copy_mode" in st.session_state:
                        del st.session_state.recipe_copy_mode
                    st.session_state.recipe_ingredients = []
                    st.session_state.recipe_options = []
                    st.rerun()
        
        if submitted:
            if not menu_name or not menu_name.strip():
                st.warning("메뉴명을 입력하세요.")
            elif len(st.session_state.recipe_ingredients) == 0:
                st.warning("최소 1개 이상의 재료를 추가하세요.")
            else:
                # 모든 재료가 선택되었는지 확인
                all_valid = True
                for ing in st.session_state.recipe_ingredients:
                    if not ing.get("ingredient_code") or not ing.get("ingredient_name"):
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
                        "options": []
                    }
                    
                    for ing in st.session_state.recipe_ingredients:
                        recipe_data["ingredients"].append({
                            "ingredient_code": ing["ingredient_code"],
                            "ingredient_name": ing["ingredient_name"],
                            "qty": ing["qty"],
                            "unit": ing.get("unit", "g")
                        })
                    
                    for opt in st.session_state.recipe_options:
                        if opt.get("option_name") and opt.get("ingredient_code"):
                            recipe_data["options"].append({
                                "option_name": opt["option_name"],
                                "ingredient_code": opt["ingredient_code"],
                                "ingredient_name": opt["ingredient_name"],
                                "qty": opt["qty"],
                                "unit": opt.get("unit", "g")
                            })
                    
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
                    st.session_state.recipe_ingredients = []
                    st.session_state.recipe_options = []
                    
                    action_text = "수정" if edit_mode else "등록"
                    st.success(f"✅ '{menu_name_final}' 레시피가 성공적으로 {action_text}되었습니다!")
                    st.rerun()

# -------------------------------
# 레시피 목록 조회 탭
# -------------------------------
with list_tab:
    st.markdown("#### ③ 레시피 목록 조회 및 검색")
    
    # 검색 및 필터 (Form 형태)
    with st.form("recipe_list_search_form", clear_on_submit=False):
        search_col1, search_col2 = st.columns([2, 1])
        with search_col1:
            search_query = st.text_input("검색", key="recipe_list_search",
                                        placeholder="메뉴명, 카테고리, 재료명 등 모든 항목으로 검색 가능",
                                        label_visibility="collapsed")
        with search_col2:
            category_filter = st.selectbox("카테고리 필터",
                                          options=["전체"] + [c["name"] for c in st.session_state.categories],
                                          key="recipe_category_filter", label_visibility="collapsed")
        search_submitted = st.form_submit_button("검색", use_container_width=True, type="primary")
    
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    
    # 필터링 적용
    filtered_recipes = {}
    for menu_name, recipe_data in st.session_state.recipes.items():
        match = True
        
        # 검색어 필터
        if search_query and search_query.strip():
            search_term = search_query.strip().lower()
            if (search_term not in menu_name.lower() and
                search_term not in recipe_data.get("category", "").lower()):
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
            with st.expander(f"🍽️ {menu_name}", expanded=False):
                # 기본 정보
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.markdown(f"**메뉴명:** {menu_name}")
                with col2:
                    category_name = recipe_data.get("category", "-")
                    st.markdown(f"**카테고리:** {category_name}")
                with col3:
                    price = recipe_data.get("price", 0)
                    st.markdown(f"**판매 가격:** {price:,}원")
                
                st.markdown("**재료 목록:**")
                for ing in recipe_data.get("ingredients", []):
                    st.write(f"- {ing['ingredient_name']} ({ing['ingredient_code']}): {ing['qty']}{ing.get('unit', 'g')}")
                
                # 옵션 목록
                if recipe_data.get("options"):
                    st.markdown("**옵션 목록:**")
                    for opt in recipe_data.get("options", []):
                        st.write(f"- {opt['option_name']}: {opt['ingredient_name']} ({opt['ingredient_code']}) {opt['qty']}{opt.get('unit', 'g')}")
                
                # 예상 원가 계산
                total_cost = 0
                for ing in recipe_data.get("ingredients", []):
                    if ing.get("ingredient_code"):
                        recent_price = get_recent_price(ing["ingredient_code"])
                        qty = ing.get("qty", 0)
                        unit_cost = recent_price if recent_price > 0 else 0
                        ingredient_cost = unit_cost * qty / 100 if ing.get("unit") in ["g", "ml"] else unit_cost * qty
                        total_cost += ingredient_cost
                
                if total_cost > 0:
                    st.markdown(f"**예상 제조 원가:** {int(total_cost):,}원")
                    if price > 0:
                        margin = price - int(total_cost)
                        margin_rate = (margin / price * 100) if price > 0 else 0
                        st.markdown(f"**예상 마진:** {margin:,}원 ({margin_rate:.1f}%)")
                
                # 액션 버튼
                action_col1, action_col2, action_col3 = st.columns([1, 1, 1])
                with action_col1:
                    if st.button("수정", key=f"recipe_edit_{menu_name}", use_container_width=True):
                        st.session_state.recipe_menu_name_edit = menu_name
                        st.session_state.recipe_copy_mode = False
                        st.rerun()
                with action_col2:
                    # ⑤ 레시피 복사 기능
                    if st.button("복사", key=f"recipe_copy_{menu_name}", use_container_width=True):
                        st.session_state.recipe_menu_name_edit = menu_name
                        st.session_state.recipe_copy_mode = True
                        # 복사 모드: 재료 목록 복사
                        st.session_state.recipe_ingredients = recipe_data.get("ingredients", []).copy()
                        st.session_state.recipe_options = recipe_data.get("options", []).copy()
                        st.rerun()
                with action_col3:
                    if st.button("삭제", key=f"recipe_delete_{menu_name}", use_container_width=True):
                        del st.session_state.recipes[menu_name]
                        st.success(f"'{menu_name}' 레시피가 삭제되었습니다.")
                        st.rerun()
