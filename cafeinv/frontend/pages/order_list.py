import os, sys
import streamlit as st
from datetime import datetime, date, timedelta
import pandas as pd

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
        max-width: 900px;
        padding-top: 1rem;
        padding-right: 1.5rem;
        padding-left: 1.5rem;
        padding-bottom: 1rem;
    }
    div[data-testid="stHorizontalBlock"] { padding-left: 0.5rem; }
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
# -----------------------
# 검색 섹션 (Form 형태)
st.markdown("### 🔍 검색")

# 검색어 초기화 (세션 상태에 없으면)
if "order_list_search_term" not in st.session_state:
    st.session_state.order_list_search_term = ""
if "order_list_date_from" not in st.session_state:
    st.session_state.order_list_date_from = None
if "order_list_date_to" not in st.session_state:
    st.session_state.order_list_date_to = None

# 빠른 기간 선택에 따른 날짜 계산 함수
def calculate_quick_period_dates(quick_period):
    """빠른 기간 선택에 따라 시작일과 종료일을 계산"""
    if quick_period == "전체":
        return None, None
    
    today = datetime.now().date()
    
    if quick_period == "오늘":
        return today, today
    elif quick_period == "이번 주":
        # 이번 주 월요일
        days_since_monday = today.weekday()
        date_from = today - timedelta(days=days_since_monday)
        return date_from, today
    elif quick_period == "이번 달":
        date_from = today.replace(day=1)
        return date_from, today
    elif quick_period == "지난 달":
        # 지난 달 첫째 날
        first_day_this_month = today.replace(day=1)
        last_day_last_month = first_day_this_month - timedelta(days=1)
        date_from = last_day_last_month.replace(day=1)
        return date_from, last_day_last_month
    elif quick_period == "최근 7일":
        date_from = today - timedelta(days=6)
        return date_from, today
    elif quick_period == "최근 30일":
        date_from = today - timedelta(days=29)
        return date_from, today
    return None, None

# 빠른 기간 선택 상태 초기화
if "order_list_quick_period" not in st.session_state:
    st.session_state.order_list_quick_period = "전체"

# 빠른 기간 선택 (form 밖에 배치)
st.markdown("#### 📅 기간별 조회")
quick_col1, quick_col2 = st.columns([3, 1])
with quick_col1:
    st.caption("빠른 기간 선택")
    quick_period = st.selectbox(
        "기간 선택",
        options=["전체", "오늘", "이번 주", "이번 달", "지난 달", "최근 7일", "최근 30일"],
        index=["전체", "오늘", "이번 주", "이번 달", "지난 달", "최근 7일", "최근 30일"].index(
            st.session_state.order_list_quick_period
        ),
        key="order_list_quick_period_select",
        label_visibility="collapsed"
    )
    
    # 빠른 선택이 변경되면 날짜 자동 계산
    if quick_period != st.session_state.order_list_quick_period:
        st.session_state.order_list_quick_period = quick_period
        if quick_period != "전체":
            quick_date_from, quick_date_to = calculate_quick_period_dates(quick_period)
            st.session_state.order_list_date_from = quick_date_from
            st.session_state.order_list_date_to = quick_date_to
        else:
            st.session_state.order_list_date_from = None
            st.session_state.order_list_date_to = None
        st.rerun()

# 빠른 선택에 따른 날짜 계산
if st.session_state.order_list_quick_period != "전체":
    quick_date_from, quick_date_to = calculate_quick_period_dates(st.session_state.order_list_quick_period)
else:
    quick_date_from, quick_date_to = None, None

# 기본 날짜 값 설정 (세션 상태 우선, 없으면 빠른 선택 날짜)
default_date_from = st.session_state.order_list_date_from if st.session_state.order_list_date_from else quick_date_from
default_date_to = st.session_state.order_list_date_to if st.session_state.order_list_date_to else quick_date_to

