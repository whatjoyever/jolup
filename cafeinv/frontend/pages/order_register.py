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
            
            # 기본 선택값 설정 (이전에 선택한 품목이 검색 결과에 있으면 유지)
            default_index = 0
            if st.session_state.get("receive_selected_product"):
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