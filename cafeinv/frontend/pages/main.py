import os, sys
import streamlit as st

# --- import 경로 보정 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

from sidebar import render_sidebar
from client import api_get, api_post
# -------------------------

st.set_page_config(page_title="Stock Mate", page_icon="📦", layout="wide")
render_sidebar("main")

# ===== CSS: 카드형 버튼 디자인 =====
st.markdown("""
<style>
/* 컬럼 안에서 버튼 중앙 정렬 */
div[data-testid="column"] {
    display: flex;
    justify-content: center;
}

/* 버튼 크기: 가로로 넓고 겹치지 않게 고정 */
.stButton > button {
    width: 420px !important;         /* 가로 고정폭 */
    height: 160px !important;        /* 세로 고정높이 */
    font-size: 28px !important;      /* 글자 크기 */
    font-weight: 700 !important;
    border-radius: 20px !important;
    background-color: #f8f9fa !important;
    border: 2px solid #e0e0e0 !important;
    color: #1f1f1f !important;
    box-shadow: 0 6px 15px rgba(0,0,0,0.15) !important;
    transition: all 0.25s ease !important;
    margin: 18px !important;         /* 컬럼 간격 여유 */
    white-space: nowrap !important;  /* 줄바꿈 방지 */
}
.stButton > button:hover {
    background-color: #e9ecef !important;
    transform: translateY(-4px) !important;
    box-shadow: 0 10px 25px rgba(0,0,0,0.25) !important;
}

/* 메인 영역 중앙 정렬 */
.block-container {
    max-width: 1400px !important;
    margin: 0 auto !important;
    display: flex;
    flex-direction: column;
    align-items: center;
}

/* 버튼 사이 간격 확보 (컬럼 간격) */
section[data-testid="stHorizontalBlock"] > div {
    gap: 40px !important;
}
</style>
""", unsafe_allow_html=True)




# ===== 타이틀 =====
st.markdown(
    "<div style='text-align:center; font-size:75px; font-weight:800; color:#1f4e79; margin:40px 0;'>Stock Mate</div>",
    unsafe_allow_html=True
)

# ===== 중앙 2x2 버튼 =====
# 폭을 여유 있게 주기 위해 컬럼 3등분 구조
_, center, _ = st.columns([1, 2.5, 1])
with center:
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        if st.button("⚙️ 기본정보"):
            st.switch_page("pages/info.py")
        if st.button("📤 출고관리"):
            st.switch_page("pages/release.py")

    with col2:
        if st.button("📥 입고관리"):
            st.switch_page("pages/receive.py")
        if st.button("📦 재고현황"):
            st.switch_page("pages/inventory.py")

# ===== 백엔드 연동 테스트 =====
st.markdown("---")
st.markdown("### 🔌 백엔드 연동 테스트")
t1, t2 = st.columns(2)
with t1:
    if st.button("GET /health", use_container_width=True):
        data, err = api_get("/health")
        st.write("결과:", data if data else err)
with t2:
    if st.button("GET /inventory_tx?limit=20", use_container_width=True):
        data, err = api_get("/inventory_tx", params={"limit": 20})
        st.write("결과:", data if data else err)

st.caption(f"API_URL = {os.getenv('API_URL')}")