with st.form("order_list_search_form", clear_on_submit=False):
    # 수동 날짜 입력
    date_col1, date_col2 = st.columns([1, 1])
    with date_col1:
        st.caption("시작일 (수동 입력)")
        date_from = st.date_input(
            "시작일", 
            value=default_date_from,
            key="order_list_date_from_input", 
            label_visibility="collapsed"
        )
    with date_col2:
        st.caption("종료일 (수동 입력)")
        date_to = st.date_input(
            "종료일", 
            value=default_date_to,
            key="order_list_date_to_input", 
            label_visibility="collapsed"
        )
    
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    
    # 키워드 검색
    st.markdown("#### 🔎 키워드 검색")
    st.caption("품목명, 카테고리명, 거래처명으로 검색 가능")
    search_query = st.text_input("검색", key="order_list_search",
                                 label_visibility="collapsed", 
                                 placeholder="품목명, 카테고리명, 거래처명 입력",
                                 value=st.session_state.order_list_search_term)
    
    search_col1, search_col2 = st.columns([1, 1])
    with search_col1:
        search_submitted = st.form_submit_button("검색", use_container_width=True, type="primary")
    with search_col2:
        reset_submitted = st.form_submit_button("초기화", use_container_width=True, type="secondary")
    
    # 검색 실행
    if search_submitted:
        st.session_state.order_list_search_term = search_query.strip() if search_query else ""
        
        # 빠른 선택이 "전체"가 아니면 빠른 선택 날짜 사용, 아니면 수동 입력한 날짜 사용
        if st.session_state.order_list_quick_period != "전체":
            quick_date_from, quick_date_to = calculate_quick_period_dates(st.session_state.order_list_quick_period)
            st.session_state.order_list_date_from = quick_date_from
            st.session_state.order_list_date_to = quick_date_to
        else:
            st.session_state.order_list_date_from = date_from if date_from else None
            st.session_state.order_list_date_to = date_to if date_to else None
    
    # 초기화 실행
    if reset_submitted:
        st.session_state.order_list_search_term = ""
        st.session_state.order_list_date_from = None
        st.session_state.order_list_date_to = None
        st.session_state.order_list_quick_period = "전체"
        st.rerun()

# 필터링 로직
filtered_receives = list(st.session_state.receives)

# 키워드 검색 필터링
if st.session_state.order_list_search_term:
    search_lower = st.session_state.order_list_search_term.lower().strip()
    filtered_receives = [
        r for r in filtered_receives 
        if (search_lower in r.get("product_name", "").lower() or
            search_lower in r.get("category", "").lower() or
            search_lower in (r.get("partner", {}).get("name", "") if r.get("partner") else "").lower())
    ]

# 기간 검색 필터링
if st.session_state.order_list_date_from and st.session_state.order_list_date_to:
    date_from = st.session_state.order_list_date_from
    date_to = st.session_state.order_list_date_to
    
    if date_from > date_to:
        st.warning("⚠️ 시작일이 종료일보다 늦습니다. 올바른 기간을 선택해주세요.")
    else:
        period_filtered = []
        for r in filtered_receives:
            try:
                order_date_str = r.get("date", "")
                if order_date_str:
                    order_date = datetime.strptime(order_date_str, "%Y-%m-%d").date()
                    if date_from <= order_date <= date_to:
                        period_filtered.append(r)
            except:
                # 날짜 형식이 잘못된 경우 해당 항목 제외
                continue
        filtered_receives = period_filtered
        
        # 기간 필터가 적용되었을 때 정보 표시
        st.info(f"📅 기간: {date_from.strftime('%Y-%m-%d')} ~ {date_to.strftime('%Y-%m-%d')} ({len(filtered_receives)}건)")
