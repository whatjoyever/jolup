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
# CSS (버튼 크기, 정렬, 겹침 방지)
# -----------------------------
st.markdown("""
<style>
/* 메인 컨테이너 중앙정렬 */
.block-container {
    max-width: 1120px !important;
    margin: 0 auto !important;
    padding-left: 4rem !important;
    padding-right: 4rem !important;
}

/* 컬럼 내부 버튼 중앙정렬 */
div[data-testid="column"] {
    display: flex;
    justify-content: center;
}

/* 버튼 스타일 */
.stButton > button {
    width: 100% !important;
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

/* 컬럼 간 간격 확보 */
section[data-testid="stHorizontalBlock"] > div {
    gap: 80px !important;
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
# 메인 버튼 (중앙 2열)
# -----------------------------
left, center, right = st.columns([1, 8, 1])
with center:
    # 첫 번째 줄
    col1, col2 = st.columns(2, gap="large")
    with col1:
        if st.button("⚙️ 기본정보", use_container_width=True):
            st.switch_page("pages/info.py")
    with col2:
        if st.button("🧾 입고관리", use_container_width=True):
            st.switch_page("pages/receive.py")

    # 두 번째 줄
    col3, col4 = st.columns(2, gap="large")
    with col3:
        if st.button("📤 출고관리", use_container_width=True):
            st.switch_page("pages/release.py")
    with col4:
        if st.button("📦 재고현황", use_container_width=True):
            st.switch_page("pages/inventory.py")

# -----------------------------
# 백엔드 연동 테스트
# -----------------------------
st.markdown("---")
st.subheader("🔌 백엔드 연동 테스트")

t1, t2 = st.columns(2, gap="large")
with t1:
    if st.button("GET /health", use_container_width=True):
        data, err = api_get("/health")
        st.write("결과:", data if data else err)
with t2:
    if st.button("GET /inventory_tx?limit=20", use_container_width=True):
        data, err = api_get("/inventory_tx", params={"limit": 20})
        st.write("결과:", data if data else err)

st.caption(f"API_URL = {API_URL}")
