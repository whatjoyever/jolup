# file: login.py
import streamlit as st

DEST_MAIN = "pages/main.py"   # ✅ 올바른 경로로 고정

st.set_page_config(
    page_title="Stock Mate - 로그인",
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items=None,
)

# 세션 기본값
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ✅ 이미 로그인 되어 있으면 즉시 메인 페이지로 전환 (아무것도 그리지 않음)
if st.session_state.logged_in:
    st.switch_page(DEST_MAIN)   # ← 핵심
    st.stop()

# ---------- 여기부터는 로그인 화면만 ----------
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
    '<h1 style="text-align:center; font-size:72px; font-weight:800; color:#0B3B75; margin:.2em 0 .1em 0;">Stock Mate</h1>',
    unsafe_allow_html=True
)
st.markdown('<div class="deco"><span class="dot"></span><span class="line"></span><span class="dot"></span></div>',
            unsafe_allow_html=True)

with st.form("login_form", clear_on_submit=False):
    uid = st.text_input("사번번호")
    pw  = st.text_input("비밀번호", type="password")
    login_clicked = st.form_submit_button("로그인", use_container_width=True)

if login_clicked:
    if not uid or not pw:
        st.warning("아이디와 비밀번호를 모두 입력하세요.")
    else:
        # TODO: 실제 인증 로직 연결 (현재는 모두 통과)
        st.session_state["user"] = uid
        st.session_state.logged_in = True
        st.success("로그인 성공!")
        st.switch_page(DEST_MAIN)  # ✅ 성공 즉시 이동
        st.stop()
