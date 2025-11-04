import os, sys
import streamlit as st
from datetime import datetime
import calendar
from collections import defaultdict

# --- sidebar import 경로 보정 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

from sidebar import render_sidebar
from client import api_get, api_post

# -------------------------------
# 페이지 설정 & 커스텀 사이드바
# -------------------------------
st.set_page_config(page_title="발주 목록", page_icon="📋", layout="wide")
render_sidebar("receive")

# 기본 여백/스타일
st.markdown("""
<style>
    .main .block-container {
        max-width: 100%;
        padding-top: 1rem;
        padding-right: 4rem;
        padding-left: 4rem;
        padding-bottom: 1rem;
    }
    div[data-testid="stHorizontalBlock"] { padding-left: 1rem; }
</style>
""", unsafe_allow_html=True)

# -------------------------------
# 세션 상태 초기화
# -------------------------------
if "receives" not in st.session_state:
    st.session_state.receives = []
if "receive_selected" not in st.session_state:
    st.session_state.receive_selected = set()
if "receive_edit_mode" not in st.session_state:
    st.session_state.receive_edit_mode = False

# -------------------------------
# 헤더 & 뒤로가기 버튼
# -------------------------------
title_col, button_col = st.columns([4, 1])
with title_col:
    st.title("발주 목록")
with button_col:
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
    if st.button("← 뒤로가기", use_container_width=True, key="back_button"):
        st.switch_page("pages/receive.py")

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# -------------------------------
# 발주 내역 검색
# -------------------------------
st.subheader("발주 내역 검색")

# 통합 검색창
st.caption("품목명, 카테고리명, 발주일로 검색")
search_query = st.text_input("검색", key="order_list_search",
                             label_visibility="collapsed", 
                             placeholder="품목명, 카테고리명, 또는 발주일(YYYY-MM-DD) 입력")

# 통합 검색 필터링 (품목명, 카테고리명, 발주일 중 하나라도 매칭되면 표시)
filtered_receives = list(st.session_state.receives)
if search_query:
    search_lower = search_query.lower().strip()
    filtered_receives = [
        r for r in filtered_receives 
        if (search_lower in r.get("product_name", "").lower() or
            search_lower in r.get("category", "").lower() or
            search_query in r.get("date", ""))
    ]

st.markdown("---")

# -------------------------------
# 발주 내역 캘린더
# -------------------------------
st.subheader("발주 내역 캘린더")

# 월/년 선택
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    current_year = datetime.now().year
    selected_year = st.selectbox("년도", options=range(current_year - 2, current_year + 3), 
                                 index=2, key="order_list_calendar_year")
with col2:
    selected_month = st.selectbox("월", options=range(1, 13), 
                                 index=datetime.now().month - 1, key="order_list_calendar_month")

# 날짜별 발주 내역 그룹화
date_orders = defaultdict(list)
for order in st.session_state.receives:
    try:
        order_date = datetime.strptime(order.get("date", ""), "%Y-%m-%d").date()
        if order_date.year == selected_year and order_date.month == selected_month:
            date_orders[order_date.day].append(order)
    except:
        pass

# 선택된 날짜 (세션 상태)
if "order_list_selected_calendar_date" not in st.session_state:
    st.session_state.order_list_selected_calendar_date = None
if "order_list_last_calendar_month" not in st.session_state:
    st.session_state.order_list_last_calendar_month = None

# 월이 바뀌면 선택된 날짜 초기화
current_month_key = f"{selected_year}-{selected_month}"
if st.session_state.order_list_last_calendar_month != current_month_key:
    st.session_state.order_list_selected_calendar_date = None
    st.session_state.order_list_last_calendar_month = current_month_key

# 캘린더 생성
cal = calendar.monthcalendar(selected_year, selected_month)
month_name = calendar.month_name[selected_month]

# 캘린더 스타일
calendar_css = """
<style>
.calendar-container {
    margin: 20px 0;
}
.calendar-header {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 5px;
    margin-bottom: 5px;
}
.calendar-day-header {
    text-align: center;
    font-weight: bold;
    padding: 10px;
    background-color: #f0f0f0;
    border-radius: 5px;
}
</style>
"""
st.markdown(calendar_css, unsafe_allow_html=True)

