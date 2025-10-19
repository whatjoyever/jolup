import os, sys
import streamlit as st
from client import api_get, api_post


# --- sidebar import 경로 보정 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))  # ../frontend
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

from sidebar import render_sidebar
from client import api_get, api_post   # ✅ 올바른 import
# --------------------------------


# ===============================
# 페이지 설정 & 커스텀 사이드바
# ===============================
st.set_page_config(page_title="입고관리", page_icon="📥", layout="wide")
render_sidebar("receive")  # ✅ 기본 Pages 목록 숨기고, 우리가 만든 네비만 표시

# ===============================
# 글로벌 스타일 (기존 여백 조정 유지)
# ===============================
st.markdown("""
<style>
  .main .block-container { max-width: 100%; padding: 1rem; }
  div[data-testid="stHorizontalBlock"] { padding-left: 1rem; }
  /* 비고 확인 버튼 핑크색 스타일 */
  div[data-testid="stPopover"] button { background-color: #ff69b4 !important; color: white !important; border: none !important; }
  div[data-testid="stPopover"] button:hover { background-color: #ff1493 !important; }
</style>
""", unsafe_allow_html=True)

# ===============================
# 헤더
# ===============================
title_col, button_col = st.columns([4, 1])
with title_col:
    st.title("입고관리")
    st.write("상품 입고 내역을 등록하고 조회합니다.")
with button_col:
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
    if st.button("HOME", use_container_width=True):
        st.switch_page("main.py")

# ===============================
# 세션 상태 초기화
# ===============================
if "products" not in st.session_state:
    st.session_state.products = []           # 예: [{"code","name","category","unit","price"}]
if "receives" not in st.session_state:
    st.session_state.receives = []           # 발주 목록
if "receive_selected" not in st.session_state:
    st.session_state.receive_selected = set()
if "receive_edit_mode" not in st.session_state:
    st.session_state.receive_edit_mode = False
if "received_items" not in st.session_state:
    st.session_state.received_items = []     # 입고 완료된 항목들
if "staff_list" not in st.session_state:
    st.session_state.staff_list = ["김철수", "이영희", "박민수", "정수진"]

# (선택) 초기 참조데이터를 서버에서 가져오고 싶다면 여기를 해제
# with st.spinner("참조 데이터 불러오는 중..."):
#     items, e1 = api_get("/catalog/items")        # 품목 목록
#     staff, e2 = api_get("/ref/users")            # 담당자 목록
# if not e1 and isinstance(items, list): st.session_state.products = items
# if not e2 and isinstance(staff, list): st.session_state.staff_list = [u.get("name","") for u in staff if u.get("name")]

# ===============================
# 탭
# ===============================
order_tab, receive_tab = st.tabs(["발주 관리", "입고 확인"])

