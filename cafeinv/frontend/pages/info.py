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

# -------------------------------
# CSS 수정본 (겹침 방지 + 넓은 버튼)
# -------------------------------
st.markdown("""
<style>
    /* 메인 컨테이너 */
    .main .block-container {
        max-width: 1200px;
        padding-top: 1rem;
        padding-right: 1.5rem;
        padding-left: 1.5rem;
        padding-bottom: 1rem;
    }

    /* 전체 카드 공통 */
    .action-card {
        background-color: transparent;
        border: none;
        padding: 0;
        margin: 20px auto;
        text-align: center;

        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        align-items: center;

        width: 100%;
        max-width: 380px;    /* 버튼+아이콘 넓이 안정적 */
        gap: 28px;
    }

    /* 컬럼 padding */
    div[data-testid="column"] {
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }

    /* 설명 텍스트 */
    .action-card-text {
        font-size: 16px;
        color: #555;
        margin: 0 0 6px 0;
        font-weight: 500;
    }

    /* 아이콘 박스 */
    .icon-box {
        background-color: #f8f9fa;
        border: 2px solid #e9ecef;
        border-radius: 14px;
        padding: 20px;

        display: flex;
        align-items: center;
        justify-content: center;

        min-height: 130px;
        width: 100%;
        max-width: 300px;    /* 더 넓은 아이콘 박스 */
    }

    .icon-box .card-icon {
        font-size: 62px;
        margin: 0;
    }

    /* 버튼 */
    .action-card button {
        width: 100% !important;
        max-width: 300px !important;
        height: 60px !important;

        font-size: 20px !important;
        font-weight: 700 !important;
        border-radius: 12px !important;

        margin: 0 auto !important;
        display: block;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------
# 헤더
# -------------------------------
st.markdown("## 기본정보")
st.write("상품, 거래처 등 기본 정보를 관리하는 화면입니다.")

st.divider()

# -------------------------------
# 메인 선택 버튼들
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