# 캘린더 헤더
weekdays = ['월', '화', '수', '목', '금', '토', '일']
header_html = '<div class="calendar-header">'
for day in weekdays:
    header_html += f'<div class="calendar-day-header">{day}</div>'
header_html += '</div>'
st.markdown(header_html, unsafe_allow_html=True)

# 캘린더 날짜 그리드
st.markdown('<div class="calendar-container">', unsafe_allow_html=True)
for week in cal:
    week_cols = st.columns(7)
    for day_idx, day in enumerate(week):
        with week_cols[day_idx]:
            if day == 0:
                st.markdown('<div style="height: 60px;"></div>', unsafe_allow_html=True)
            else:
                has_orders = day in date_orders
                order_count = len(date_orders[day]) if has_orders else 0
                is_selected = st.session_state.order_list_selected_calendar_date == day
                
                button_text = f"{day}\n{order_count}건" if has_orders else str(day)
                button_key = f"order_list_cal_day_{day}_{selected_year}_{selected_month}"
                button_type = "primary" if is_selected else "secondary"
                
                if has_orders and not is_selected:
                    st.markdown(f"""
                    <div style="background-color: #e3f2fd; border: 2px solid #2196F3; border-radius: 8px; padding: 2px;">
                    """, unsafe_allow_html=True)
                
                button_clicked = st.button(
                    button_text,
                    key=button_key,
                    use_container_width=True,
                    type=button_type
                )
                
                if has_orders and not is_selected:
                    st.markdown("</div>", unsafe_allow_html=True)
                
                if button_clicked:
                    if st.session_state.order_list_selected_calendar_date == day:
                        st.session_state.order_list_selected_calendar_date = None
                    else:
                        st.session_state.order_list_selected_calendar_date = day
                    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# 선택된 날짜의 발주 내역 표시
