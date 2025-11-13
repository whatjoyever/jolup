import os, sys
import streamlit as st
from datetime import datetime, date
from client import api_get, api_post

# --- sidebar import 경로 보정 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))  # ../frontend
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

from sidebar import render_sidebar
from client import api_get, api_post   # ✅ 올바른 import
# --------------------------------

# ===============================
# 페이지 설정 & 커스텀 사이드바
# ===============================
st.set_page_config(page_title="출고관리", page_icon="📤", layout="wide")
render_sidebar("release")

# ===============================
# 글로벌 스타일 (여백 조정)
# ===============================
st.markdown("""
<style>
  .main .block-container { max-width: 100%; padding-top: 1rem; padding-right: 4rem; padding-left: 4rem; padding-bottom: 1rem; }
  div[data-testid="stHorizontalBlock"] { padding-left: 1rem; }
</style>
""", unsafe_allow_html=True)

# ===============================
# 세션 상태 초기화
# ===============================
# products: info.py의 품목 등록을 공유
if "products" not in st.session_state:
    st.session_state.products = []

# received_items: receive.py에서 입고 완료된 항목을 공유
if "received_items" not in st.session_state:
    st.session_state.received_items = []  # [{product_code, product_name, actual_qty, ...}]

# releases: 이 페이지에서 관리하는 출고 내역
if "releases" not in st.session_state:
    st.session_state.releases = []        # [{product_code, product_name, qty, price, date, note, release_type, staff, reason}]
if "release_selected" not in st.session_state:
    st.session_state.release_selected = set()
if "release_edit_mode" not in st.session_state:
    st.session_state.release_edit_mode = False

# recipes: 레시피 데이터 (메뉴명 -> 재료 목록)
if "recipes" not in st.session_state:
    st.session_state.recipes = {}  # {menu_name: [{"ingredient_code": "A001", "ingredient_name": "A 원두", "qty": 20, "unit": "g"}, ...]}

# staff_list: 담당자 목록 (기본정보의 관리자 목록에서 가져오기)
if "admins" not in st.session_state:
    st.session_state.admins = []

# ===============================
# 유틸: 현재 재고 계산 (세션 기반)
# ===============================
def calc_stock_map():
    """
    세션의 received_items/ releases를 이용해 품목별 재고를 dict로 반환.
    { product_code: {"name": name, "stock": int} }
    """
    stock = {}
    # 입고 합산
    for r in st.session_state.received_items:
        code = r["product_code"]
        name = r["product_name"]
        qty  = int(r.get("actual_qty", 0))
        if code not in stock:
            stock[code] = {"name": name, "stock": 0}
        stock[code]["stock"] += qty
    # 출고 차감
    for o in st.session_state.releases:
        code = o["product_code"]
        qty  = int(o.get("qty", 0))
        if code not in stock:
            # 입고가 없었는데 출고가 먼저 있었다면(비정상) 음수로 내려갈 수 있음
            stock[code] = {"name": o.get("product_name", code), "stock": 0}
        stock[code]["stock"] -= qty
    return stock

# ===============================
# 헤더
# ===============================
title_col, right_col = st.columns([4, 2])
with title_col:
    st.title("출고관리")
    st.caption("상품 출고 내역을 등록하고 조회합니다. (세션 재고 검증)")
with right_col:
    st.write(""); st.write("")
    if st.button("HOME", use_container_width=True):
        st.switch_page("pages/main.py")

# ===============================
# 탭
# ===============================
register_tab, history_tab = st.tabs(["출고 등록", "출고 내역"])

