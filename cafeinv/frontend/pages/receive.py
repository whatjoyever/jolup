import os, sys
import streamlit as st

# --- sidebar import 경로 보정 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

from sidebar import render_sidebar

# -------------------------------
# 페이지 설정 & 커스텀 사이드바
# -------------------------------
st.set_page_config(page_title="입고관리", page_icon="📥", layout="wide")
render_sidebar("receive")

# -------------------------------
# CSS — 버튼 넓게 / 간격 넓게 / 카드 균일화
# -------------------------------
st.markdown("""
<style>
    .main .block-container {
        max-width: 1200px;
        padding-top: 1rem;
        padding-right: 1.5rem;
        padding-left: 1.5rem;
        padding-bottom: 1rem;
    }

    /* 4개 버튼 카드 영역 – 넓은 레이아웃 */
    .action-card {
        background-color: transparent;
        padding: 0;
        margin: 20px auto;
        text-align: center;

        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: flex-start;

        width: 100%;
        max-width: 320px;   /* 카드 전체폭 더 넓게 */
        gap: 28px;          /* 카드 내부 간격 (기본정보와 동일) */
    }
    
    /* 아이콘과 버튼 사이 여백 */
    .icon-box {
        margin-bottom: 20px !important;
    }

    /* 컬럼 좌우 여백 */
    div[data-testid="column"] {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    /* 설명 텍스트 */
    .action-card-text {
        font-size: 15px;
        color: #666;
        font-weight: 500;
        margin: 0;
        padding: 0;
    }

    /* 아이콘 박스 */
    .icon-box {
        background-color: #f8f9fa;
        border: 2px solid #e9ecef;
        border-radius: 14px;

        padding: 20px;
        width: 100%;
        max-width: 260px;

        min-height: 130px;

        display: flex;
        justify-content: center;
        align-items: center;
    }

    .icon-box .card-icon {
        font-size: 60px;
        margin: 0;
        padding: 0;
    }

    /* 버튼 */
    .action-card button {
        width: 100% !important;
        max-width: 260px !important;

        height: 55px !important;
        margin: 0 auto !important;

        font-size: 18px !important;
        font-weight: 700 !important;

        border-radius: 12px !important;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------
# 세션 상태 초기화
# -------------------------------
if "products" not in st.session_state:
    st.session_state.products = []
if "receives" not in st.session_state:
    st.session_state.receives = []
if "receive_selected" not in st.session_state:
    st.session_state.receive_selected = set()
if "receive_edit_mode" not in st.session_state:
    st.session_state.receive_edit_mode = False
if "received_items" not in st.session_state:
    st.session_state.received_items = []
if "staff_list" not in st.session_state:
    st.session_state.staff_list = ["김철수", "이영희", "박민수", "정수진"]
if "partners" not in st.session_state:
    st.session_state.partners = []

# -------------------------------
# 헤더
# -------------------------------
st.markdown("## 입고관리")
st.write("상품 입고 내역을 등록하고 조회합니다.")

st.divider()

# -------------------------------
# 메인 선택 버튼들 (카드 형태)
# -------------------------------
col1, col2, col3, col4 = st.columns([1, 1, 1, 1], gap="large")

with col1:
    st.markdown('<div class="action-card">', unsafe_allow_html=True)
    st.markdown('<p class="action-card-text">▼ 발주 등록 페이지로 이동</p>', unsafe_allow_html=True)
    st.markdown('<div class="icon-box"><div class="card-icon">📝</div></div>', unsafe_allow_html=True)
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
    if st.button("발주 등록", key="order_register_btn", use_container_width=False, type="primary"):
        st.switch_page("pages/order_register.py")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="action-card">', unsafe_allow_html=True)
    st.markdown('<p class="action-card-text">▼ 발주 목록 확인 페이지로 이동</p>', unsafe_allow_html=True)
    st.markdown('<div class="icon-box"><div class="card-icon">📋</div></div>', unsafe_allow_html=True)
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
    if st.button("발주 목록", key="order_list_btn", use_container_width=False, type="primary"):
        st.switch_page("pages/order_list.py")
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
    st.markdown('<div class="action-card">', unsafe_allow_html=True)
    st.markdown('<p class="action-card-text">▼ 입고 등록 페이지로 이동</p>', unsafe_allow_html=True)
    st.markdown('<div class="icon-box"><div class="card-icon">📦</div></div>', unsafe_allow_html=True)
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
    if st.button("입고 등록", key="receive_register_btn", use_container_width=False, type="primary"):
        st.switch_page("pages/receive_register.py")
    st.markdown('</div>', unsafe_allow_html=True)

with col4:
    st.markdown('<div class="action-card">', unsafe_allow_html=True)
    st.markdown('<p class="action-card-text">▼ 입고 내역 확인 페이지로 이동</p>', unsafe_allow_html=True)
    st.markdown('<div class="icon-box"><div class="card-icon">📊</div></div>', unsafe_allow_html=True)
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
    if st.button("입고 내역", key="receive_history_btn", use_container_width=False, type="primary"):
        st.switch_page("pages/receive_history.py")
    st.markdown('</div>', unsafe_allow_html=True)
