import os
import streamlit as st
from dotenv import load_dotenv
import requests

# -----------------------------
# 환경 설정
# -----------------------------
load_dotenv()
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Stock Mate", layout="wide")

# -----------------------------
# 헬퍼 함수
# -----------------------------
def api_get(path: str, params: dict | None = None, timeout: int = 10):
    """FastAPI 백엔드 GET 요청"""
    try:
        r = requests.get(f"{API_URL}{path}", params=params, timeout=timeout)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)

# -----------------------------
# CSS (버튼 크기, 정렬)
# -----------------------------
st.markdown("""
<style>
/* 메인 컨테이너 살짝 넓게 */
.block-container {
    max-width: 1100px !important;
    margin: 0 auto !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
}

/* 버튼 스타일 */
.stButton > button {
    display: block;                 /* 가운데 정렬 위해 block 으로 */
    margin: 0 auto;                 /* 좌우 중앙 정렬 */
    width: 260px !important;        /* 버튼 가로폭 */
    height: 160px !important;
    font-size: 28px !important;
    font-weight: 800 !important;
    border-radius: 22px !important;
    background: #f8f9fa !important;
    border: 2px solid #e0e0e0 !important;
    color: #1f1f1f !important;
    box-shadow: 0 6px 15px rgba(0,0,0,0.15) !important;
    transition: all .2s ease !important;
}
.stButton > button:hover {
    background: #e9ecef !important;
    transform: translateY(-3px) !important;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# 타이틀
# -----------------------------
st.markdown(
    "<h1 style='text-align:center; font-size:72px; color:#1f4e79; font-weight:800; margin:24px 0 8px;'>Stock Mate</h1>",
    unsafe_allow_html=True
)

# -----------------------------
# 메인 버튼 (중앙 2x2)
# -----------------------------
left, center, right = st.columns([1, 8, 1])

with center:
    # 첫 번째 줄
    row1_col1, row1_col2 = st.columns(2, gap="large")
    with row1_col1:
        if st.button("⚙️ 기본정보", use_container_width=False):
            st.switch_page("pages/info.py")
    with row1_col2:
        if st.button("🧾 입고관리", use_container_width=False):
            st.switch_page("pages/receive.py")

    # 두 번째 줄
    row2_col1, row2_col2 = st.columns(2, gap="large")
    with row2_col1:
        if st.button("📤 출고관리", use_container_width=False):
            st.switch_page("pages/release.py")
    with row2_col2:
        if st.button("📦 재고현황", use_container_width=False):
            st.switch_page("pages/inventory.py")