# ------------------------------------------------------------------
# 발주 관리 탭
# ------------------------------------------------------------------
with order_tab:
    st.subheader("발주 등록")

    # 검색 상태 초기화
    if "receive_search_results" not in st.session_state:
        st.session_state.receive_search_results = []
    if "receive_selected_product" not in st.session_state:
        st.session_state.receive_selected_product = None

    # 품목 검색
    search_col1, search_col2 = st.columns([2, 1])
    with search_col1:
        st.caption("품목 검색")
        product_search = st.text_input("품목 검색", key="receive_product_search",
                                       label_visibility="collapsed", placeholder="품목명 입력")
    with search_col2:
        st.markdown("<div style='height: 37px'></div>", unsafe_allow_html=True)
        if st.button("검색", key="receive_search_btn", use_container_width=True):
            if product_search:
                st.session_state.receive_search_results = [
                    p for p in st.session_state.products if product_search.lower() in p.get("name", "").lower()
                ]
            else:
                st.session_state.receive_search_results = st.session_state.products

    # 입력 변화에 따른 즉시 필터
    if product_search:
        st.session_state.receive_search_results = [
            p for p in st.session_state.products if product_search.lower() in p.get("name", "").lower()
        ]
    elif not product_search and len(st.session_state.products) > 0:
        st.session_state.receive_search_results = st.session_state.products

    # 검색 결과 표시
    if len(st.session_state.products) == 0:
        st.warning("등록된 품목이 없습니다. 기본정보 페이지에서 품목을 먼저 등록하세요.")
    elif st.session_state.receive_search_results:
        st.caption("검색 결과")
        product_options = [f"{p['name']} ({p['code']})" for p in st.session_state.receive_search_results]
        selected_option = st.selectbox("품목 선택", options=product_options,
                                       key="receive_product_select", label_visibility="collapsed")
        selected_idx = product_options.index(selected_option)
        st.session_state.receive_selected_product = st.session_state.receive_search_results[selected_idx]
        st.info(f"선택된 품목: {st.session_state.receive_selected_product['name']} "
                f"({st.session_state.receive_selected_product['code']})")
    else:
        st.warning("검색 결과가 없습니다.")

    # 발주 등록 폼
    with st.form("receive_form", clear_on_submit=True):
        r2c1, r2c2, r2c3 = st.columns([1, 1, 1])
        with r2c1:
            st.caption("발주 수량")
            receive_qty = st.number_input("발주 수량", min_value=1, step=1, value=1,
                                          key="receive_qty_input", label_visibility="collapsed")
        with r2c2:
            st.caption("발주 단가")
            default_price = st.session_state.receive_selected_product.get("price", 0) \
                if st.session_state.receive_selected_product else 0
            default_price_str = f"{default_price:,}" if default_price > 0 else ""
            receive_price_input = st.text_input("발주 단가", value=default_price_str,
                                                key="receive_price_input", label_visibility="collapsed",
                                                placeholder="100000")
            # 숫자만 추출
            if receive_price_input:
                price_clean = ''.join(filter(str.isdigit, receive_price_input.replace(",", "")))
                receive_price = int(price_clean) if price_clean else 0
                if receive_price:
                    st.caption(f"입력값: {receive_price:,}원")
            else:
                receive_price = 0
        with r2c3:
            st.caption("발주일")
            receive_date = st.date_input("발주일", key="receive_date_input", label_visibility="collapsed")

        r3c1, r3c2 = st.columns([2, 1])
        with r3c1:
            st.caption("비고")
            receive_note = st.text_input("비고", key="receive_note_input",
                                         label_visibility="collapsed", placeholder="입고 관련 메모")
        with r3c2:
            st.markdown("<div style='height: 37px'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button("등록", use_container_width=True)

        if submitted:
            if st.session_state.receive_selected_product is None:
                st.warning("품목을 선택하세요.")
            else:
                # (현재는 로컬 세션 저장. 서버 저장으로 전환하려면 아래 주석 해제)
                # payload = {
                #   "product_code": st.session_state.receive_selected_product["code"],
                #   "qty": receive_qty, "price": receive_price,
                #   "order_date": str(receive_date), "note": receive_note
                # }
                # resp, err = api_post("/inventory/receive/orders", payload)
                # if err: st.error(f"등록 실패: {err}")
                # else: st.success("발주가 등록되었습니다."); st.rerun()

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
                st.session_state.receive_search_results = []
                st.session_state.receive_selected_product = None
                st.rerun()

    st.markdown("---")

    # 발주 내역 검색
    search_row1, search_row2, search_row3 = st.columns([1, 1, 1])
    with search_row1:
        st.caption("품목명으로 검색")
        receive_product_search = st.text_input("품목명으로 검색", key="receive_history_product_search",
                                               label_visibility="collapsed", placeholder="품목명 입력")
    with search_row2:
        st.caption("카테고리로 검색")
        receive_category_search = st.text_input("카테고리로 검색", key="receive_history_category_search",
                                                label_visibility="collapsed", placeholder="카테고리명 입력")
    with search_row3:
        st.caption("발주일로 검색")
        receive_date_search = st.text_input("발주일로 검색", key="receive_history_date_search",
                                            label_visibility="collapsed", placeholder="2024-01-01")

    filtered_receives = st.session_state.receives
    if receive_product_search:
        filtered_receives = [r for r in filtered_receives if receive_product_search.lower() in r.get("product_name", "").lower()]
    if receive_category_search:
        filtered_receives = [r for r in filtered_receives if receive_category_search.lower() in r.get("category", "").lower()]
    if receive_date_search:
        filtered_receives = [r for r in filtered_receives if receive_date_search in r.get("date", "")]

    # 발주 내역 테이블
    with st.form("receive_list_form"):
        if st.session_state.receive_edit_mode:
            title_col, btn_col1, btn_col2 = st.columns([5, 1, 1])
            with title_col: st.subheader("발주 내역")
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
                        st.success("선택한 발주가 취소되었습니다."); st.rerun()
            with btn_col2:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("전체 취소", use_container_width=True):
                    st.session_state.receives = []
                    st.session_state.receive_selected = set()
                    st.session_state.receive_edit_mode = False
                    st.success("전체 발주가 취소되었습니다."); st.rerun()
        else:
            title_col, btn_col = st.columns([5, 1])
            with title_col: st.subheader("발주 내역")
            with btn_col:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("수정", use_container_width=True):
                    st.session_state.receive_edit_mode = True; st.rerun()

        if len(st.session_state.receives) == 0:
            st.warning("등록된 발주 내역이 없습니다"); st.form_submit_button("", use_container_width=True, help="")
        elif len(filtered_receives) == 0:
            st.warning("검색 결과가 없습니다"); st.form_submit_button("", use_container_width=True, help="")
        else:
            if receive_product_search or receive_category_search or receive_date_search:
                st.write(f"검색 결과: {len(filtered_receives)}개")

            h1, h2, h3, h4, h5, h6, h7, h8, h9 = st.columns([0.8, 1.5, 2, 1.5, 1.2, 1.5, 1.5, 1.2, 1.5])
            with h1: st.write("**선택**")
            with h2: st.write("**품목코드**")
            with h3: st.write("**품목명**")
            with h4: st.write("**카테고리**")
            with h5: st.write("**발주일**")
            with h6: st.write("**수량**")
            with h7: st.write("**단가**")
            with h8: st.write("**금액**")
            with h9: st.write("**비고**")

            for filtered_idx, receive in enumerate(filtered_receives):
                original_idx = next(i for i, r in enumerate(st.session_state.receives) if r == receive)
                c1, c2, c3, c4, c5, c6, c7, c8, c9 = st.columns([0.8, 1.5, 2, 1.5, 1.2, 1.5, 1.5, 1.2, 1.5])
                with c1:
                    is_checked = original_idx in st.session_state.receive_selected
                    checked = st.checkbox("", value=is_checked, key=f"receive_sel_{original_idx}")
                    if checked: st.session_state.receive_selected.add(original_idx)
                    else:       st.session_state.receive_selected.discard(original_idx)
                with c2: st.text_input("품목코드", value=receive["product_code"], key=f"receive_code_{original_idx}", disabled=True, label_visibility="collapsed")
                with c3: st.text_input("품목명", value=receive["product_name"], key=f"receive_name_{original_idx}", disabled=True, label_visibility="collapsed")
                with c4: st.text_input("카테고리", value=receive["category"], key=f"receive_category_{original_idx}", disabled=True, label_visibility="collapsed")
                with c5: st.text_input("발주일", value=receive.get("date", ""), key=f"receive_date_{original_idx}", disabled=True, label_visibility="collapsed")
                with c6: st.text_input("수량", value=str(receive["quantity"]), key=f"receive_qty_{original_idx}", disabled=True, label_visibility="collapsed")
                with c7: st.text_input("단가", value=f"{receive['price']:,}", key=f"receive_price_{original_idx}", disabled=True, label_visibility="collapsed")
                with c8:
                    total_price = receive["quantity"] * receive["price"]
                    st.text_input("총 금액", value=f"{total_price:,}", key=f"receive_total_{original_idx}", disabled=True, label_visibility="collapsed")
                with c9:
                    if receive.get("note", "").strip():
                        with st.popover("비고 확인", use_container_width=True):
                            st.write(f"**비고:** {receive['note']}")
                    else:
                        st.write("-")

# ------------------------------------------------------------------
# 입고 확인 탭
# ------------------------------------------------------------------
with receive_tab:
    st.subheader("입고 등록")

    # 미입고 발주 목록
    unreceived_orders = [r for r in st.session_state.receives if not r.get("is_received", False)]

    if len(unreceived_orders) == 0:
        st.warning("입고 처리가 필요한 발주가 없습니다.")
    else:
        st.caption("발주 선택")
        order_options = [f"{r['product_name']} ({r['product_code']}) - 발주수량: {r['quantity']}개" for r in unreceived_orders]
        selected_order_idx = st.selectbox("발주 건 선택",
                                          options=range(len(order_options)),
                                          format_func=lambda x: order_options[x],
                                          key="receive_order_select", label_visibility="collapsed")

        if selected_order_idx is not None:
            selected_order = unreceived_orders[selected_order_idx]
            st.info(f"선택된 발주: {selected_order['product_name']} ({selected_order['product_code']}) - 발주수량: {selected_order['quantity']}개")

            with st.form("receive_confirm_form", clear_on_submit=True):
                col1, col2 = st.columns([1, 1])
                with col1:
                    st.caption("발주 수량")
                    st.text_input("발주 수량", value=f"{selected_order['quantity']}개", key="order_qty_display", disabled=True, label_visibility="collapsed")

                    st.caption("실제 입고 수량")
                    actual_qty = st.number_input("실제 입고 수량", min_value=0, step=1, value=selected_order['quantity'],
                                                 key="actual_qty_input", label_visibility="collapsed")

                    st.caption("발주 단가")
                    st.text_input("발주 단가", value=f"{selected_order['price']:,}원", key="order_price_display", disabled=True, label_visibility="collapsed")

                    st.caption("실제 입고 단가")
                    actual_price = st.number_input("실제 입고 단가", min_value=0, step=100, value=selected_order['price'],
                                                   key="actual_price_input", label_visibility="collapsed")
                with col2:
                    st.caption("입고일")
                    receive_date = st.date_input("입고일", key="receive_confirm_date_input", label_visibility="collapsed")

                    st.caption("유통기한")
                    receive_expiry = st.date_input("유통기한", key="receive_expiry_input", label_visibility="collapsed")

                    st.caption("담당자")
                    staff_name = st.selectbox("담당자", options=st.session_state.staff_list,
                                              key="staff_select", label_visibility="collapsed")

                    st.caption("특이사항")
                    special_note = st.text_area("특이사항", key="special_note_input",
                                                label_visibility="collapsed",
                                                placeholder="포장 박스 일부 파손, 유통기한 임박 상품 포함 등", height=100)

                submitted = st.form_submit_button("입고 완료", use_container_width=True)

                if submitted:
                    if actual_qty == 0:
                        st.warning("실제 입고 수량을 입력하세요.")
                    else:
                        # (현재는 로컬 세션 저장. 서버 저장으로 전환하려면 아래 주석 해제)
                        # payload = {
                        #   "product_code": selected_order["product_code"],
                        #   "order_qty": selected_order["quantity"],
                        #   "actual_qty": actual_qty,
                        #   "order_price": selected_order["price"],
                        #   "actual_price": actual_price,
                        #   "receive_date": str(receive_date),
                        #   "expiry": str(receive_expiry),
                        #   "staff": staff_name,
                        #   "note": special_note,
                        # }
                        # resp, err = api_post("/inventory/receive/confirm", payload)
                        # if err: st.error(f"입고 저장 실패: {err}")
                        # else:
                        #   st.success("입고가 저장되었습니다."); st.rerun()

                        # 로컬 상태 업데이트
                        st.session_state.received_items.append({
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
                        })

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
                        if diff > 0: st.warning(f"과입고: {diff}개 초과")
                        else:        st.warning(f"부족: {abs(diff)}개 부족")
                with col2:
                    st.write(f"**발주 단가:** {item['order_price']:,}원")
                    st.write(f"**실제 입고 단가:** {item['actual_price']:,}원")
                    if item['order_price'] != item['actual_price']:
                        price_diff = item['actual_price'] - item['order_price']
                        if price_diff > 0: st.warning(f"단가 상승: +{price_diff:,}원")
                        else:               st.info(f"단가 하락: {price_diff:,}원")
                    st.write(f"**입고일:** {item['receive_date']}")
                    st.write(f"**담당자:** {item['staff']}")
                    st.write(f"**유통기한:** {item.get('expiry', '-')}")
                    if item.get('special_note'):
                        st.write(f"**특이사항:** {item['special_note']}")
