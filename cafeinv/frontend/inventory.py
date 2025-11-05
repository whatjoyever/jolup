import streamlit as st

st.set_page_config(layout="wide")

#Streamlit의 기본 여백(padding)을 제거하기 위한 CSS를 주입합니다.
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



# 재고현황 페이지
st.title("재고현황")
st.write("현재 창고의 재고 현황을 파악하는 화면을 여기에 구성할 수 있습니다.")

# 여기에 재고현황 기능들을 추가하세요
# 예: 재고 조회, 재고 분석, 재고 알림 등

if st.button("메인으로 돌아가기"):
    st.switch_page("main.py")
    # st.switch_page("main.py") 
    st.write("메인 페이지로 이동합니다.") # 예시 동작