# ------------------------------------------------------------------
# 출고 등록
# ------------------------------------------------------------------
with register_tab:
    
    # ① 출고 유형 선택 (가장 중요!)
    st.markdown("#### 출고 유형 선택 (필수)")
    release_type = st.radio(
        "출고 유형",
        options=["재료 소모", "폐기 처분", "기타 출고"],
        key="release_type_select",
        horizontal=True,
        help="출고 유형을 선택하면 재고 감소 원인을 명확히 구분할 수 있습니다."
    )
    
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # 직접 출고 (재료 소모, 폐기 처분, 기타 출고)
    st.markdown(f"#### 직접 출고 ({release_type})")
    st.markdown(f'<p style="color: #666; font-size: 12px; margin-top: -10px; margin-bottom: 16px;">💡 {release_type}에 해당하는 재료를 직접 선택하고 오늘 사용한 총 사용량을 입력하세요.</p>', unsafe_allow_html=True)
    
    # 출고일 및 출고 유형 선택 (상단)
    release_info_col1, release_info_col2 = st.columns([1, 1])
    with release_info_col1:
        st.caption("출고일 (기본값: 오늘)")
        release_date = st.date_input("출고일", key="release_date_input", value=date.today(), label_visibility="collapsed")
    
    with release_info_col2:
        st.caption("출고 유형")
        st.info(f"**선택된 유형:** {release_type}")
    
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    
    # 재료 목록 초기화
    if "release_ingredients" not in st.session_state:
        st.session_state.release_ingredients = []
    
    # 기본 제공 재료 (물, 얼음) - 항상 사용 가능
    default_ingredients = [
        {"code": "WATER", "name": "물", "unit": "ml"},
        {"code": "ICE", "name": "얼음", "unit": "g"}
    ]
    
    # 전체 재료 목록 (기본 제공 + 등록된 품목)
    all_available_products = default_ingredients + st.session_state.products
    
    # 재료 추가 영역
    st.markdown("#### 재료 추가")
    add_release_col1, add_release_col2, add_release_col3, add_release_col4 = st.columns([3, 2, 1.5, 1])
    
    with add_release_col1:
        st.caption("재료 선택")
        if len(all_available_products) > 0:
            # 재료 검색 (Form 형태)
            with st.form("release_ingredient_search_form", clear_on_submit=False):
                search_term_new = st.text_input(
                    "재료 검색",
                    key="new_release_search_input",
                    placeholder="재료명 또는 코드번호로 검색",
                    label_visibility="collapsed"
                )
                search_submitted = st.form_submit_button("검색", use_container_width=True, type="primary")
                
                # 검색어를 session_state에 저장
                if search_submitted:
                    if search_term_new and search_term_new.strip():
                        st.session_state.new_release_search = search_term_new.strip()
                    else:
                        st.session_state.new_release_search = ""
            
            # 검색어 초기화 (세션 상태에 없으면)
            if "new_release_search" not in st.session_state:
                st.session_state.new_release_search = ""
            
            # 검색어로 필터링
            if st.session_state.new_release_search:
                search_term_lower = st.session_state.new_release_search.lower()
                filtered_products_new = [
                    p for p in all_available_products
                    if search_term_lower in p.get('name', '').lower() or search_term_lower in p.get('code', '').lower()
                ]
            else:
                filtered_products_new = all_available_products
            
            if len(filtered_products_new) > 0:
                product_options_new = [f"{p.get('name', '')} ({p.get('code', '')})" for p in filtered_products_new]
                selected_option_new = st.selectbox(
                    "재료",
                    options=product_options_new,
                    key="new_release_select",
                    index=0,
                    label_visibility="collapsed"
                )
                selected_idx_new = product_options_new.index(selected_option_new)
                selected_product_new = filtered_products_new[selected_idx_new]
            else:
                selected_product_new = None
                st.warning("검색 결과가 없습니다.")
        else:
            selected_product_new = None
            st.warning("등록된 품목이 없습니다.")
    
    with add_release_col2:
        st.caption("사용량 (오늘 총 사용량)")
        if "new_release_qty" not in st.session_state:
            st.session_state.new_release_qty = 0.0
        qty_new = st.number_input(
            "사용량",
            min_value=0.0,
            step=0.1,
            value=st.session_state.new_release_qty,
            key="new_release_qty_input",
            label_visibility="collapsed"
        )
        st.session_state.new_release_qty = qty_new
    
    with add_release_col3:
        st.caption("단위")
        if selected_product_new:
            product_unit_new = selected_product_new.get("unit", "g")
        else:
            product_unit_new = "g"
        
        unit_options = ["g", "ml", "개", "봉투", "박스", "병", "컵", "스푼"]
        if "new_release_unit" not in st.session_state:
            st.session_state.new_release_unit = product_unit_new if product_unit_new in unit_options else "g"
        
        unit_new = st.selectbox(
            "단위",
            options=unit_options,
            index=unit_options.index(st.session_state.new_release_unit) if st.session_state.new_release_unit in unit_options else 0,
            key="new_release_unit_select",
            label_visibility="collapsed"
        )
        st.session_state.new_release_unit = unit_new
        if product_unit_new:
            st.caption(f"기본: {product_unit_new}")
    
    with add_release_col4:
        st.caption("추가")
        st.markdown("<div style='height: 37px'></div>", unsafe_allow_html=True)
        if st.button("➕ 추가", key="add_release_btn", use_container_width=True, type="primary"):
            if selected_product_new and qty_new > 0:
                new_release_item = {
                    "ingredient_code": selected_product_new.get("code", ""),
                    "ingredient_name": selected_product_new.get("name", ""),
                    "qty": qty_new,
                    "unit": unit_new,
                    "base_unit": product_unit_new  # 기본 단위 저장
                }
                st.session_state.release_ingredients.append(new_release_item)
                # 검색어 초기화
                st.session_state.new_release_search = ""
                st.session_state.new_release_qty = 0.0
                st.session_state.new_release_unit = product_unit_new if product_unit_new in unit_options else "g"
                st.rerun()
            else:
                st.warning("재료를 선택하고 사용량을 입력하세요.")
    
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    
    # 재료 목록 표시 및 편집
    if len(st.session_state.release_ingredients) == 0:
        st.markdown('<p style="color: #666; font-size: 12px;">위에서 재료를 추가하세요.</p>', unsafe_allow_html=True)
    else:
        st.markdown("**출고할 재료 목록:**")
        st.markdown("---")
        
        # 재고 확인
        stock_map = calc_stock_map()
        
        # 재료 목록을 카드 형태로 표시
        for idx, ingredient in enumerate(st.session_state.release_ingredients):
            with st.container():
                ing_row_col1, ing_row_col2, ing_row_col3, ing_row_col4, ing_row_col5 = st.columns([3, 2, 1.5, 1, 1])
                
                with ing_row_col1:
                    st.markdown(f"**{ingredient.get('ingredient_name', '재료 미선택')}**")
                    if ingredient.get('ingredient_code'):
                        st.caption(f"코드: {ingredient.get('ingredient_code', '')}")
                
                with ing_row_col2:
                    qty_display = ingredient.get('qty', 0)
                    unit_display = ingredient.get('unit', 'g')
                    base_unit = ingredient.get('base_unit', 'g')
                    st.markdown(f"**사용량:** {qty_display}{unit_display}")
                    if unit_display != base_unit:
                        st.caption(f"기본 단위 환산 필요: {base_unit}")
                
                with ing_row_col3:
                    # 재고 확인
                    ingredient_code = ingredient.get('ingredient_code', '')
                    current_stock = stock_map.get(ingredient_code, {"stock": 0})["stock"]
                    if current_stock >= qty_display:
                        st.success(f"재고: {current_stock}")
                    else:
                        st.error(f"재고 부족: {current_stock}")
                
                with ing_row_col4:
                    # 수정 버튼
                    if st.button("✏️ 수정", key=f"release_edit_{idx}", use_container_width=True):
                        if "editing_release_idx" not in st.session_state or st.session_state.editing_release_idx != idx:
                            st.session_state.editing_release_idx = idx
                            st.rerun()
                
                with ing_row_col5:
                    # 삭제 버튼
                    if st.button("🗑️ 삭제", key=f"release_delete_{idx}", use_container_width=True):
                        st.session_state.release_ingredients.pop(idx)
                        if "editing_release_idx" in st.session_state and st.session_state.editing_release_idx >= len(st.session_state.release_ingredients):
                            del st.session_state.editing_release_idx
                        st.rerun()
                
                # 수정 모드
                if "editing_release_idx" in st.session_state and st.session_state.editing_release_idx == idx:
                    st.markdown("---")
                    edit_col1, edit_col2, edit_col3, edit_col4 = st.columns([3, 2, 1.5, 1])
                    
                    with edit_col1:
                        st.caption("재료 재선택")
                        if len(all_available_products) > 0:
                            current_sel = f"{ingredient.get('ingredient_name', '')} ({ingredient.get('ingredient_code', '')})"
                            product_options_edit = [f"{p.get('name', '')} ({p.get('code', '')})" for p in all_available_products]
                            try:
                                default_idx_edit = product_options_edit.index(current_sel) if current_sel in product_options_edit else 0
                            except:
                                default_idx_edit = 0
                            
                            selected_option_edit = st.selectbox(
                                "재료",
                                options=product_options_edit,
                                key=f"release_edit_select_{idx}",
                                index=default_idx_edit,
                                label_visibility="collapsed"
                            )
                            selected_idx_edit = product_options_edit.index(selected_option_edit)
                            selected_product_edit = all_available_products[selected_idx_edit]
                            st.session_state.release_ingredients[idx]["ingredient_code"] = selected_product_edit.get("code", "")
                            st.session_state.release_ingredients[idx]["ingredient_name"] = selected_product_edit.get("name", "")
                            st.session_state.release_ingredients[idx]["base_unit"] = selected_product_edit.get("unit", "g")
                    
                    with edit_col2:
                        st.caption("사용량 수정")
                        qty_edit = st.number_input(
                            "사용량",
                            min_value=0.0,
                            step=0.1,
                            value=float(ingredient.get("qty", 0)),
                            key=f"release_edit_qty_{idx}",
                            label_visibility="collapsed"
                        )
                        st.session_state.release_ingredients[idx]["qty"] = qty_edit
                    
                    with edit_col3:
                        st.caption("단위 수정")
                        unit_options = ["g", "ml", "개", "봉투", "박스", "병", "컵", "스푼"]
                        current_unit_edit = ingredient.get("unit", "g")
                        unit_index_edit = unit_options.index(current_unit_edit) if current_unit_edit in unit_options else 0
                        unit_edit = st.selectbox(
                            "단위",
                            options=unit_options,
                            index=unit_index_edit,
                            key=f"release_edit_unit_{idx}",
                            label_visibility="collapsed"
                        )
                        st.session_state.release_ingredients[idx]["unit"] = unit_edit
                    
                    with edit_col4:
                        st.caption("저장")
                        st.markdown("<div style='height: 37px'></div>", unsafe_allow_html=True)
                        if st.button("💾 저장", key=f"release_save_{idx}", use_container_width=True):
                            del st.session_state.editing_release_idx
                            st.rerun()
                
                st.markdown("---")
    
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    
    # 출고 완료 버튼
    with st.form("release_complete_form", clear_on_submit=True):
        st.markdown("#### 출고 정보")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.caption("담당자")
            # 기본정보에서 등록한 관리자 중 재직 중인 관리자만 표시
            active_admins = [admin["name"] for admin in st.session_state.get("admins", []) if admin.get("status") == "재직"]
            if not active_admins:
                active_admins = ["관리자 미등록"]
            staff_name = st.selectbox("담당자", options=active_admins, key="release_staff_select", label_visibility="collapsed")
            
            st.caption("출고 사유 및 메모")
            out_reason = st.text_area("출고 사유 및 메모", key="release_reason_input",
                                     placeholder="예: 오늘 개봉해서 사용한 원재료, 유통기한 경과로 폐기 등",
                                     height=100, label_visibility="collapsed")
        
        with col2:
            st.markdown("<div style='height: 100px'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button("출고 완료", use_container_width=True, type="primary")
        
        if submitted:
            if len(st.session_state.release_ingredients) == 0:
                st.warning("출고할 재료를 추가하세요.")
            else:
                # 재고 확인
                stock_map = calc_stock_map()
                all_sufficient = True
                insufficient_items = []
                
                for ingredient in st.session_state.release_ingredients:
                    ingredient_code = ingredient.get('ingredient_code', '')
                    qty = ingredient.get('qty', 0)
                    unit = ingredient.get('unit', 'g')
                    base_unit = ingredient.get('base_unit', 'g')
                    
                    # 단위 환산 (간단한 예시 - 실제로는 더 정교한 변환이 필요할 수 있음)
                    # 여기서는 단위가 같으면 그대로, 다르면 기본 단위로 환산 필요
                    # 실제 구현에서는 단위 변환 로직이 필요합니다
                    converted_qty = qty  # 일단 그대로 사용 (실제로는 단위 변환 필요)
                    
                    current_stock = stock_map.get(ingredient_code, {"stock": 0})["stock"]
                    
                    if converted_qty > current_stock:
                        all_sufficient = False
                        insufficient_items.append({
                            "name": ingredient.get('ingredient_name', ''),
                            "required": converted_qty,
                            "available": current_stock
                        })
                
                if not all_sufficient:
                    error_msg = "재고 부족:\n"
                    for item in insufficient_items:
                        error_msg += f"- {item['name']}: 필요 {item['required']}, 재고 {item['available']}\n"
                    st.error(error_msg)
                else:
                    # 모든 재료 출고 등록
                    for ingredient in st.session_state.release_ingredients:
                        ingredient_code = ingredient.get('ingredient_code', '')
                        ingredient_name = ingredient.get('ingredient_name', '')
                        qty = int(ingredient.get('qty', 0))
                        
                        st.session_state.releases.append({
                            "product_code": ingredient_code,
                            "product_name": ingredient_name,
                            "qty": qty,
                            "price": 0,
                            "date": str(release_date),
                            "note": out_reason or f"{release_type}",
                            "release_type": release_type,
                            "staff": staff_name,
                            "reason": out_reason or f"{release_type}"
                        })
                    
                    st.success(f"총 {len(st.session_state.release_ingredients)}개 재료가 출고되었습니다.")
                    st.session_state.release_ingredients = []
                    st.session_state.new_release_search = ""
                    st.session_state.new_release_qty = 0.0
                    st.session_state.new_release_unit = "g"
                    if "editing_release_idx" in st.session_state:
                        del st.session_state.editing_release_idx
                    st.rerun()

# ------------------------------------------------------------------
# 출고 내역
# ------------------------------------------------------------------
with history_tab:
    
    # ⑥ 출고 내역 조회 및 검색
    st.markdown("#### 출고 내역 조회 및 검색")
    
    # 검색 섹션 (Form 형태)
    st.markdown("### 🔍 검색")
    with st.form("release_history_search_form", clear_on_submit=False):
        st.caption("품목명, 출고일, 비고, 담당자, 출고 유형 등 모든 항목으로 검색 가능")
        search_query = st.text_input("검색", key="release_history_search",
                                    placeholder="품목명, 출고일, 비고, 담당자 등 모든 항목으로 검색 가능",
                                    label_visibility="collapsed")
        search_submitted = st.form_submit_button("검색", use_container_width=True, type="primary")
        
        # 검색어를 session_state에 저장
        if search_submitted:
            if search_query and search_query.strip():
                st.session_state.release_search_term = search_query.strip()
            else:
                st.session_state.release_search_term = ""
    
    # 검색어 초기화 (세션 상태에 없으면)
    if "release_search_term" not in st.session_state:
        st.session_state.release_search_term = ""
    
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    
    # 필터 섹션 (기간, 출고 유형, 담당자)
    st.markdown("### 필터")
    filter_col1, filter_col2, filter_col3 = st.columns([1, 1, 1])
    with filter_col1:
        st.caption("기간 시작")
        start_date_q = st.date_input("시작일", key="release_start_date", value=date.today().replace(day=1), label_visibility="collapsed")
    with filter_col2:
        st.caption("기간 종료")
        end_date_q = st.date_input("종료일", key="release_end_date", value=date.today(), label_visibility="collapsed")
    with filter_col3:
        st.caption("출고 유형")
        release_type_filter = st.selectbox("출고 유형", 
                                          options=["전체", "재료 소모", "폐기 처분", "기타 출고"],
                                          key="release_type_filter", label_visibility="collapsed")
    
    filter_col4, filter_col5 = st.columns([1, 1])
    with filter_col4:
        st.caption("담당자")
        # 기본정보에서 등록한 관리자 중 재직 중인 관리자만 표시
        active_admins_for_filter = [admin["name"] for admin in st.session_state.get("admins", []) if admin.get("status") == "재직"]
        staff_filter_options = ["전체"] + active_admins_for_filter if active_admins_for_filter else ["전체", "관리자 미등록"]
        staff_filter = st.selectbox("담당자 필터", 
                                   options=staff_filter_options,
                                   key="release_staff_filter", label_visibility="collapsed")
    with filter_col5:
        # 검색 조건 초기화 버튼
        if st.session_state.release_search_term or release_type_filter != "전체" or staff_filter != "전체":
            st.markdown("<div style='height: 37px'></div>", unsafe_allow_html=True)
            if st.button("필터 초기화", key="release_filter_reset", use_container_width=True):
                st.session_state.release_search_term = ""
                st.session_state.release_start_date = date.today().replace(day=1)
                st.session_state.release_end_date = date.today()
                st.session_state.release_type_filter = "전체"
                st.session_state.release_staff_filter = "전체"
                st.rerun()
    
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    
    # 필터링 적용
    filtered = list(st.session_state.releases)
    
    # 통합 검색 (session_state의 검색어 사용)
    if st.session_state.release_search_term:
        search_term = st.session_state.release_search_term.lower()
        filtered = [x for x in filtered 
                   if search_term in x.get("product_name", "").lower()
                   or search_term in x.get("product_code", "").lower()
                   or search_term in x.get("date", "")
                   or search_term in x.get("note", "").lower()
                   or search_term in x.get("reason", "").lower()
                   or search_term in x.get("staff", "").lower()
                   or search_term in x.get("release_type", "").lower()]
    
    # 기간 필터
    if start_date_q and end_date_q:
        temp_filtered = []
        for x in filtered:
            try:
                release_date = datetime.strptime(x.get("date", ""), "%Y-%m-%d").date()
                if start_date_q <= release_date <= end_date_q:
                    temp_filtered.append(x)
            except:
                pass
        filtered = temp_filtered
    
    # 출고 유형 필터
    if release_type_filter and release_type_filter != "전체":
        filtered = [x for x in filtered if x.get("release_type") == release_type_filter]
    
    # 담당자 필터
    if staff_filter and staff_filter != "전체":
        filtered = [x for x in filtered if x.get("staff") == staff_filter]

    # 테이블 (편집/삭제)
    with st.form("release_list_form"):
        if st.session_state.release_edit_mode:
            tcol, b1, b2 = st.columns([5,1,1])
            with tcol: st.subheader("출고 내역")
            with b1:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("선택 삭제", use_container_width=True):
                    if not st.session_state.release_selected:
                        st.info("삭제할 항목을 선택하세요.")
                    else:
                        # 삭제 전 재고 검증: 삭제하면 재고가 증가(되돌림)이므로 별도 검증 불필요
                        for i in sorted(st.session_state.release_selected, reverse=True):
                            if 0 <= i < len(st.session_state.releases):
                                st.session_state.releases.pop(i)
                        st.session_state.release_selected = set()
                        st.session_state.release_edit_mode = False
                        st.success("선택한 출고 내역을 삭제했습니다."); st.rerun()
            with b2:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("전체 삭제", use_container_width=True):
                    st.session_state.releases = []
                    st.session_state.release_selected = set()
                    st.session_state.release_edit_mode = False
                    st.success("전체 출고 내역을 삭제했습니다."); st.rerun()
        else:
            tcol, b = st.columns([5,1])
            with tcol: st.subheader("출고 내역")
            with b:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("수정", use_container_width=True):
                    st.session_state.release_edit_mode = True; st.rerun()

        if len(st.session_state.releases) == 0:
            st.warning("등록된 출고 내역이 없습니다"); st.form_submit_button("", use_container_width=True, help="")
        elif len(filtered) == 0:
            st.warning("검색 결과가 없습니다"); st.form_submit_button("", use_container_width=True, help="")
        else:
            if st.session_state.release_search_term or release_type_filter != "전체" or staff_filter != "전체" or (start_date_q and end_date_q):
                st.info(f"검색 결과: {len(filtered)}건")
            
            h1, h2, h3, h4, h5, h6, h7, h8, h9 = st.columns([0.8, 1.2, 1.8, 1, 0.8, 1, 1.2, 1.2, 1.5])
            with h1: st.write("**선택**")
            with h2: st.write("**출고일**")
            with h3: st.write("**품목명**")
            with h4: st.write("**출고수량**")
            with h5: st.write("**출고유형**")
            with h6: st.write("**담당자**")
            with h7: st.write("**출고사유**")
            with h8: st.write("**비고**")
            with h9: st.write("**상태**")

            for _, row in enumerate(filtered):
                idx = next(i for i, r in enumerate(st.session_state.releases) if r == row)
                c1, c2, c3, c4, c5, c6, c7, c8, c9 = st.columns([0.8, 1.2, 1.8, 1, 0.8, 1, 1.2, 1.2, 1.5])
                with c1:
                    is_checked = idx in st.session_state.release_selected
                    checked = st.checkbox("", value=is_checked, key=f"release_sel_{idx}")
                    if checked: st.session_state.release_selected.add(idx)
                    else:       st.session_state.release_selected.discard(idx)
                with c2: 
                    st.write(row.get("date", "-"))
                with c3: 
                    st.write(f"{row.get('product_name', '-')} ({row.get('product_code', '-')})")
                with c4: 
                    st.write(f"{row.get('qty', 0):,}")
                with c5: 
                    release_type_display = row.get("release_type", "-")
                    st.write(release_type_display)
                with c6: 
                    st.write(row.get("staff", "-"))
                with c7: 
                    reason = row.get("reason", "-")
                    if reason and reason != "-":
                        st.write(reason[:20] + "..." if len(reason) > 20 else reason)
                    else:
                        st.write("-")
                with c8: 
                    note = row.get("note", "")
                    if note and note.strip():
                        st.write(note[:20] + "..." if len(note) > 20 else note)
                    else:
                        st.write("-")
                with c9:
                    st.success("✅ 등록")