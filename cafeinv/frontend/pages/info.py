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
st.set_page_config(page_title="기본정보 관리", page_icon="⚙️", layout="wide")
render_sidebar("info")

# 기본 여백/스타일
st.markdown("""
<style>
    .main .block-container {
        max-width: 100%;
        padding-top: 2rem;
        padding-right: 4rem;
        padding-left: 4rem;
        padding-bottom: 2rem;
    }
    .info-card {
        background-color: white;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .action-card {
        background-color: transparent;
        border: none;
        padding: 0;
        margin: 10px auto;
        box-shadow: none;
        text-align: center;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        align-items: center;
        width: 350px;
        max-width: 350px;
        gap: 30px;
    }
    div[data-testid="column"] {
        padding-left: 0.25rem !important;
        padding-right: 0.25rem !important;
    }
    div[data-testid="column"] > div {
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .action-card-text {
        font-size: 16px;
        color: #666;
        margin: 0 0 10px 0;
        line-height: 1.6;
        font-weight: 500;
    }
    .action-card button {
        width: 350px !important;
        max-width: 350px !important;
        margin: 0 auto;
        display: block;
    }
    .card-icon {
        font-size: 60px;
        text-align: center;
        margin: 0;
        display: block;
    }
    .icon-box {
        background-color: #f8f9fa;
        border: 2px solid #e9ecef;
        border-radius: 12px;
        padding: 20px;
        margin: 0 0 40px 0;
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 120px;
        width: 280px;
        max-width: 280px;
        box-sizing: border-box;
    }
    .icon-box .card-icon {
        margin: 0;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------
# 헤더
# -------------------------------
st.markdown("## 기본정보")
st.write("상품, 거래처 등 기본 정보를 관리하는 화면을 여기에 구성할 수 있습니다.")

st.divider()

# -------------------------------
# 메인 선택 버튼들 (카드 형태)
# -------------------------------
col1, col2, col3 = st.columns([1, 1, 1], gap="small")

with col1:
    st.markdown('<div class="action-card">', unsafe_allow_html=True)
    st.markdown('<p class="action-card-text">▼ 등록이 필요한 경우 페이지로 이동</p>', unsafe_allow_html=True)
    st.markdown('<div class="icon-box"><div class="card-icon">📝</div></div>', unsafe_allow_html=True)
    if st.button("등록하기", key="register_btn", use_container_width=False, type="primary"):
        st.switch_page("pages/info_register.py")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="action-card">', unsafe_allow_html=True)
    st.markdown('<p class="action-card-text">▼ 레시피 등록 페이지로 이동</p>', unsafe_allow_html=True)
    st.markdown('<div class="icon-box"><div class="card-icon">📖</div></div>', unsafe_allow_html=True)
    if st.button("레시피 등록", key="recipe_btn", use_container_width=False, type="primary"):
        st.switch_page("pages/recipe_register.py")
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
    st.markdown('<div class="action-card">', unsafe_allow_html=True)
    st.markdown('<p class="action-card-text">▼ 등록한 목록 확인 가능 페이지로 이동</p>', unsafe_allow_html=True)
    st.markdown('<div class="icon-box"><div class="card-icon">📋</div></div>', unsafe_allow_html=True)
    if st.button("목록보기", key="list_btn", use_container_width=False, type="primary"):
        st.switch_page("pages/info_list.py")
    st.markdown('</div>', unsafe_allow_html=True)
