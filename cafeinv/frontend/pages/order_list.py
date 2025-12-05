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

# 버튼 영역 (form 밖)
if st.session_state.receive_edit_mode:
    title_col, btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(
        [5, 1, 1, 1, 1]
    )
    with title_col:
        st.subheader("발주 내역")
    with btn_col1:
        st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
        if st.button("선택 취소", use_container_width=True, key="order_list_select_delete"):
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
        if st.button("전체 취소", use_container_width=True, key="order_list_all_delete"):
            st.session_state.receives = []
            st.session_state.receive_selected = set()
            st.session_state.receive_edit_mode = False
            st.success("전체 발주가 취소되었습니다.")
            st.rerun()
    with btn_col3:
        st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
        if st.button("저장", use_container_width=True, key="order_list_save"):
            st.session_state._order_list_save_clicked = True
    with btn_col4:
        st.write("")
else:
    title_col, btn_col = st.columns([5, 1])
    with title_col:
        st.subheader("발주 내역")
    with btn_col:
        st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
        if st.button("수정", use_container_width=True, key="order_list_edit"):
            st.session_state.receive_edit_mode = True
            st.rerun()

if len(st.session_state.receives) == 0:
    st.warning("등록된 발주 내역이 없습니다")
elif len(filtered_receives) == 0:
    st.warning("검색 결과가 없습니다")
