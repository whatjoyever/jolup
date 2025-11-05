import os, sys
import streamlit as st
from datetime import datetime

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
st.set_page_config(page_title="발주 등록", page_icon="📝", layout="wide")
render_sidebar("receive")

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

# 품목 검색 (Form 형태)
st.markdown("### 🔍 검색")
with st.form("order_register_search_form", clear_on_submit=False):
    st.caption("품목명 또는 코드번호로 검색 가능")
    product_search = st.text_input("검색", key="order_register_product_search",
                                   label_visibility="collapsed", 
                                   placeholder="품목명 또는 코드번호로 검색 가능")
    search_submitted = st.form_submit_button("검색", use_container_width=True, type="primary")
    
    # 검색어를 session_state에 저장
    if search_submitted:
        if product_search and product_search.strip():
            st.session_state.order_register_search_term = product_search.strip()
        else:
            st.session_state.order_register_search_term = ""

# 검색어 초기화 (세션 상태에 없으면)
if "order_register_search_term" not in st.session_state:
    st.session_state.order_register_search_term = ""

# 검색 필터링
if st.session_state.order_register_search_term:
    search_term = st.session_state.order_register_search_term.lower()
    st.session_state.receive_search_results = [
        p for p in st.session_state.products 
        if search_term in p.get("name", "").lower() or search_term in p.get("code", "").lower()
    ]
else:
    st.session_state.receive_search_results = st.session_state.products

# 검색 결과 표시
if len(st.session_state.products) == 0:
    st.warning("등록된 품목이 없습니다. 기본정보 페이지에서 품목을 먼저 등록하세요.")
elif st.session_state.receive_search_results:
    st.caption("검색 결과")
    product_options = [f"{p['name']} ({p['code']})" for p in st.session_state.receive_search_results]
    selected_option = st.selectbox("품목 선택", options=product_options,
                                   key="order_register_product_select", label_visibility="collapsed")
    selected_idx = product_options.index(selected_option)
    st.session_state.receive_selected_product = st.session_state.receive_search_results[selected_idx]
    st.info(f"선택된 품목: {st.session_state.receive_selected_product['name']} "
            f"({st.session_state.receive_selected_product['code']})")
else:
    st.warning("검색 결과가 없습니다.")

# 발주 등록 폼
with st.form("order_register_form", clear_on_submit=True):
    # 거래처 선택
    st.caption("거래처 선택")
    if "partners" in st.session_state and len(st.session_state.partners) > 0:
        partner_options = [f"{p['name']} ({p['code']})" for p in st.session_state.partners]
        selected_partner_idx = st.selectbox(
            "거래처",
            options=range(len(partner_options)),
            format_func=lambda x: partner_options[x],
            key="order_register_partner_select",
            label_visibility="collapsed"
        )
        selected_partner = st.session_state.partners[selected_partner_idx]
    else:
        st.info("💡 거래처를 먼저 등록해주세요. (기본정보 > 목록보기 > 거래처 목록)")
        selected_partner = None
    
    r2c1, r2c2, r2c3 = st.columns([1, 1, 1])
    with r2c1:
        st.caption("발주 수량")
        receive_qty = st.number_input("발주 수량", min_value=1, step=1, value=1,
                                      key="order_register_qty_input", label_visibility="collapsed")
    with r2c2:
        st.caption("발주 단가")
        default_price = st.session_state.receive_selected_product.get("price", 0) \
            if st.session_state.receive_selected_product else 0
        default_price_str = f"{default_price:,}" if default_price > 0 else ""
        receive_price_input = st.text_input("발주 단가", value=default_price_str,
                                            key="order_register_price_input", label_visibility="collapsed",
                                            placeholder="100000")
        # 숫자만 추출
        if receive_price_input:
            price_clean = ''.join(filter(str.isdigit, receive_price_input.replace(",", "")))
            receive_price = int(price_clean) if price_clean else 0
            if receive_price:
                st.caption(f"입력값: {receive_price:,}원")
        else:
            receive_price = 0
    with r2c3:
        st.caption("발주일")
        receive_date = st.date_input("발주일", key="order_register_date_input", label_visibility="collapsed")

    r3c1, r3c2 = st.columns([2, 1])
    with r3c1:
        st.caption("비고")
        receive_note = st.text_input("비고", key="order_register_note_input",
                                     label_visibility="collapsed", placeholder="입고 관련 메모")
    with r3c2:
        st.markdown("<div style='height: 37px'></div>", unsafe_allow_html=True)
        submitted = st.form_submit_button("등록", use_container_width=True)

    if submitted:
        if st.session_state.receive_selected_product is None:
            st.warning("품목을 선택하세요.")
        else:
            # 거래처 정보 추가
            partner_info = None
            if selected_partner:
                partner_info = {
                    "code": selected_partner.get("code", ""),
                    "name": selected_partner.get("name", ""),
                    "business_number": selected_partner.get("business_number", ""),
                    "representative": selected_partner.get("representative", ""),
                    "address": selected_partner.get("address", ""),
                    "phone": selected_partner.get("phone", "")
                }
            
            st.session_state.receives.append({
                "product_code": st.session_state.receive_selected_product["code"],
                "product_name": st.session_state.receive_selected_product["name"],
                "category": st.session_state.receive_selected_product.get("category", ""),
                "unit": st.session_state.receive_selected_product.get("unit", ""),
                "quantity": receive_qty,
                "price": receive_price,
                "date": str(receive_date),
                "note": receive_note,
                "partner": partner_info,  # 거래처 정보 추가
                "is_received": False
            })
            st.success("발주 내역이 등록되었습니다.")
            st.session_state.receive_search_results = []
            st.session_state.receive_selected_product = None
            st.rerun()

