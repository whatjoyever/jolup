import streamlit as st

# 페이지 레이아웃을 'wide'로 설정하여 전체 너비를 사용하게 합니다.
# 이 코드는 스크립트에서 st 요소들을 사용하기 전에 가장 먼저 호출되어야 합니다.
st.set_page_config(layout="wide")

# Streamlit의 기본 여백(padding)을 제거하기 위한 CSS를 주입합니다.
st.markdown("""
<style>
    /* 메인 콘텐츠 영역의 최대 너비 제한을 해제하고 여백을 제거합니다 */
    .main .block-container {
        max-width: 100%;
        padding-top: 1rem;
        padding-right: 1rem;
        padding-left: 1rem;
        padding-bottom: 1rem;
    }
    /* 사이드바가 있는 경우 등의 추가 여백을 제거합니다 */
    div[data-testid="stHorizontalBlock"] {
        padding-left: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# --- 페이지 콘텐츠 ---

# 출고관리 페이지
st.title("출고관리")
st.write("상품 출고 내역을 등록하고 조회하는 화면을 여기에 구성할 수 있습니다.")

# 여기에 출고관리 기능들을 추가하세요
# 예: 출고 등록, 출고 내역 조회, 출고 수정/삭제 등

if st.button("메인으로 돌아가기"):
    st.switch_page("main.py")
