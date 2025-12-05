import os, sys
import streamlit as st
from datetime import datetime, date, timedelta

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
st.set_page_config(
    page_title="발주 등록",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)
render_sidebar("receive")

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
    .order-items-scrollable {
        max-height: 400px;
        overflow-y: auto;
        overflow-x: hidden;
        padding-right: 8px;
    }
    .order-items-scrollable > * {
        margin: 0;
    }
    .order-items-scrollable::-webkit-scrollbar {
        width: 8px;
    }
    .order-items-scrollable::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 4px;
    }
    .order-items-scrollable::-webkit-scrollbar-thumb {
        background: #888;
        border-radius: 4px;
    }
    .order-items-scrollable::-webkit-scrollbar-thumb:hover {
        background: #555;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------
# 세션 상태 초기화
# -------------------------------
if "products" not in st.session_state:
    st.session_state.products = []
if "partners" not in st.session_state:
    st.session_state.partners = []
if "receives" not in st.session_state:
    st.session_state.receives = []
if "receive_search_results" not in st.session_state:
    st.session_state.receive_search_results = []
if "receive_selected_product" not in st.session_state:
    st.session_state.receive_selected_product = None
# 발주 등록 임시 목록 (거래처별 여러 품목 추가용)
if "order_register_temp_items" not in st.session_state:
    st.session_state.order_register_temp_items = []
if "order_register_selected_partner" not in st.session_state:
    st.session_state.order_register_selected_partner = None
if "order_register_common_date" not in st.session_state:
    st.session_state.order_register_common_date = date.today()
if "order_register_common_delivery_date" not in st.session_state:
    st.session_state.order_register_common_delivery_date = date.today() + timedelta(days=7)
if "order_register_common_note" not in st.session_state:
    st.session_state.order_register_common_note = ""
if "recommended_items_added" not in st.session_state:
    st.session_state.recommended_items_added = set()  # 발주 추가된 추천 품목 코드 저장
if "order_register_auto_select_product" not in st.session_state:
    st.session_state.order_register_auto_select_product = None  # 자동 선택할 품목 코드

# -------------------------------
# 헤더 & 뒤로가기 버튼
# -------------------------------
title_col, button_col = st.columns([4, 1])
with title_col:
    st.title("발주 등록")
with button_col:
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
    if st.button("← 뒤로가기", use_container_width=True, key="back_button"):
        st.switch_page("pages/receive.py")

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# -------------------------------
# 재고 계산 함수 (inventory.py와 동일한 로직)
# -------------------------------
UNIT_CONVERT = {
    ("kg", "g"): 1000.0,
    ("g", "kg"): 0.001,
    ("L", "ml"): 1000.0,
    ("ml", "L"): 0.001,
}

def convert_qty(qty: float, from_unit: str | None, to_unit: str | None) -> float:
    """단위 변환 (kg↔g, L↔ml). 정의되지 않은 조합은 값 그대로."""
    if qty is None:
        return 0.0
    if not from_unit or not to_unit or from_unit == to_unit:
        return float(qty)
    factor = UNIT_CONVERT.get((from_unit, to_unit))
    if factor is None:
        return float(qty)
    return float(qty) * factor

def get_product_base_unit(product_code: str) -> str:
    """품목별 기준 단위 결정."""
    for p in st.session_state.products:
        if p.get("code") == product_code:
            u = (p.get("unit") or "").strip()
            if u in ("kg", "g"):
                return "g"
            if u in ("L", "ml"):
                return "ml"
            return u or "g"
    return "g"

def get_stock_by_code(product_code: str) -> tuple[float, str]:
    """해당 품목의 현재 재고를 (수량, 기준단위) 형태로 반환."""
    base_unit = get_product_base_unit(product_code)
    
    total_in = 0.0
    for r in st.session_state.get("received_items", []):
        if r.get("product_code") != product_code:
            continue
        qty = float(r.get("actual_qty", 0) or 0)
        from_unit = (r.get("unit") or base_unit).strip()
        total_in += convert_qty(qty, from_unit, base_unit)
    
    total_out = 0.0
    for o in st.session_state.get("releases", []):
        if o.get("product_code") != product_code:
            continue
        qty = float(o.get("qty", 0) or 0)
        from_unit = (o.get("unit") or base_unit).strip()
        total_out += convert_qty(qty, from_unit, base_unit)
    
    return total_in - total_out, base_unit

# -------------------------------
# 발주 추천 품목 섹션
# -------------------------------
if "received_items" not in st.session_state:
    st.session_state.received_items = []
if "releases" not in st.session_state:
    st.session_state.releases = []

# 안전재고 미달 품목 찾기
low_stock_items = []
for product in st.session_state.products:
    if product.get("status") != "사용":  # 사용 중인 품목만
        continue
    
    product_code = product.get("code", "")
    if not product_code:
        continue
    
    safety_stock = float(product.get("safety", 0) or 0)
    if safety_stock <= 0:
        continue
    
    current_stock, base_unit = get_stock_by_code(product_code)
    display_unit = (product.get("unit") or "").strip() or base_unit
    stock_display = convert_qty(current_stock, base_unit, display_unit)
    
    if stock_display < safety_stock:
        low_stock_items.append({
            "product": product,
            "current_stock": stock_display,
            "safety_stock": safety_stock,
            "unit": display_unit,
            "reason": "안전재고 미달"
        })

# 유통기한 임박 품목 찾기 (7일 이내)
expiring_items = []
today = date.today()
expiry_threshold = today + timedelta(days=7)

for received_item in st.session_state.get("received_items", []):
    expiry_str = received_item.get("expiry", "")
    if not expiry_str:
        continue
    
    try:
        # 날짜 파싱
        if isinstance(expiry_str, date):
            expiry_date = expiry_str
        elif isinstance(expiry_str, str):
            expiry_str_clean = expiry_str.strip()
            if " " in expiry_str_clean:
                expiry_str_clean = expiry_str_clean.split(" ")[0]
            
            if len(expiry_str_clean) >= 10:
                date_part = expiry_str_clean[:10]
                try:
                    expiry_date = datetime.strptime(date_part, "%Y-%m-%d").date()
                except ValueError:
                    try:
                        expiry_date = datetime.strptime(date_part, "%Y/%m/%d").date()
                    except ValueError:
                        try:
                            expiry_date = datetime.strptime(date_part, "%Y.%m.%d").date()
                        except ValueError:
                            continue
            else:
                continue
        else:
            continue
        
        # 유통기한이 임박한지 확인 (7일 이내)
        if today <= expiry_date <= expiry_threshold:
            product_code = received_item.get("product_code", "")
            # 해당 품목 정보 찾기
            product_info = None
            for p in st.session_state.products:
                if p.get("code") == product_code:
                    product_info = p
                    break
            
            if product_info and product_info.get("status") == "사용":
                # 이미 추가된 품목인지 확인
                already_added = False
                for item in expiring_items:
                    if item["product"].get("code") == product_code:
                        already_added = True
                        break
                
                if not already_added:
                    days_left = (expiry_date - today).days
                    expiring_items.append({
                        "product": product_info,
                        "expiry_date": expiry_date,
                        "days_left": days_left,
                        "reason": f"유통기한 임박 ({days_left}일 남음)"
                    })
    except Exception:
        continue

# 발주 추천 품목이 있으면 표시
recommended_items = low_stock_items + expiring_items

# 이미 발주 추가된 품목은 제외
recommended_items = [
    item for item in recommended_items 
    if item["product"].get("code", "") not in st.session_state.get("recommended_items_added", set())
]

# 각 추천 품목에 대해 이전 거래 내역에서 거래처 및 단가 정보 찾기
def get_previous_transaction(product_code: str):
    """해당 품목의 이전 거래 내역에서 거래처 및 단가 정보 찾기"""
    # receives에서 해당 품목의 최근 거래 내역 찾기 (최신순으로)
    for receive in reversed(st.session_state.get("receives", [])):
        if receive.get("product_code") == product_code:
            partner = receive.get("partner")
            partner_name = None
            price = receive.get("price", 0)
            
            if partner:
                if isinstance(partner, dict):
                    partner_name = partner.get("name", "")
                elif isinstance(partner, str):
                    partner_name = partner
            
            # partner_name이 직접 저장된 경우
            if not partner_name:
                partner_name = receive.get("partner_name")
            
            if partner_name or price:
                return {
                    "partner_name": partner_name,
                    "price": price
                }
    
    return None

if recommended_items:
    st.markdown("### 📋 발주 추천 품목")
    # 연한 빨간색 배경의 안내 문구
    st.markdown("""
    <div style='background-color: #ffcccc; color: #8b0000; padding: 12px; border-radius: 5px; margin-bottom: 16px; border: 1px solid #ff9999;'>
        <strong>💡 안전재고 미달 또는 유통기한이 임박한 품목입니다. 발주를 권장합니다.</strong>
    </div>
    """, unsafe_allow_html=True)
    
    # 추천 품목 목록 표시
    for idx, item in enumerate(recommended_items):
        product = item["product"]
        reason = item["reason"]
        product_code = product.get("code", "")
        
        # 이전 거래 내역에서 거래처 및 단가 찾기
        previous_transaction = get_previous_transaction(product_code)
        previous_partner = previous_transaction.get("partner_name") if previous_transaction else None
        previous_price = previous_transaction.get("price", 0) if previous_transaction else None
        
        with st.expander(f"⚠️ {product.get('name', '')} ({product.get('code', '')}) - {reason}", expanded=False):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**품목명:** {product.get('name', '')}")
                st.write(f"**코드:** {product.get('code', '')}")
                st.write(f"**카테고리:** {product.get('category', '-')}")
                if "current_stock" in item:
                    st.write(f"**현재 재고:** {item['current_stock']:.2f} {item['unit']}")
                    st.write(f"**안전재고:** {item['safety_stock']:.2f} {item['unit']}")
                if "expiry_date" in item:
                    st.write(f"**유통기한:** {item['expiry_date']}")
                    st.write(f"**남은 일수:** {item['days_left']}일")
            with col2:
                st.write(f"**단위:** {product.get('unit', '-')}")
                if previous_partner:
                    st.write(f"**이전 거래처:** {previous_partner}")
                else:
                    st.write(f"**이전 거래처:** -")
                if previous_price and previous_price > 0:
                    st.write(f"**이전 단가:** {previous_price:,}원")
                else:
                    st.write(f"**이전 단가:** -")
            with col3:
                if st.button("➕ 발주 추가", key=f"add_recommended_{product.get('code', '')}_{idx}", use_container_width=True):
                    # 거래처가 선택되어 있으면 바로 추가
                    if st.session_state.order_register_selected_partner:
                        product_code = product.get("code", "")
                        # 이전 거래 단가가 있으면 우선 사용, 없으면 기본 단가 사용
                        default_price = previous_price if (previous_price and previous_price > 0) else product.get("price", 0)
                        
                        # 같은 품목이 이미 있는지 확인
                        existing_idx = None
                        for i, temp_item in enumerate(st.session_state.order_register_temp_items):
                            if temp_item["product_code"] == product_code:
                                existing_idx = i
                                break
                        
                        if existing_idx is not None:
                            # 같은 품목이 있으면 수량만 증가 (안전재고 미달인 경우)
                            if "current_stock" in item:
                                recommended_qty = max(1, int(item["safety_stock"] - item["current_stock"]) + 1)
                                st.session_state.order_register_temp_items[existing_idx]["quantity"] += recommended_qty
                                st.success(f"✅ {product.get('name', '')} 수량이 {recommended_qty}개 증가했습니다.")
                            else:
                                st.info("이미 발주 목록에 추가된 품목입니다.")
                        else:
                            # 새로운 품목 추가
                            partner_name = st.session_state.order_register_selected_partner.get("name", "")
                            recommended_qty = 1
                            if "current_stock" in item:
                                # 안전재고 미달인 경우, 안전재고 수준까지 채우는 수량 추천
                                recommended_qty = max(1, int(item["safety_stock"] - item["current_stock"]) + 1)
                            
                            new_item = {
                                "product_code": product_code,
                                "product_name": product.get("name", ""),
                                "category": product.get("category", ""),
                                "unit": product.get("unit", ""),
                                "quantity": recommended_qty,
                                "price": default_price,
                                "partner_name": partner_name,
                            }
                            st.session_state.order_register_temp_items.append(new_item)
                            st.success(f"✅ {new_item['product_name']} ({new_item['product_code']}) {recommended_qty}개가 발주 목록에 추가되었습니다.")
                        
                        # 추천 품목 목록에서 제거하기 위해 추가된 품목 코드 저장
                        st.session_state.recommended_items_added.add(product_code)
                        # 발주 등록 폼에서 자동 선택할 품목 설정
                        st.session_state.order_register_auto_select_product = product_code
                        
                        st.rerun()
                    else:
                        st.warning("거래처를 먼저 선택해주세요.")
    
    st.markdown("---")

# -------------------------------
# 발주 등록 폼
# -------------------------------
st.subheader("발주 등록")

# 검색어 초기화 (세션 상태에 없으면)
if "order_register_search_term" not in st.session_state:
    st.session_state.order_register_search_term = ""
if "order_register_partner_search_term" not in st.session_state:
    st.session_state.order_register_partner_search_term = ""

# 통합된 발주 정보 입력 폼
with st.form("order_register_form", clear_on_submit=False):
    # 1. 공통 정보 입력 (발주일, 납기일, 비고)
    st.markdown("### 1️⃣ 공통 정보")
    common_col1, common_col2, common_col3 = st.columns([1, 1, 2])
    with common_col1:
        st.caption("발주일 (오늘 날짜)")
        today = date.today()
        # 발주일은 항상 오늘 날짜로 고정
        st.session_state.order_register_common_date = today
        st.date_input(
            "발주일", value=today, key="order_register_common_date_input", 
            label_visibility="collapsed", disabled=True,
            help="발주일은 오늘 날짜로 자동 설정됩니다.")
    with common_col2:
        st.caption("납기일")
        st.session_state.order_register_common_delivery_date = st.date_input(
            "납기일", value=st.session_state.order_register_common_delivery_date, 
            key="order_register_common_delivery_date_input",
            label_visibility="collapsed", min_value=date.today(),
            help="납기일을 선택하세요. (기본값: 오늘 + 7일)")
    with common_col3:
        st.caption("비고")
        st.session_state.order_register_common_note = st.text_input(
            "비고", value=st.session_state.order_register_common_note,
            key="order_register_common_note_input",
            label_visibility="collapsed", placeholder="발주 관련 메모 (모든 품목에 공통 적용)")

    st.markdown("---")

    # 2. 거래처 선택
    st.markdown("### 2️⃣ 거래처 선택")
    
    # 거래처 검색 입력
    st.caption("거래처명 또는 코드번호로 검색 가능")
    partner_search = st.text_input(
        "거래처 검색",
        value=st.session_state.order_register_partner_search_term,
        key="order_register_partner_search",
        label_visibility="collapsed",
        placeholder="거래처명 또는 코드번호로 검색 가능",
        help="검색어를 입력하면 거래처 목록이 자동으로 필터링됩니다."
    )
    
    # 검색어 업데이트
    if partner_search != st.session_state.order_register_partner_search_term:
        st.session_state.order_register_partner_search_term = partner_search
    
    partners = st.session_state.get("partners", [])
    
    # 검색 필터링
    if st.session_state.order_register_partner_search_term and st.session_state.order_register_partner_search_term.strip():
        search_term_partner = st.session_state.order_register_partner_search_term.strip().lower()
        filtered_partners = [
            p for p in partners
            if search_term_partner in p.get("name", "").lower() 
            or search_term_partner in p.get("code", "").lower()
            or search_term_partner in p.get("business_number", "").lower()
        ]
    else:
        filtered_partners = partners
    
    if partners and len(partners) > 0:
        if len(filtered_partners) == 0:
            st.warning("검색 결과가 없습니다.")
            selected_partner = None
        else:
            partner_options = [f"{p.get('name', '')} ({p.get('code', '')})" for p in filtered_partners]
            
            # 현재 선택된 거래처 인덱스 찾기
            current_partner_idx = 0
            if st.session_state.order_register_selected_partner:
                current_partner_code = st.session_state.order_register_selected_partner.get("code", "")
                for idx, p in enumerate(filtered_partners):
                    if p.get("code", "") == current_partner_code:
                        current_partner_idx = idx
                        break
            
            selected_partner_idx = st.selectbox(
                "거래처 선택",
                options=range(len(partner_options)),
                format_func=lambda x: partner_options[x],
                index=current_partner_idx,
                key="order_register_partner_select",
                help="위 검색창에서 검색어를 입력하면 목록이 필터링됩니다.",
                label_visibility="visible"
            )
            selected_partner = filtered_partners[selected_partner_idx]
            
            # 거래처 선택 상태 업데이트 (품목 목록은 유지)
            st.session_state.order_register_selected_partner = selected_partner
            st.success(f"✅ 선택된 거래처: **{selected_partner.get('name', '')}** (코드: {selected_partner.get('code', '')})")
    else:
        st.warning("💡 거래처를 먼저 등록해주세요. (기본정보 > 신규 등록 > 거래처 등록 탭)")
        selected_partner = None
        st.session_state.order_register_selected_partner = None

    st.markdown("---")

    # 3. 품목 추가 (검색 + 선택 + 발주 정보 입력 통합)
    if selected_partner:
        st.markdown("### 3️⃣ 품목 추가")
        
        # 검색 및 품목 선택을 하나의 섹션으로 통합
        st.markdown("#### 🔍 품목 검색 및 선택")
        
        # 검색 입력
        st.caption("품목명 또는 코드번호로 검색 가능")
        product_search = st.text_input(
            "검색",
            value=st.session_state.order_register_search_term,
            key="order_register_product_search",
            label_visibility="collapsed",
            placeholder="품목명 또는 코드번호로 검색 가능",
            help="검색어를 입력하면 품목 목록이 자동으로 필터링됩니다."
        )
        
        # 검색어 업데이트
        if product_search != st.session_state.order_register_search_term:
            st.session_state.order_register_search_term = product_search
        
        # 실시간 검색 필터링
        if st.session_state.order_register_search_term and st.session_state.order_register_search_term.strip():
            search_term = st.session_state.order_register_search_term.strip().lower()
            filtered_products = [
                p for p in st.session_state.products
                if search_term in p.get("name", "").lower() or search_term in p.get("code", "").lower()
            ]
        else:
            filtered_products = st.session_state.products
        
        # 품목 선택
        if len(st.session_state.products) == 0:
            st.warning("등록된 품목이 없습니다. 기본정보 페이지에서 품목을 먼저 등록하세요.")
            selected_product = None
        elif len(filtered_products) == 0:
            st.warning("검색 결과가 없습니다.")
            selected_product = None
        else:
            product_options = [f"{p['name']} ({p['code']})" for p in filtered_products]
            
            # 기본 선택값 설정
            default_index = 0
            
            # 자동 선택할 품목이 있으면 우선 적용
            if st.session_state.get("order_register_auto_select_product"):
                auto_select_code = st.session_state.order_register_auto_select_product
                for idx, p in enumerate(filtered_products):
                    if p.get("code", "") == auto_select_code:
                        default_index = idx
                        # 자동 선택 후 초기화
                        st.session_state.order_register_auto_select_product = None
                        break
            # 자동 선택 품목이 없으면 이전에 선택한 품목이 검색 결과에 있으면 유지
            elif st.session_state.get("receive_selected_product"):
                prev_selected = st.session_state.receive_selected_product
                prev_option = f"{prev_selected.get('name', '')} ({prev_selected.get('code', '')})"
                if prev_option in product_options:
                    default_index = product_options.index(prev_option)
            
            selected_option = st.selectbox(
                "품목 선택",
                options=product_options,
                index=default_index,
                key="order_register_product_select",
                label_visibility="visible",
                help="위 검색창에서 검색어를 입력하면 목록이 필터링됩니다."
            )
            selected_idx = product_options.index(selected_option)
            selected_product = filtered_products[selected_idx]
            st.session_state.receive_selected_product = selected_product
            
            # 발주 수량 및 단가 입력
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            st.markdown("#### 💰 발주 정보 입력")
            
            qty_price_col1, qty_price_col2 = st.columns([1, 1])
            with qty_price_col1:
                st.caption("발주 수량")
                add_qty = st.number_input(
                    "발주 수량",
                    min_value=1,
                    step=1,
                    value=1,
                    key="order_register_add_qty_input",
                    label_visibility="collapsed"
                )
            with qty_price_col2:
                st.caption("발주 단가")
                default_price = selected_product.get("price", 0) if selected_product else 0
                default_price_str = f"{default_price:,}" if default_price > 0 else ""
                add_price_input = st.text_input(
                    "발주 단가",
                    value=default_price_str,
                    key="order_register_add_price_input",
                    label_visibility="collapsed",
                    placeholder="100000"
                )
                # 숫자만 추출
                if add_price_input:
                    price_clean = ''.join(filter(str.isdigit, add_price_input.replace(",", "")))
                    add_price = int(price_clean) if price_clean else 0
                    if add_price:
                        st.caption(f"입력값: {add_price:,}원")
                else:
                    add_price = 0
        
        # 품목 추가 버튼
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        add_submitted = st.form_submit_button("➕ 품목 추가", use_container_width=True, type="primary")
        
        if add_submitted:
            if not selected_partner:
                st.warning("거래처를 먼저 선택해주세요.")
            elif selected_product is None:
                st.warning("품목을 선택하세요.")
            elif add_price == 0:
                st.warning("발주 단가를 입력하세요.")
            else:
                # 같은 품목이 이미 있는지 확인
                product_code = selected_product["code"]
                existing_idx = None
                for idx, item in enumerate(st.session_state.order_register_temp_items):
                    if item["product_code"] == product_code and item["price"] == add_price:
                        existing_idx = idx
                        break
                
                if existing_idx is not None:
                    # 같은 품목이 있으면 수량만 증가
                    st.session_state.order_register_temp_items[existing_idx]["quantity"] += add_qty
                    st.success(f"✅ {selected_product['name']} ({product_code}) 수량이 {add_qty}개 증가했습니다. (총 {st.session_state.order_register_temp_items[existing_idx]['quantity']}개)")
                else:
                    # 새로운 품목 추가
                    partner_name = selected_partner.get("name", "") if selected_partner else ""
                    new_item = {
                        "product_code": product_code,
                        "product_name": selected_product["name"],
                        "category": selected_product.get("category", ""),
                        "unit": selected_product.get("unit", ""),
                        "quantity": add_qty,
                        "price": add_price,
                        "partner_name": partner_name,
                    }
                    st.session_state.order_register_temp_items.append(new_item)
                    st.success(f"✅ {new_item['product_name']} ({new_item['product_code']}) {add_qty}개가 추가되었습니다.")
                
                # 검색어는 유지 (초기화하지 않음)
                st.rerun()

# 폼 외부에서 발주 목록 표시
st.markdown("---")

# 4. 추가된 발주 목록 확인 및 관리
if st.session_state.order_register_selected_partner:
    st.markdown("### 4️⃣ 발주 목록")
    
    if len(st.session_state.order_register_temp_items) > 0:
        # 발주 목록 테이블
        st.markdown("#### 추가된 품목")
        
        # 테이블 헤더
        header_col1, header_col2, header_col3, header_col4, header_col5, header_col6 = st.columns([2.5, 2, 1, 1, 1, 1])
        with header_col1:
            st.markdown("**품목명 (코드)**")
        with header_col2:
            st.markdown("**거래처**")
        with header_col3:
            st.markdown("**수량**")
        with header_col4:
            st.markdown("**단가**")
        with header_col5:
            st.markdown("**합계**")
        with header_col6:
            st.markdown("**작업**")
        
        st.markdown("---")
        
        # 발주 목록 아이템 (5개 이상일 때 스크롤 가능)
        items_count = len(st.session_state.order_register_temp_items)
        if items_count > 5:
            st.markdown(f'<div class="order-items-scrollable">', unsafe_allow_html=True)
        
        for idx, item in enumerate(st.session_state.order_register_temp_items):
            item_col1, item_col2, item_col3, item_col4, item_col5, item_col6 = st.columns([2.5, 2, 1, 1, 1, 1])
            with item_col1:
                st.write(f"**{item['product_name']}**")
                st.caption(f"코드: {item['product_code']}")
            with item_col2:
                partner_name = item.get("partner_name", "-")
                st.write(f"{partner_name}")
            with item_col3:
                st.write(f"{item['quantity']}개")
            with item_col4:
                st.write(f"{item['price']:,}원")
            with item_col5:
                st.write(f"**{item['quantity'] * item['price']:,}원**")
            with item_col6:
                if st.button("🗑️ 삭제", key=f"delete_item_{idx}", use_container_width=True):
                    st.session_state.order_register_temp_items.pop(idx)
                    st.rerun()
            
            if idx < len(st.session_state.order_register_temp_items) - 1:
                st.markdown("---")
        
        if items_count > 5:
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("---")
        
        # 총합 계산
        total_items = len(st.session_state.order_register_temp_items)
        total_quantity = sum(item['quantity'] for item in st.session_state.order_register_temp_items)
        total_amount = sum(item['quantity'] * item['price'] for item in st.session_state.order_register_temp_items)
        
        st.markdown("#### 📊 발주 요약")
        summary_col1, summary_col2, summary_col3 = st.columns([1, 1, 1])
        with summary_col1:
            st.metric("품목 수", f"{total_items}개")
        with summary_col2:
            st.metric("총 수량", f"{total_quantity}개")
        with summary_col3:
            st.metric("총 금액", f"{total_amount:,}원")
        
        st.markdown("---")
        
        # 5. 최종 발주 등록
        st.markdown("### 5️⃣ 발주 등록")
        final_col1, final_col2 = st.columns([1, 1])
        with final_col1:
            if st.button("🗑️ 전체 삭제", use_container_width=True, type="secondary"):
                st.session_state.order_register_temp_items = []
                st.rerun()
        with final_col2:
            if st.button("✅ 발주 등록", use_container_width=True, type="primary"):
                # 거래처 정보 추가
                partner_info = None
                selected_partner = st.session_state.order_register_selected_partner
                if selected_partner:
                    partner_info = {
                        "code": selected_partner.get("code", ""),
                        "name": selected_partner.get("name", ""),
                        "business_number": selected_partner.get("business_number", ""),
                        "representative": selected_partner.get("representative", ""),
                        "address": selected_partner.get("address", ""),
                        "phone": selected_partner.get("phone", "")
                    }
                
                # 모든 품목을 발주 목록에 추가
                for item in st.session_state.order_register_temp_items:
                    st.session_state.receives.append({
                        "product_code": item["product_code"],
                        "product_name": item["product_name"],
                        "category": item.get("category", ""),
                        "unit": item.get("unit", ""),
                        "quantity": item["quantity"],
                        "price": item["price"],
                        "date": str(st.session_state.order_register_common_date),
                        "delivery_date": str(st.session_state.order_register_common_delivery_date),
                        "note": st.session_state.order_register_common_note,
                        "partner": partner_info,
                        "is_received": False,
                        "received_qty": 0
                    })
                
                # 임시 목록 초기화
                st.session_state.order_register_temp_items = []
                st.session_state.order_register_common_note = ""
                st.session_state.receive_selected_product = None
                st.session_state.order_register_search_term = ""
                
                st.success(f"✅ {total_items}개 품목이 발주 등록되었습니다!")
                st.rerun()
    else:
        st.info("💡 품목을 추가하면 여기에 표시됩니다. 위에서 품목을 선택하고 '➕ 품목 추가' 버튼을 클릭하세요.")
else:
    st.info("💡 거래처를 먼저 선택해주세요.")