elif st.session_state.order_list_date_from or st.session_state.order_list_date_to:
    st.warning("⚠️ 시작일과 종료일을 모두 선택해주세요.")

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
        if st.session_state.order_list_search_term:
            st.write(f"검색 결과: {len(filtered_receives)}개")

        if not st.session_state.receive_edit_mode:
            # 읽기 모드: 표 형식으로 표시
            orders_data = []
            for idx, receive in enumerate(filtered_receives, start=1):
                partner_name = receive.get("partner", {}).get("name", "-") if receive.get("partner") else "-"
                total_price = receive["quantity"] * receive["price"]
                note_text = receive.get("note", "").strip() if receive.get("note") else "-"
                
                orders_data.append({
                    "번호": str(idx),
                    "품목코드": receive.get("product_code", "-"),
                    "품목명": receive.get("product_name", "-"),
                    "카테고리": receive.get("category", "-"),
                    "거래처": partner_name,
                    "발주일": receive.get("date", "-"),
                    "납기일": receive.get("delivery_date", "-"),
                    "수량": str(receive.get("quantity", 0)),
                    "단가": f"{receive.get('price', 0):,}원",
                    "총 금액": f"{total_price:,}원",
                    "비고": note_text[:20] + "..." if len(note_text) > 20 else note_text
                })
            
            if orders_data:
                df_orders = pd.DataFrame(orders_data)
                st.dataframe(
                    df_orders,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "번호": st.column_config.TextColumn("번호", width="small"),
                        "품목코드": st.column_config.TextColumn("품목코드", width="small"),
                        "품목명": st.column_config.TextColumn("품목명", width="small"),
                        "카테고리": st.column_config.TextColumn("카테고리", width="small"),
                        "거래처": st.column_config.TextColumn("거래처", width="small"),
                        "발주일": st.column_config.TextColumn("발주일", width="small"),
                        "납기일": st.column_config.TextColumn("납기일", width="small"),
                        "수량": st.column_config.TextColumn("수량", width="small"),
                        "단가": st.column_config.TextColumn("단가", width="medium"),
                        "총 금액": st.column_config.TextColumn("총 금액", width="medium"),
                        "비고": st.column_config.TextColumn("비고", width="medium")
                    }
                )
        else:
            # 수정 모드: 기존 방식 (체크박스 포함)
            h1, h2, h3, h4, h5, h6, h7, h8, h9, h10, h11 = st.columns([0.8, 1.5, 2, 1.5, 1.2, 1.2, 1.2, 1.5, 1.5, 1.2, 1.5])
            with h1: st.write("**선택**")
            with h2: st.write("**품목코드**")
            with h3: st.write("**품목명**")
            with h4: st.write("**카테고리**")
            with h5: st.write("**거래처**")
            with h6: st.write("**발주일**")
            with h7: st.write("**납기일**")
            with h8: st.write("**수량**")
            with h9: st.write("**단가**")
            with h10: st.write("**금액**")
            with h11: st.write("**비고**")

            for filtered_idx, receive in enumerate(filtered_receives):
                original_idx = next(i for i, r in enumerate(st.session_state.receives) if r == receive)
                c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11 = st.columns([0.8, 1.5, 2, 1.5, 1.2, 1.2, 1.2, 1.5, 1.5, 1.2, 1.5])
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
                    st.text_input("납기일", value=receive.get("delivery_date", ""), key=f"order_list_delivery_date_{original_idx}", disabled=True, label_visibility="collapsed")
                with c8: 
                    st.text_input("수량", value=str(receive["quantity"]), key=f"order_list_qty_{original_idx}", disabled=True, label_visibility="collapsed")
                with c9: 
                    st.text_input("단가", value=f"{receive['price']:,}", key=f"order_list_price_{original_idx}", disabled=True, label_visibility="collapsed")
                with c10:
                    total_price = receive["quantity"] * receive["price"]
                    st.text_input("총 금액", value=f"{total_price:,}", key=f"order_list_total_{original_idx}", disabled=True, label_visibility="collapsed")
                with c11:
                    if receive.get("note", "").strip():
                        with st.popover("비고 확인", use_container_width=True):
                            st.write(f"**비고:** {receive['note']}")
                    else:
                        st.write("-")