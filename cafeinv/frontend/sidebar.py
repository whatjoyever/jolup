import streamlit as st

def render_sidebar(active: str = "main"):
    # 기본 페이지 네비 숨김
    st.markdown("""
    <style>
      [data-testid="stSidebarNav"] { display: none; }
      /* ✅ 사이드바 버튼은 가로폭 100%, 컴팩트 사이즈 */
      [data-testid="stSidebar"] .stButton > button {
        width: 100% !important;
        height: 44px !important;
        font-size: 16px !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
        margin: 6px 0 !important;
      }
    </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("<h3>📋 메뉴</h3>", unsafe_allow_html=True)
        st.divider()
        if st.button(("✅ 🏠 메인" if active=="main" else "🏠 메인"), use_container_width=True):
            st.switch_page("pages/main.py")
        if st.button(("✅ ⚙️ 기본정보" if active=="info" else "⚙️ 기본정보"), use_container_width=True):
            st.switch_page("pages/info.py")
        if st.button(("✅ 📥 입고관리" if active=="receive" else "📥 입고관리"), use_container_width=True):
            st.switch_page("pages/receive.py")
        if st.button(("✅ 📤 출고관리" if active=="release" else "📤 출고관리"), use_container_width=True):
            st.switch_page("pages/release.py")
        if st.button(("✅ 📦 재고현황" if active=="inventory" else "📦 재고현황"), use_container_width=True):
            st.switch_page("pages/inventory.py")
        st.divider()
        st.caption("Stock Mate © 2025")