else:
    if st.session_state.order_list_search_term:
        st.info(f"검색 결과: {len(filtered_receives)}개")

    # 발주 내역을 날짜 기준으로 최신순 정렬
    def get_order_date(receive):
        """발주일을 date 객체로 반환 (정렬용)"""
        try:
            date_str = receive.get("date", "")
            if date_str:
                return datetime.strptime(date_str, "%Y-%m-%d").date()
            return date.min  # 날짜가 없으면 가장 오래된 것으로 처리
        except:
            return date.min
    
    # 최신순 정렬 (날짜 내림차순)
    sorted_receives = sorted(filtered_receives, key=get_order_date, reverse=True)
    
    # 월별로 그룹화
    monthly_groups = {}
    for receive in sorted_receives:
        try:
            date_str = receive.get("date", "")
            if date_str:
                order_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                month_key = f"{order_date.year}년 {order_date.month}월"
                if month_key not in monthly_groups:
                    monthly_groups[month_key] = []
                monthly_groups[month_key].append(receive)
            else:
                # 날짜가 없는 경우 "날짜 없음" 그룹에 추가
                if "날짜 없음" not in monthly_groups:
                    monthly_groups["날짜 없음"] = []
                monthly_groups["날짜 없음"].append(receive)
        except:
            # 날짜 파싱 실패 시 "날짜 없음" 그룹에 추가
            if "날짜 없음" not in monthly_groups:
                monthly_groups["날짜 없음"] = []
            monthly_groups["날짜 없음"].append(receive)
    
    # 월별 그룹을 최신순으로 정렬 (날짜 없음은 마지막에)
    sorted_month_keys = []
    date_keys = []
    no_date_key = None
    for key in monthly_groups.keys():
        if key == "날짜 없음":
            no_date_key = key
        else:
            date_keys.append(key)
    
    # 날짜 키를 년월 기준으로 정렬 (최신순)
    def parse_month_key(key):
        try:
            year_str, month_str = key.replace("년", "").replace("월", "").split()
            return (int(year_str), int(month_str))
        except:
            return (0, 0)
    
    date_keys.sort(key=parse_month_key, reverse=True)
    sorted_month_keys = date_keys
    if no_date_key:
        sorted_month_keys.append(no_date_key)

    if not st.session_state.receive_edit_mode:
        # 읽기 모드: 월별로 구분하여 표 형식으로 표시
        all_orders_data = []
        global_idx = 1  # 전체 번호 (최신순)
        
        for month_key in sorted_month_keys:
            month_receives = monthly_groups[month_key]
            
            # 월별 헤더 표시
            st.markdown(f"### 📅 {month_key} 발주 내역 ({len(month_receives)}건)")
            
            orders_data = []
            for receive in month_receives:
                partner_name = receive.get("partner", {}).get("name", "-") if receive.get("partner") else "-"
                total_price = receive["quantity"] * receive["price"]
                note_text = receive.get("note", "").strip() if receive.get("note") else "-"
                
                orders_data.append({
                    "번호": str(global_idx),
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
                global_idx += 1
            
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
            
            st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
    else:
        # 수정 모드: 월별로 구분하여 표 형식으로 편집 가능하게
        all_edited_dfs = []  # 모든 월별 edited_df 저장
        global_idx = 1  # 전체 번호 (최신순)
        
        for month_idx, month_key in enumerate(sorted_month_keys):
            month_receives = monthly_groups[month_key]
            
            # 월별 헤더 표시
            st.markdown(f"### 📅 {month_key} 발주 내역 ({len(month_receives)}건)")
            
            orders_data = []
            for receive in month_receives:
                # 원본 인덱스 찾기
                original_idx = next(
                    (
                        i
                        for i, r in enumerate(st.session_state.receives)
                        if r == receive
                    ),
                    None,
                )
                if original_idx is None:
                    continue
                
                # 체크박스 상태 확인
                is_checked = original_idx in st.session_state.receive_selected
                
                partner_name = receive.get("partner", {}).get("name", "-") if receive.get("partner") else "-"
                total_price = receive["quantity"] * receive["price"]
                note_text = receive.get("note", "").strip() if receive.get("note") else ""
                
                # 날짜 문자열을 datetime으로 변환 (편집을 위해)
                try:
                    order_date = datetime.strptime(receive.get("date", ""), "%Y-%m-%d").date() if receive.get("date") else None
                except:
                    order_date = None
                
                try:
                    delivery_date = datetime.strptime(receive.get("delivery_date", ""), "%Y-%m-%d").date() if receive.get("delivery_date") else None
                except:
                    delivery_date = None
                
                orders_data.append({
                    "선택": is_checked,
                    "번호": str(global_idx),
                    "품목코드": receive.get("product_code", "-"),
                    "품목명": receive.get("product_name", "-"),
                    "카테고리": receive.get("category", "-"),
                    "거래처": partner_name,
                    "발주일": order_date,
                    "납기일": delivery_date,
                    "수량": int(receive.get("quantity", 0)),
                    "단가": int(receive.get("price", 0)),
                    "총 금액": total_price,  # 자동 계산용 (표시만)
                    "비고": note_text,
                    "_original_idx": original_idx  # 원본 인덱스 저장용 (표시 안 함)
                })
                global_idx += 1
            
            if orders_data:
                df_orders = pd.DataFrame(orders_data)
                
                # 편집 가능한 표 (각 월별로 고유한 key 사용)
                edited_df = st.data_editor(
                    df_orders,
                    use_container_width=True,
                    hide_index=True,
                    key=f"order_list_data_editor_{month_idx}",
                    column_config={
                        "선택": st.column_config.CheckboxColumn("선택", width="small"),
                        "번호": st.column_config.TextColumn("번호", width="small", disabled=True),
                        "품목코드": st.column_config.TextColumn("품목코드", width="small", disabled=True),
                        "품목명": st.column_config.TextColumn("품목명", width="small", disabled=True),
                        "카테고리": st.column_config.TextColumn("카테고리", width="small", disabled=True),
                        "거래처": st.column_config.TextColumn("거래처", width="small", disabled=True),
                        "발주일": st.column_config.DateColumn("발주일", width="small", format="YYYY-MM-DD"),
                        "납기일": st.column_config.DateColumn("납기일", width="small", format="YYYY-MM-DD"),
                        "수량": st.column_config.NumberColumn("수량", width="small", min_value=1),
                        "단가": st.column_config.NumberColumn("단가", width="medium", min_value=0),
                        "총 금액": st.column_config.NumberColumn("총 금액", width="medium", disabled=True),
                        "비고": st.column_config.TextColumn("비고", width="medium"),
                        "_original_idx": st.column_config.NumberColumn("_original_idx", width="small", disabled=True)
                    },
                    num_rows="dynamic"
                )
                
                # 체크박스 상태 업데이트
                for _, row in edited_df.iterrows():
                    original_idx = int(row["_original_idx"])
                    if row["선택"]:
                        st.session_state.receive_selected.add(original_idx)
                    else:
                        st.session_state.receive_selected.discard(original_idx)
                
                # 총 금액 자동 계산 및 업데이트
                for idx, row in edited_df.iterrows():
                    qty = int(row["수량"]) if pd.notna(row["수량"]) else 0
                    price = int(row["단가"]) if pd.notna(row["단가"]) else 0
                    total = qty * price
                    edited_df.at[idx, "총 금액"] = total
                
                # 모든 월별 데이터를 하나의 리스트에 모음
                all_edited_dfs.append(edited_df)
            
            st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
        
        # 저장 버튼이 클릭되었을 때 처리 (모든 월별 데이터 처리)
        if st.session_state.get("_order_list_save_clicked", False):
            st.session_state._order_list_save_clicked = False  # 플래그 리셋
            has_error = False
            
            # 모든 월별 데이터프레임을 순회하며 저장
            for edited_df in all_edited_dfs:
                # st.data_editor의 최신 반환값 직접 사용 (편집된 내용 반영)
                for _, row in edited_df.iterrows():
                    original_idx = int(row["_original_idx"])
                    if 0 <= original_idx < len(st.session_state.receives):
                        # 날짜 처리
                        order_date = row["발주일"]
                        if pd.notna(order_date):
                            if isinstance(order_date, str):
                                order_date_str = order_date
                            else:
                                order_date_str = order_date.strftime("%Y-%m-%d")
                        else:
                            order_date_str = ""
                        
                        delivery_date = row["납기일"]
                        if pd.notna(delivery_date):
                            if isinstance(delivery_date, str):
                                delivery_date_str = delivery_date
                            else:
                                delivery_date_str = delivery_date.strftime("%Y-%m-%d")
                        else:
                            delivery_date_str = ""
                        
                        # 수량과 단가 처리
                        qty = int(row["수량"]) if pd.notna(row["수량"]) else 0
                        price = int(row["단가"]) if pd.notna(row["단가"]) else 0
                        note = str(row["비고"]).strip() if pd.notna(row["비고"]) else ""
                        
                        # 유효성 검사
                        if qty <= 0:
                            st.error("수량은 1 이상이어야 합니다.")
                            has_error = True
                            break
                        if price < 0:
                            st.error("단가는 0 이상이어야 합니다.")
                            has_error = True
                            break
                        
                        # 발주 내역 업데이트
                        st.session_state.receives[original_idx]["date"] = order_date_str
                        st.session_state.receives[original_idx]["delivery_date"] = delivery_date_str
                        st.session_state.receives[original_idx]["quantity"] = qty
                        st.session_state.receives[original_idx]["price"] = price
                        st.session_state.receives[original_idx]["note"] = note
                
                if not has_error:
                    st.session_state.receive_edit_mode = False
                    st.success("저장되었습니다.")
                    st.rerun()