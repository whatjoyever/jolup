# file: login.py
import os, sys
import streamlit as st

# ✅ sidebar import 경로 보정 (import는 하지 않음!)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "."))  # frontend 디렉토리
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

DEST_MAIN = "pages/main.py"   # ✅ 메인 페이지 경로

st.set_page_config(
    page_title="Stock Mate - 로그인",
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items=None,
)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ✅ 로그인 상태면 즉시 main.py로
if st.session_state.logged_in:
    st.switch_page(DEST_MAIN)
    st.stop()

# ---------- 로그인 화면 ----------
st.markdown("""
<style>
[data-testid="stSidebar"],
[data-testid="stSidebarNav"],
[data-testid="collapsedControl"]{display:none !important;}
.block-container{max-width:1100px; padding-top:2.4rem;}
.deco{display:flex;align-items:center;gap:12px;margin:16px 0 28px;}
.deco .dot{width:12px;height:12px;background:#0B3B75;border-radius:50%;}
.deco .line{flex:1;height:3px;background:#0B3B75;}
</style>
""", unsafe_allow_html=True)

st.markdown(
    '<h1 style="text-align:center; font-size:72px; font-weight:800; color:#0B3B75;">Stock Mate</h1>',
    unsafe_allow_html=True
)

with st.form("login_form", clear_on_submit=False):
    uid = st.text_input("사번번호")
    pw  = st.text_input("비밀번호", type="password")
    login_clicked = st.form_submit_button("로그인", use_container_width=True)

if login_clicked:
    if not uid or not pw:
        st.warning("아이디와 비밀번호를 모두 입력하세요.")
    else:
        st.session_state["user"] = uid
        st.session_state.logged_in = True
        st.success("로그인 성공!")
        st.switch_page(DEST_MAIN)
        st.stop()