if st.session_state.order_list_selected_calendar_date:
    selected_date_str = f"{selected_year}-{selected_month:02d}-{st.session_state.order_list_selected_calendar_date:02d}"
    st.markdown("---")
    st.markdown(f"### 📅 {selected_date_str} 발주 내역")
    
    filtered_receives = date_orders[st.session_state.order_list_selected_calendar_date]
    
    if len(filtered_receives) == 0:
        st.info(f"{selected_date_str}에 등록된 발주가 없습니다.")
    else:
        st.write(f"총 {len(filtered_receives)}건의 발주가 있습니다.")
        
        for idx, receive in enumerate(filtered_receives):
            original_idx = next(i for i, r in enumerate(st.session_state.receives) if r == receive)
            with st.expander(f"{receive['product_name']} ({receive['product_code']}) - {receive.get('quantity', 0)}개", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**품목코드:** {receive['product_code']}")
                    st.write(f"**품목명:** {receive['product_name']}")
                    st.write(f"**카테고리:** {receive.get('category', '-')}")
                    st.write(f"**수량:** {receive.get('quantity', 0)}개")
                    st.write(f"**단가:** {receive.get('price', 0):,}원")
                with col2:
                    partner_name = receive.get("partner", {}).get("name", "-") if receive.get("partner") else "-"
                    st.write(f"**거래처:** {partner_name}")
                    st.write(f"**발주일:** {receive.get('date', '-')}")
                    total_price = receive.get('quantity', 0) * receive.get('price', 0)
                    st.write(f"**총 금액:** {total_price:,}원")
                    if receive.get('note'):
                        st.write(f"**비고:** {receive.get('note', '-')}")
                    st.write(f"**입고 상태:** {'✅ 입고 완료' if receive.get('is_received', False) else '⏳ 대기 중'}")

st.markdown("---")

# 발주 내역 테이블
with st.form("order_list_form"):
    if st.session_state.receive_edit_mode:
        title_col, btn_col1, btn_col2 = st.columns([5, 1, 1])
        with title_col: 
            st.subheader("발주 내역")
        with btn_col1:
            st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
            if st.form_submit_button("선택 취소", use_container_width=True):
                if not st.session_state.receive_selected:
                    st.info("취소할 항목을 선택하세요.")
                else:
                    for i in sorted(st.session_state.receive_selected, reverse=True):
                        if 0 <= i < len(st.session_state.receives):
                            st.session_state.receives.pop(i)
                    st.session_state.receive_selected = set()
                    st.session_state.receive_edit_mode = False
                    st.success("선택한 발주가 취소되었습니다.")
                    st.rerun()
        with btn_col2:
            st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
            if st.form_submit_button("전체 취소", use_container_width=True):
                st.session_state.receives = []
                st.session_state.receive_selected = set()
                st.session_state.receive_edit_mode = False
                st.success("전체 발주가 취소되었습니다.")
                st.rerun()
    else:
        title_col, btn_col = st.columns([5, 1])
        with title_col: 
            st.subheader("발주 내역")
        with btn_col:
            st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
            if st.form_submit_button("수정", use_container_width=True):
                st.session_state.receive_edit_mode = True
                st.rerun()

    if len(st.session_state.receives) == 0:
        st.warning("등록된 발주 내역이 없습니다")
        st.form_submit_button("", use_container_width=True, help="")
    elif len(filtered_receives) == 0:
        st.warning("검색 결과가 없습니다")
        st.form_submit_button("", use_container_width=True, help="")
    else:
        if search_query:
            st.write(f"검색 결과: {len(filtered_receives)}개")

        h1, h2, h3, h4, h5, h6, h7, h8, h9, h10 = st.columns([0.8, 1.5, 2, 1.5, 1.2, 1.5, 1.5, 1.2, 1.5, 1.5])
        with h1: st.write("**선택**")
        with h2: st.write("**품목코드**")
        with h3: st.write("**품목명**")
        with h4: st.write("**카테고리**")
        with h5: st.write("**거래처**")
        with h6: st.write("**발주일**")
        with h7: st.write("**수량**")
        with h8: st.write("**단가**")
        with h9: st.write("**금액**")
        with h10: st.write("**비고**")

        for filtered_idx, receive in enumerate(filtered_receives):
            original_idx = next(i for i, r in enumerate(st.session_state.receives) if r == receive)
            c1, c2, c3, c4, c5, c6, c7, c8, c9, c10 = st.columns([0.8, 1.5, 2, 1.5, 1.2, 1.2, 1.5, 1.5, 1.2, 1.5])
            with c1:
                is_checked = original_idx in st.session_state.receive_selected
                checked = st.checkbox("", value=is_checked, key=f"order_list_sel_{original_idx}")
                if checked: 
                    st.session_state.receive_selected.add(original_idx)
                else:       
                    st.session_state.receive_selected.discard(original_idx)
            with c2: 
                st.text_input("품목코드", value=receive["product_code"], key=f"order_list_code_{original_idx}", disabled=True, label_visibility="collapsed")
            with c3: 
                st.text_input("품목명", value=receive["product_name"], key=f"order_list_name_{original_idx}", disabled=True, label_visibility="collapsed")
            with c4: 
                st.text_input("카테고리", value=receive["category"], key=f"order_list_category_{original_idx}", disabled=True, label_visibility="collapsed")
            with c5: 
                partner_name = receive.get("partner", {}).get("name", "-") if receive.get("partner") else "-"
                st.text_input("거래처", value=partner_name, key=f"order_list_partner_{original_idx}", disabled=True, label_visibility="collapsed")
            with c6: 
                st.text_input("발주일", value=receive.get("date", ""), key=f"order_list_date_{original_idx}", disabled=True, label_visibility="collapsed")
            with c7: 
                st.text_input("수량", value=str(receive["quantity"]), key=f"order_list_qty_{original_idx}", disabled=True, label_visibility="collapsed")
            with c8: 
                st.text_input("단가", value=f"{receive['price']:,}", key=f"order_list_price_{original_idx}", disabled=True, label_visibility="collapsed")
            with c9:
                total_price = receive["quantity"] * receive["price"]
                st.text_input("총 금액", value=f"{total_price:,}", key=f"order_list_total_{original_idx}", disabled=True, label_visibility="collapsed")
            with c10:
                if receive.get("note", "").strip():
                    with st.popover("비고 확인", use_container_width=True):
                        st.write(f"**비고:** {receive['note']}")
                else:
                    st.write("-")

