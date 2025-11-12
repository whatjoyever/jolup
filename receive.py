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
    /* 비고 확인 버튼 핑크색 스타일 */
    div[data-testid="stPopover"] button {
        background-color: #ff69b4 !important;
        color: white !important;
        border: none !important;
    }
    div[data-testid="stPopover"] button:hover {
        background-color: #ff1493 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 페이지 콘텐츠 ---

# 입고관리 제목과 메인으로 돌아가기 버튼
title_col, button_col = st.columns([4, 1])
with title_col:
    st.title("입고관리")
    st.write("상품 입고 내역을 등록하고 조회하는 화면을 여기에 구성할 수 있습니다.")
with button_col:
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
    if st.button("HOME🏠", use_container_width=True):
        st.switch_page("main.py")

# 세션 상태 초기화
if "products" not in st.session_state:
    st.session_state.products = []
if "receives" not in st.session_state:
    st.session_state.receives = []
if "receive_selected" not in st.session_state:
    st.session_state.receive_selected = set()
if "receive_edit_mode" not in st.session_state:
    st.session_state.receive_edit_mode = False
if "received_items" not in st.session_state:
    st.session_state.received_items = []  # 입고 완료된 항목들
if "staff_list" not in st.session_state:
    st.session_state.staff_list = ["김철수", "이영희", "박민수", "정수진"]

# 탭 생성
order_tab, receive_tab = st.tabs(["발주 관리", "입고 확인"])

with order_tab:
    # 발주 등록 폼
    st.subheader("발주 등록")

    # 세션 상태 초기화 (검색 결과 저장용)
    if "receive_search_results" not in st.session_state:
        st.session_state.receive_search_results = []
    if "receive_selected_product" not in st.session_state:
        st.session_state.receive_selected_product = None

    # 품목 검색
    search_col1, search_col2 = st.columns([2, 1])
    with search_col1:
        st.caption("품목 검색")
        product_search = st.text_input("품목 검색", key="receive_product_search", label_visibility="collapsed", placeholder="품목명 입력")
    with search_col2:
        st.markdown("<div style='height: 37px'></div>", unsafe_allow_html=True)
        if st.button("검색", key="receive_search_btn", use_container_width=True):
            # 검색 실행
            if product_search:
                st.session_state.receive_search_results = [p for p in st.session_state.products if product_search.lower() in p.get("name", "").lower()]
            else:
                st.session_state.receive_search_results = st.session_state.products

    # 검색어가 변경되면 자동으로 검색 결과 업데이트
    if product_search:
        st.session_state.receive_search_results = [p for p in st.session_state.products if product_search.lower() in p.get("name", "").lower()]
    elif not product_search and len(st.session_state.products) > 0:
        # 검색어가 없으면 모든 품목 표시
        st.session_state.receive_search_results = st.session_state.products

    # 검색 결과 표시
    if len(st.session_state.products) == 0:
        st.warning("등록된 품목이 없습니다. 기본정보 페이지에서 품목을 먼저 등록하세요.")
    elif st.session_state.receive_search_results:
        st.caption("검색 결과")
        product_options = [f"{p['name']} ({p['code']})" for p in st.session_state.receive_search_results]
        selected_option = st.selectbox(
            "품목 선택",
            options=product_options,
            key="receive_product_select",
            label_visibility="collapsed",
        )
        # 선택된 품목 정보 저장
        selected_idx = product_options.index(selected_option)
        st.session_state.receive_selected_product = st.session_state.receive_search_results[selected_idx]
        
        # 선택된 품목 정보 표시
        st.info(f"선택된 품목: {st.session_state.receive_selected_product['name']} ({st.session_state.receive_selected_product['code']})")
    else:
        st.warning("검색 결과가 없습니다.")

    with st.form("receive_form", clear_on_submit=True):
        
        # 발주 정보 입력
        r2c1, r2c2, r2c3 = st.columns([1, 1, 1])
        with r2c1:
            st.caption("발주 수량")
            receive_qty = st.number_input("발주 수량", min_value=1, step=1, value=1, key="receive_qty_input", label_visibility="collapsed")
        with r2c2:
            st.caption("발주 단가")
            # 선택된 품목의 입고 단가를 기본값으로 설정
            default_price = st.session_state.receive_selected_product.get("price", 0) if st.session_state.receive_selected_product else 0
            default_price_str = f"{default_price:,}" if default_price > 0 else ""
            receive_price_input = st.text_input("발주 단가", value=default_price_str, key="receive_price_input", label_visibility="collapsed", placeholder="100000")
            
            # 입력값 처리 (쉼표 제거하고 숫자만 추출)
            if receive_price_input:
                receive_price_clean = receive_price_input.replace(",", "")
                receive_price_clean = ''.join(filter(str.isdigit, receive_price_clean))
                if receive_price_clean:
                    receive_price = int(receive_price_clean)
                    receive_price_formatted = f"{receive_price:,}"
                    st.caption(f"입력값: {receive_price_formatted}원")
                else:
                    receive_price = 0
            else:
                receive_price = 0
        with r2c3:
            st.caption("발주일")
            receive_date = st.date_input("발주일", key="receive_date_input", label_visibility="collapsed")
        
        r3c1, r3c2 = st.columns([2, 1])
        with r3c1:
            st.caption("비고")
            receive_note = st.text_input("비고", key="receive_note_input", label_visibility="collapsed", placeholder="입고 관련 메모")
        with r3c2:
            st.markdown("<div style='height: 37px'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button("등록", use_container_width=True)
        
        if submitted:
            if st.session_state.receive_selected_product is None:
                st.warning("품목을 선택하세요.")
            else:
                # 발주 내역 저장
                st.session_state.receives.append({
                    "product_code": st.session_state.receive_selected_product["code"],
                    "product_name": st.session_state.receive_selected_product["name"],
                    "category": st.session_state.receive_selected_product.get("category", ""),
                    "unit": st.session_state.receive_selected_product.get("unit", ""),
                    "quantity": receive_qty,
                    "price": receive_price,
                    "date": str(receive_date),
                    "note": receive_note,
                    "is_received": False
                })
                st.success("발주 내역이 등록되었습니다.")
                # 검색 결과 초기화
                st.session_state.receive_search_results = []
                st.session_state.receive_selected_product = None
                st.rerun()

    st.markdown("---")

    # 발주 내역 검색 기능
    search_row1, search_row2, search_row3 = st.columns([1, 1, 1])
    with search_row1:
        st.caption("품목명으로 검색")
        receive_product_search = st.text_input("품목명으로 검색", key="receive_history_product_search", label_visibility="collapsed", placeholder="품목명 입력")
    with search_row2:
        st.caption("카테고리로 검색")
        receive_category_search = st.text_input("카테고리로 검색", key="receive_history_category_search", label_visibility="collapsed", placeholder="카테고리명 입력")
    with search_row3:
        st.caption("발주일로 검색")
        receive_date_search = st.text_input("발주일로 검색", key="receive_history_date_search", label_visibility="collapsed", placeholder="2024-01-01")

    # 발주 내역 필터링
    filtered_receives = st.session_state.receives
    if receive_product_search:
        filtered_receives = [r for r in filtered_receives if receive_product_search.lower() in r.get("product_name", "").lower()]
    if receive_category_search:
        filtered_receives = [r for r in filtered_receives if receive_category_search.lower() in r.get("category", "").lower()]
    if receive_date_search:
        filtered_receives = [r for r in filtered_receives if receive_date_search in r.get("date", "")]

    # form 타입으로 발주 내역 목록
    with st.form("receive_list_form"):
        # 제목과 버튼을 같은 줄에 배치
        if st.session_state.receive_edit_mode:
            # 수정 모드: 제목 + 선택 취소, 전체 취소 버튼
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
            # 일반 모드: 제목 + 수정 버튼
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
            # submit 버튼 (에러 방지용)
            st.form_submit_button("", use_container_width=True, help="")
        elif len(filtered_receives) == 0:
            st.warning("검색 결과가 없습니다")
            # submit 버튼 (에러 방지용)
            st.form_submit_button("", use_container_width=True, help="")
        else:
            # 검색 결과 개수 표시
            if receive_product_search or receive_category_search or receive_date_search:
                st.write(f"검색 결과: {len(filtered_receives)}개")
            # 헤더
            h1, h2, h3, h4, h5, h6, h7, h8, h9 = st.columns([0.8, 1.5, 2, 1.5, 1.2, 1.5, 1.5, 1.2, 1.5])
            with h1:
                st.write("**선택**")
            with h2:
                st.write("**품목코드**")
            with h3:
                st.write("**품목명**")
            with h4:
                st.write("**카테고리**")
            with h5:
                st.write("**발주일**")
            with h6:
                st.write("**수량**")
            with h7:
                st.write("**단가**")
            with h8:
                st.write("**금액**")
            with h9:
                st.write("**비고**")
            
            # 발주 내역 표시
            for filtered_idx, receive in enumerate(filtered_receives):
                # 원본 리스트에서의 실제 인덱스 찾기
                original_idx = next(i for i, r in enumerate(st.session_state.receives) if r == receive)
                c1, c2, c3, c4, c5, c6, c7, c8, c9 = st.columns([0.8, 1.5, 2, 1.5, 1.2, 1.5, 1.5, 1.2, 1.5])
                with c1:
                    # 체크박스의 현재 상태 확인
                    is_checked = original_idx in st.session_state.receive_selected
                    checked = st.checkbox("", value=is_checked, key=f"receive_sel_{original_idx}")
                    if checked:
                        st.session_state.receive_selected.add(original_idx)
                    else:
                        st.session_state.receive_selected.discard(original_idx)
                with c2:
                    st.text_input("품목코드", value=receive["product_code"], key=f"receive_code_{original_idx}", disabled=True, label_visibility="collapsed")
                with c3:
                    st.text_input("품목명", value=receive["product_name"], key=f"receive_name_{original_idx}", disabled=True, label_visibility="collapsed")
                with c4:
                    st.text_input("카테고리", value=receive["category"], key=f"receive_category_{original_idx}", disabled=True, label_visibility="collapsed")
                with c5:
                    st.text_input("발주일", value=receive.get("date", ""), key=f"receive_date_{original_idx}", disabled=True, label_visibility="collapsed")
                with c6:
                    st.text_input("수량", value=str(receive["quantity"]), key=f"receive_qty_{original_idx}", disabled=True, label_visibility="collapsed")
                with c7:
                    price_text = f"{receive['price']:,}"
                    st.text_input("단가", value=price_text, key=f"receive_price_{original_idx}", disabled=True, label_visibility="collapsed")
                with c8:
                    total_price = receive["quantity"] * receive["price"]
                    total_text = f"{total_price:,}"
                    st.text_input("총 금액", value=total_text, key=f"receive_total_{original_idx}", disabled=True, label_visibility="collapsed")
                with c9:
                    # 비고가 있으면 버튼 표시, 없으면 "-" 표시
                    if receive.get("note", "").strip():
                        with st.popover("📝 비고 확인", use_container_width=True):
                            st.write(f"**비고:** {receive['note']}")
                    else:
                        st.write("-")

with receive_tab:
    st.subheader("입고 등록")
    
    # 미입고 발주 목록 가져오기
    unreceived_orders = [r for r in st.session_state.receives if r.get("is_received", False) == False]
    
    if len(unreceived_orders) == 0:
        st.warning("입고 처리가 필요한 발주가 없습니다.")
    else:
        # 발주 선택
        st.caption("발주 선택")
        order_options = [f"{r['product_name']} ({r['product_code']}) - 발주수량: {r['quantity']}개" for r in unreceived_orders]
        selected_order_idx = st.selectbox(
            "발주 건 선택",
            options=range(len(order_options)),
            format_func=lambda x: order_options[x],
            key="receive_order_select",
            label_visibility="collapsed"
        )
        
        if selected_order_idx is not None:
            selected_order = unreceived_orders[selected_order_idx]
            
            # 선택된 발주 정보 표시
            st.info(f"선택된 발주: {selected_order['product_name']} ({selected_order['product_code']}) - 발주수량: {selected_order['quantity']}개")
            
            # 입고 정보 입력 폼
            with st.form("receive_confirm_form", clear_on_submit=True):
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.caption("발주 수량")
                    st.text_input("발주 수량", value=f"{selected_order['quantity']}개", key="order_qty_display", disabled=True, label_visibility="collapsed")
                    
                    st.caption("실제 입고 수량")
                    actual_qty = st.number_input("실제 입고 수량", min_value=0, step=1, value=selected_order['quantity'], key="actual_qty_input", label_visibility="collapsed")
                    
                    st.caption("발주 단가")
                    st.text_input("발주 단가", value=f"{selected_order['price']:,}원", key="order_price_display", disabled=True, label_visibility="collapsed")
                    
                    st.caption("실제 입고 단가")
                    actual_price = st.number_input("실제 입고 단가", min_value=0, step=100, value=selected_order['price'], key="actual_price_input", label_visibility="collapsed")
                
                with col2:
                    st.caption("입고일")
                    receive_date = st.date_input("입고일", key="receive_confirm_date_input", label_visibility="collapsed")
                    
                    st.caption("유통기한")
                    receive_expiry = st.date_input("유통기한", key="receive_expiry_input", label_visibility="collapsed")
                    
                    st.caption("담당자")
                    staff_name = st.selectbox(
                        "담당자",
                        options=st.session_state.staff_list,
                        key="staff_select",
                        label_visibility="collapsed"
                    )
                    
                    st.caption("특이사항")
                    special_note = st.text_area("특이사항", key="special_note_input", label_visibility="collapsed", placeholder="포장 박스 일부 파손, 유통기한 임박 상품 포함 등", height=100)
                
                submitted = st.form_submit_button("입고 완료", use_container_width=True)
                
                if submitted:
                    if actual_qty == 0:
                        st.warning("실제 입고 수량을 입력하세요.")
                    else:
                        # 입고 완료 처리
                        received_item = {
                            "product_code": selected_order["product_code"],
                            "product_name": selected_order["product_name"],
                            "category": selected_order.get("category", ""),
                            "order_qty": selected_order['quantity'],
                            "actual_qty": actual_qty,
                            "order_price": selected_order['price'],
                            "actual_price": actual_price,
                            "receive_date": str(receive_date),
                            "expiry": str(receive_expiry),
                            "staff": staff_name,
                            "special_note": special_note
                        }
                        st.session_state.received_items.append(received_item)
                        
                        # 발주 건을 입고 완료 처리
                        for i, order in enumerate(st.session_state.receives):
                            if order == selected_order:
                                st.session_state.receives[i]["is_received"] = True
                                break
                        
                        st.success(f"입고 완료: {selected_order['product_name']} {actual_qty}개")
                        st.rerun()
    
    st.markdown("---")
    
    # 입고 내역 목록
    st.subheader("입고 내역")
    
    if len(st.session_state.received_items) == 0:
        st.warning("입고 내역이 없습니다.")
    else:
        # 입고 내역 표시
        for idx, item in enumerate(st.session_state.received_items):
            with st.expander(f"{item['product_name']} ({item['product_code']}) - {item['receive_date']}", expanded=False):
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.write(f"**품목코드:** {item['product_code']}")
                    st.write(f"**품목명:** {item['product_name']}")
                    st.write(f"**카테고리:** {item.get('category', '-')}")
                    st.write(f"**발주 수량:** {item['order_qty']}개")
                    st.write(f"**실제 입고 수량:** {item['actual_qty']}개")
                    
                    if item['order_qty'] != item['actual_qty']:
                        diff = item['actual_qty'] - item['order_qty']
                        if diff > 0:
                            st.warning(f"⚠️ 과입고: {diff}개 초과")
                        else:
                            st.warning(f"⚠️ 부족: {abs(diff)}개 부족")
                
                with col2:
                    st.write(f"**발주 단가:** {item['order_price']:,}원")
                    st.write(f"**실제 입고 단가:** {item['actual_price']:,}원")
                    
                    if item['order_price'] != item['actual_price']:
                        price_diff = item['actual_price'] - item['order_price']
                        if price_diff > 0:
                            st.warning(f"⚠️ 단가 상승: +{price_diff:,}원")
                        else:
                            st.info(f"ℹ️ 단가 하락: {price_diff:,}원")
                    
                    st.write(f"**입고일:** {item['receive_date']}")
                    st.write(f"**담당자:** {item['staff']}")
                    st.write(f"**유통기한:** {item.get('expiry', '-')}")
                    
                    if item.get('special_note'):
                        st.write(f"**특이사항:** {item['special_note']}")
