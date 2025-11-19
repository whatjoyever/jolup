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
  .main .block-container {
    max-width: 900px;
    padding-top: 1rem;
    padding-right: 1.5rem;
    padding-left: 1.5rem;
    padding-bottom: 1rem;
  }
  div[data-testid="stHorizontalBlock"] { padding-left: 0.5rem; }
  
  /* 카테고리 섹션 스타일 */
  .category-section {
    background-color: #f8f9fa;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 1.5rem;
    border: 1px solid #e9ecef;
  }
  
  .category-title {
    color: #0B3B75;
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 0.75rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid #0B3B75;
  }
  
  /* 테이블 행 스타일 */
  .product-row {
    padding: 0.75rem 0;
    border-bottom: 1px solid #e9ecef;
  }
  
  .product-row:last-child {
    border-bottom: none;
  }
  
  /* 선택된 품목 요약 섹션 */
  .summary-section {
    background-color: #e3f2fd;
    border-radius: 8px;
    padding: 1.25rem;
    margin: 1.5rem 0;
    border: 2px solid #2196F3;
  }
  
  /* 헤더 스타일 */
  .table-header {
    background-color: #f8f9fa;
    font-weight: 600;
    padding: 0.5rem 0;
    border-bottom: 2px solid #dee2e6;
  }
  
  /* 상태 배지 스타일 */
  .status-badge {
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.875rem;
    font-weight: 500;
  }
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

    # 카테고리별 출고 방식
    st.markdown(f"#### 카테고리별 출고 ({release_type})")
    st.markdown(f'<p style="color: #666; font-size: 13px; margin-top: -10px; margin-bottom: 20px;">💡 카테고리별로 품목을 확인하고 체크한 후 출고 수량을 입력하세요.</p>', unsafe_allow_html=True)
    
    # 출고일 및 출고 유형 선택 (상단)
    release_info_col1, release_info_col2 = st.columns([1, 1])
    with release_info_col1:
        st.caption("📅 출고일 (기본값: 오늘)")
        release_date = st.date_input("출고일", key="release_date_input", value=date.today(), label_visibility="collapsed")
    
    with release_info_col2:
        st.caption("🏷️ 출고 유형")
        st.info(f"**{release_type}**")
    
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    
    # 선택된 품목 및 수량 저장용 세션 상태 초기화
    if "release_selected_items" not in st.session_state:
        st.session_state.release_selected_items = {}  # {product_code: {"qty": float, "unit": str, "checked": bool}}
    
    # 검색 필터
    st.markdown("#### 🔍 품목 검색")
    search_col1, search_col2 = st.columns([3, 1])
    with search_col1:
        with st.form("release_category_search_form", clear_on_submit=False):
            st.caption("품목명 또는 코드번호로 검색 가능")
            search_term = st.text_input(
                "품목 검색",
                key="release_category_search_input",
                placeholder="품목명 또는 코드번호로 검색",
                label_visibility="collapsed"
            )
            search_submitted = st.form_submit_button("검색", use_container_width=True, type="primary")
            
            if search_submitted:
                if search_term and search_term.strip():
                    st.session_state.release_category_search = search_term.strip()
                else:
                    st.session_state.release_category_search = ""
    
    if "release_category_search" not in st.session_state:
        st.session_state.release_category_search = ""
    
    with search_col2:
        st.markdown("<div style='height: 37px'></div>", unsafe_allow_html=True)
        if st.button("🔄 선택 초기화", key="release_clear_selection", use_container_width=True):
            st.session_state.release_selected_items = {}
            st.rerun()
    
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    
    # 재고 계산
    stock_map = calc_stock_map()
    
    # 전체 재료 목록 (등록된 품목만 사용)
    all_available_products = list(st.session_state.products)
    
    # 검색 필터링
    if st.session_state.release_category_search:
        search_term_lower = st.session_state.release_category_search.lower()
        filtered_products = [
            p for p in all_available_products
            if search_term_lower in p.get('name', '').lower() or search_term_lower in p.get('code', '').lower()
        ]
    else:
        filtered_products = all_available_products
    
    # 카테고리별로 그룹화
    products_by_category = {}
    for product in filtered_products:
        category = product.get("category", "기타")
        if category not in products_by_category:
            products_by_category[category] = []
        products_by_category[category].append(product)
    
    # 카테고리별로 표시 (토글 기능)
    if len(filtered_products) == 0:
        st.warning("등록된 품목이 없거나 검색 결과가 없습니다.")
    else:
        for category, products in sorted(products_by_category.items()):
            # 카테고리별 품목 개수 계산
            checked_count = sum(1 for p in products 
                               if st.session_state.release_selected_items.get(p.get("code", ""), {}).get("checked", False))
            
            # 카테고리명에 선택된 품목 개수 표시
            category_label = f"📁 {category} ({len(products)}개"
            if checked_count > 0:
                category_label += f", 선택: {checked_count}개"
            category_label += ")"
            
            # 토글로 카테고리 표시
            with st.expander(category_label, expanded=True):
                # 테이블 헤더
                st.markdown('<div class="table-header">', unsafe_allow_html=True)
                header_col1, header_col2, header_col3, header_col4, header_col5, header_col6 = st.columns([0.5, 2.5, 1, 1.5, 1, 1.5])
                with header_col1:
                    st.markdown("**선택**")
                with header_col2:
                    st.markdown("**품목명 (코드)**")
                with header_col3:
                    st.markdown("**단위**")
                with header_col4:
                    st.markdown("**출고 수량**")
                with header_col5:
                    st.markdown("**재고**")
                with header_col6:
                    st.markdown("**상태**")
                st.markdown('</div>', unsafe_allow_html=True)
                
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                
                # 각 품목에 대해 체크박스 및 수량 입력 표시
                for idx, product in enumerate(products):
                    product_code = product.get("code", "")
                    product_name = product.get("name", "")
                    product_unit = product.get("unit", "g")
                    
                    # 세션 상태에서 선택 정보 가져오기
                    if product_code not in st.session_state.release_selected_items:
                        st.session_state.release_selected_items[product_code] = {
                            "qty": 1,
                            "unit": product_unit,
                            "checked": False
                        }
                    
                    item_info = st.session_state.release_selected_items[product_code]
                    is_checked = item_info.get("checked", False)
                    
                    # 선택된 품목은 강조
                    row_style = "background-color: #fff3cd;" if is_checked else ""
                    st.markdown(f'<div class="product-row" style="{row_style}">', unsafe_allow_html=True)
                    
                    row_col1, row_col2, row_col3, row_col4, row_col5, row_col6 = st.columns([0.5, 2.5, 1, 1.5, 1, 1.5])
                    
                    with row_col1:
                        def update_checkbox(product_code_key):
                            current_checked = st.session_state.get(f"release_check_{product_code_key}", False)
                            if product_code_key not in st.session_state.release_selected_items:
                                st.session_state.release_selected_items[product_code_key] = {
                                    "qty": 1,
                                    "unit": product_unit,
                                    "checked": False
                                }
                            st.session_state.release_selected_items[product_code_key]["checked"] = current_checked
                        
                        checked = st.checkbox(
                            "",
                            value=is_checked,
                            key=f"release_check_{product_code}",
                            on_change=update_checkbox,
                            args=(product_code,)
                        )
                    
                    with row_col2:
                        st.markdown(f"**{product_name}**")
                        st.caption(f"📦 {product_code}")
                    
                    with row_col3:
                        st.markdown(f"**{product_unit}**")
                    
                    with row_col4:
                        if checked:
                            # 현재 재고 확인
                            current_stock = stock_map.get(product_code, {"stock": 0})["stock"]
                            
                            def update_qty(product_code_key):
                                qty_value = st.session_state.get(f"release_qty_{product_code_key}", 1)
                                current_stock_val = stock_map.get(product_code_key, {"stock": 0})["stock"]
                                # 재고 범위 내로 제한
                                qty_val = int(qty_value)
                                if qty_val < 1:
                                    qty_val = 1
                                if qty_val > current_stock_val:
                                    qty_val = max(1, current_stock_val)
                                
                                if product_code_key in st.session_state.release_selected_items:
                                    st.session_state.release_selected_items[product_code_key]["qty"] = qty_val
                            
                            current_qty = item_info.get("qty", 1)
                            # 기존 값이 범위를 벗어나면 조정
                            if current_qty < 1:
                                current_qty = 1
                            if current_qty > current_stock:
                                current_qty = max(1, current_stock)
                            
                            # 재고가 0이면 입력 불가
                            if current_stock <= 0:
                                st.error("재고 없음")
                            else:
                                qty_input = st.number_input(
                                    "출고 수량",
                                    min_value=1,
                                    max_value=int(current_stock),
                                    step=1,
                                    value=int(current_qty),
                                    key=f"release_qty_{product_code}",
                                    label_visibility="collapsed",
                                    on_change=update_qty,
                                    args=(product_code,)
                                )
                                # 실시간 업데이트를 위해 (정수로 변환, 재고 범위 내로 제한)
                                if f"release_qty_{product_code}" in st.session_state:
                                    qty_val = int(st.session_state[f"release_qty_{product_code}"])
                                    if qty_val < 1:
                                        qty_val = 1
                                    if qty_val > current_stock:
                                        qty_val = max(1, current_stock)
                                    st.session_state.release_selected_items[product_code]["qty"] = qty_val
                        else:
                            st.write("-")
                    
                    with row_col5:
                        current_stock = stock_map.get(product_code, {"stock": 0})["stock"]
                        st.markdown(f"**{current_stock}**")
                    
                    with row_col6:
                        if checked:
                            qty_to_release = int(st.session_state.release_selected_items[product_code].get("qty", 1))
                            current_stock = stock_map.get(product_code, {"stock": 0})["stock"]
                            if qty_to_release > 0:
                                if current_stock >= qty_to_release:
                                    st.success("✅ 가능")
                                else:
                                    st.error(f"❌ 부족 (재고: {current_stock})")
                            else:
                                st.info("수량 입력 필요")
                        else:
                            st.write("-")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # 마지막 항목이 아니면 구분선
                    if idx < len(products) - 1:
                        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    
    # 선택된 품목 요약
    selected_items_summary = [
        (code, info) for code, info in st.session_state.release_selected_items.items()
        if info.get("checked", False) and info.get("qty", 1) > 0
    ]
    
    if len(selected_items_summary) > 0:
        st.markdown('<div class="summary-section">', unsafe_allow_html=True)
        st.markdown("### 📋 선택된 출고 품목 요약")
        
        summary_col1, summary_col2, summary_col3, summary_col4 = st.columns([2.5, 1.5, 1, 1.5])
        with summary_col1:
            st.markdown("**품목명 (코드)**")
        with summary_col2:
            st.markdown("**출고 수량**")
        with summary_col3:
            st.markdown("**재고**")
        with summary_col4:
            st.markdown("**상태**")
        
        st.markdown("---")
        
        all_valid = True
        for idx, (product_code, item_info) in enumerate(selected_items_summary):
            # 품목 정보 찾기
            product = None
            for p in all_available_products:
                if p.get("code") == product_code:
                    product = p
                    break
            
            if product:
                product_name = product.get("name", "")
                qty_to_release = int(item_info.get("qty", 1))
                unit = item_info.get("unit", "g")
                current_stock = stock_map.get(product_code, {"stock": 0})["stock"]
                
                sum_col1, sum_col2, sum_col3, sum_col4 = st.columns([2.5, 1.5, 1, 1.5])
                
                with sum_col1:
                    st.write(f"**{product_name}**")
                    st.caption(f"코드: {product_code}")
                
                with sum_col2:
                    st.write(f"**{qty_to_release}** {unit}")
                
                with sum_col3:
                    st.write(f"{current_stock}")
                
                with sum_col4:
                    if current_stock >= qty_to_release:
                        st.success("✅ 가능")
                    else:
                        st.error(f"❌ 부족")
                        all_valid = False
                
                # 마지막 항목이 아니면 구분선
                if idx < len(selected_items_summary) - 1:
                    st.markdown("---")
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    
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
            submitted = st.form_submit_button("✅ 출고 완료", use_container_width=True, type="primary")
        
        if submitted:
            # 선택된 품목 중 수량이 0보다 큰 항목만 가져오기
            selected_items_to_release = [
                (code, info) for code, info in st.session_state.release_selected_items.items()
                if info.get("checked", False) and info.get("qty", 1) > 0
            ]
            
            if len(selected_items_to_release) == 0:
                st.warning("출고할 품목을 선택하고 수량을 입력하세요.")
            else:
                # 재고 확인
                stock_map = calc_stock_map()
                all_sufficient = True
                insufficient_items = []
                
                # 전체 재료 목록 (등록된 품목만 사용)
                all_available_products = list(st.session_state.products)
                
                for product_code, item_info in selected_items_to_release:
                    qty = int(item_info.get("qty", 1))
                    current_stock = stock_map.get(product_code, {"stock": 0})["stock"]
                    
                    # 품목 정보 찾기
                    product = None
                    for p in all_available_products:
                        if p.get("code") == product_code:
                            product = p
                            break
                    
                    product_name = product.get("name", "") if product else product_code
                    
                    if qty > current_stock:
                        all_sufficient = False
                        insufficient_items.append({
                            "name": product_name,
                            "required": qty,
                            "available": current_stock
                        })
                
                if not all_sufficient:
                    error_msg = "재고 부족:\n"
                    for item in insufficient_items:
                        error_msg += f"- {item['name']}: 필요 {item['required']}, 재고 {item['available']}\n"
                    st.error(error_msg)
                else:
                    # 모든 선택된 품목 출고 등록
                    release_count = 0
                    for product_code, item_info in selected_items_to_release:
                        # 품목 정보 찾기
                        product = None
                        for p in all_available_products:
                            if p.get("code") == product_code:
                                product = p
                                break
                        
                        product_name = product.get("name", "") if product else product_code
                        qty = int(item_info.get("qty", 0))
                        
                        st.session_state.releases.append({
                            "product_code": product_code,
                            "product_name": product_name,
                            "qty": qty,
                            "price": 0,
                            "date": str(release_date),
                            "note": out_reason or f"{release_type}",
                            "release_type": release_type,
                            "staff": staff_name,
                            "reason": out_reason or f"{release_type}"
                        })
                        release_count += 1
                    
                    st.success(f"✅ 총 {release_count}개 품목이 출고되었습니다.")
                    # 선택 초기화
                    st.session_state.release_selected_items = {}
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