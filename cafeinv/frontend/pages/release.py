import os, sys
import streamlit as st
from datetime import datetime, date
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
st.set_page_config(page_title="출고관리", page_icon="📤", layout="wide")
render_sidebar("release")

# ===============================
# 글로벌 스타일 (여백 조정)
# ===============================
st.markdown("""
<style>
  .main .block-container { max-width: 100%; padding-top: 1rem; padding-right: 4rem; padding-left: 4rem; padding-bottom: 1rem; }
  div[data-testid="stHorizontalBlock"] { padding-left: 1rem; }
</style>
""", unsafe_allow_html=True)

# ===============================
# 세션 상태 초기화
# ===============================
# products: info.py의 품목 등록을 공유
if "products" not in st.session_state:
    st.session_state.products = []

# received_items: receive.py에서 입고 완료된 항목을 공유
if "received_items" not in st.session_state:
    st.session_state.received_items = []  # [{product_code, product_name, actual_qty, ...}]

# releases: 이 페이지에서 관리하는 출고 내역
if "releases" not in st.session_state:
    st.session_state.releases = []        # [{product_code, product_name, qty, price, date, note, release_type, staff, reason}]
if "release_selected" not in st.session_state:
    st.session_state.release_selected = set()
if "release_edit_mode" not in st.session_state:
    st.session_state.release_edit_mode = False

# recipes: 레시피 데이터 (메뉴명 -> 재료 목록)
if "recipes" not in st.session_state:
    st.session_state.recipes = {}  # {menu_name: [{"ingredient_code": "A001", "ingredient_name": "A 원두", "qty": 20, "unit": "g"}, ...]}

# staff_list: 담당자 목록
if "staff_list" not in st.session_state:
    st.session_state.staff_list = ["김철수", "이영희", "박민수", "정수진"]

# ===============================
# 유틸: 현재 재고 계산 (세션 기반)
# ===============================
def calc_stock_map():
    """
    세션의 received_items/ releases를 이용해 품목별 재고를 dict로 반환.
    { product_code: {"name": name, "stock": int} }
    """
    stock = {}
    # 입고 합산
    for r in st.session_state.received_items:
        code = r["product_code"]
        name = r["product_name"]
        qty  = int(r.get("actual_qty", 0))
        if code not in stock:
            stock[code] = {"name": name, "stock": 0}
        stock[code]["stock"] += qty
    # 출고 차감
    for o in st.session_state.releases:
        code = o["product_code"]
        qty  = int(o.get("qty", 0))
        if code not in stock:
            # 입고가 없었는데 출고가 먼저 있었다면(비정상) 음수로 내려갈 수 있음
            stock[code] = {"name": o.get("product_name", code), "stock": 0}
        stock[code]["stock"] -= qty
    return stock

# ===============================
# 헤더
# ===============================
title_col, right_col = st.columns([4, 2])
with title_col:
    st.title("출고관리")
    st.caption("상품 출고 내역을 등록하고 조회합니다. (세션 재고 검증)")
with right_col:
    st.write(""); st.write("")
    if st.button("HOME", use_container_width=True):
        st.switch_page("main.py")

# ===============================
# 탭
# ===============================
register_tab, history_tab = st.tabs(["출고 등록", "출고 내역"])

# ------------------------------------------------------------------
# 출고 등록
# ------------------------------------------------------------------
with register_tab:
    st.subheader("출고 등록")
    
    # ① 출고 유형 선택 (가장 중요!)
    st.markdown("#### ① 출고 유형 선택 (필수)")
    release_type = st.radio(
        "출고 유형",
        options=["판매 출고", "재료 소모", "폐기 처분", "기타 출고"],
        key="release_type_select",
        horizontal=True,
        help="출고 유형을 선택하면 재고 감소 원인을 명확히 구분할 수 있습니다."
    )
    
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ② 레시피 기반 출고 (판매 출고 시) 또는 ③ 직접 출고 (재료 소모, 폐기 처분 시)
    if release_type == "판매 출고":
        st.markdown("#### ② 레시피 기반 출고 (판매 출고)")
        st.info("💡 메뉴를 선택하면 레시피에 따라 필요한 재료가 자동으로 출고 목록에 추가됩니다.")
        
        # 메뉴 목록 (레시피가 있는 메뉴들)
        menu_options = ["선택하세요"] + list(st.session_state.recipes.keys())
        if len(menu_options) == 1:
            st.warning("등록된 레시피가 없습니다. 기본정보 > 레시피 등록에서 레시피를 먼저 등록하세요.")
            selected_menu = None
        else:
            selected_menu = st.selectbox("메뉴 선택", options=menu_options, key="release_menu_select")
            
            # 메뉴 수량 입력
            menu_qty = st.number_input("메뉴 수량", min_value=1, step=1, value=1, key="release_menu_qty")
            
            # 레시피에 따른 재료 자동 계산
            if selected_menu and selected_menu != "선택하세요" and selected_menu in st.session_state.recipes:
                st.markdown("**자동 계산된 재료 출고 목록:**")
                recipe_items = st.session_state.recipes[selected_menu]
                stock_map = calc_stock_map()
                for item in recipe_items:
                    total_qty = item["qty"] * menu_qty
                    unit = item.get("unit", "g")
                    ingredient_code = item.get("ingredient_code", "")
                    current_stock = stock_map.get(ingredient_code, {"stock": 0})["stock"]
                    st.write(f"- {item['ingredient_name']} ({ingredient_code}): {total_qty}{unit} (재고: {current_stock})")
            
            # 출고 등록 폼
            with st.form("release_recipe_form", clear_on_submit=True):
                r1c1, r1c2 = st.columns([1, 1])
                with r1c1:
                    st.caption("④ 출고일")
                    out_date = st.date_input("출고일", key="release_date_input", value=date.today(), label_visibility="collapsed")
                with r1c2:
                    st.caption("담당자")
                    staff_name = st.selectbox("담당자", options=st.session_state.staff_list, key="release_staff_select", label_visibility="collapsed")
                
                r2c1, r2c2 = st.columns([2, 1])
                with r2c1:
                    st.caption("⑤ 출고 사유 및 메모")
                    out_reason = st.text_area("출고 사유 및 메모", key="release_reason_input",
                                             placeholder="예: 아메리카노 10잔 판매",
                                             height=100, label_visibility="collapsed")
                with r2c2:
                    st.markdown("<div style='height: 100px'></div>", unsafe_allow_html=True)
                    submitted = st.form_submit_button("출고 등록", use_container_width=True, type="primary")
                
                if submitted:
                    if selected_menu == "선택하세요" or selected_menu not in st.session_state.recipes:
                        st.warning("메뉴를 선택하세요.")
                    else:
                        recipe_items = st.session_state.recipes[selected_menu]
                        all_sufficient = True
                        insufficient_items = []
                        
                        # 재고 확인
                        stock_map = calc_stock_map()
                        for item in recipe_items:
                            ingredient_code = item["ingredient_code"]
                            required_qty = item["qty"] * menu_qty
                            current_stock = stock_map.get(ingredient_code, {"stock": 0})["stock"]
                            
                            if required_qty > current_stock:
                                all_sufficient = False
                                insufficient_items.append({
                                    "name": item["ingredient_name"],
                                    "required": required_qty,
                                    "available": current_stock
                                })
                        
                        if not all_sufficient:
                            error_msg = "재고 부족:\n"
                            for item in insufficient_items:
                                error_msg += f"- {item['name']}: 필요 {item['required']}, 재고 {item['available']}\n"
                            st.error(error_msg)
                        else:
                            # 모든 재료 출고 등록
                            for item in recipe_items:
                                ingredient_code = item["ingredient_code"]
                                ingredient_name = item["ingredient_name"]
                                qty = item["qty"] * menu_qty
                                
                                st.session_state.releases.append({
                                    "product_code": ingredient_code,
                                    "product_name": ingredient_name,
                                    "qty": int(qty),
                                    "price": 0,  # 판매 출고는 가격 없음
                                    "date": str(out_date),
                                    "note": f"{selected_menu} {menu_qty}잔 판매 - {out_reason}" if out_reason else f"{selected_menu} {menu_qty}잔 판매",
                                    "release_type": release_type,
                                    "staff": staff_name,
                                    "reason": out_reason or f"{selected_menu} {menu_qty}잔 판매"
                                })
                            
                            st.success(f"{selected_menu} {menu_qty}잔 출고가 등록되었습니다.")
                            st.rerun()
    
    else:
        # ③ 직접 출고 (재료 소모, 폐기 처분, 기타 출고)
        st.markdown(f"#### ③ 직접 출고 ({release_type})")
        st.info(f"💡 {release_type}에 해당하는 재료를 직접 선택하고 출고 수량을 입력하세요.")
        
        # 현재 재고표 (간단 요약)
        stock_map = calc_stock_map()
        with st.expander("현재 재고(요약) 보기", expanded=False):
            if not stock_map:
                st.info("재고 데이터가 없습니다. (입고 내역이 없거나 초기 상태)")
            else:
                colh1, colh2 = st.columns([2,1])
                with colh1: st.write("**품목**")
                with colh2: st.write("**재고**")
                for code, info in stock_map.items():
                    c1, c2 = st.columns([2,1])
                    with c1: st.write(f"{info['name']} ({code})")
                    with c2: st.write(f"{info['stock']}")

        # 품목 검색/선택
        if "release_search_results" not in st.session_state:
            st.session_state.release_search_results = []
        if "release_selected_product" not in st.session_state:
            st.session_state.release_selected_product = None

        s1, s2 = st.columns([2,1])
        with s1:
            st.caption("품목 검색")
            keyword = st.text_input("품목 검색", key="release_product_search",
                                    label_visibility="collapsed", placeholder="품목명 입력")
        with s2:
            st.markdown("<div style='height: 37px'></div>", unsafe_allow_html=True)
            if st.button("검색", key="release_search_btn", use_container_width=True):
                if keyword:
                    st.session_state.release_search_results = [
                        p for p in st.session_state.products if keyword.lower() in p.get("name","").lower()
                    ]
                else:
                    st.session_state.release_search_results = st.session_state.products

        # 즉시 필터
        if keyword:
            st.session_state.release_search_results = [
                p for p in st.session_state.products if keyword.lower() in p.get("name","").lower()
            ]
        elif not keyword and len(st.session_state.products) > 0:
            st.session_state.release_search_results = st.session_state.products

        if len(st.session_state.products) == 0:
            st.warning("등록된 품목이 없습니다. 기본정보 페이지에서 품목을 먼저 등록하세요.")
        elif st.session_state.release_search_results:
            st.caption("검색 결과")
            options = [f"{p['name']} ({p['code']})" for p in st.session_state.release_search_results]
            selected = st.selectbox("품목 선택", options=options, key="release_product_select",
                                    label_visibility="collapsed")
            sel_idx = options.index(selected)
            st.session_state.release_selected_product = st.session_state.release_search_results[sel_idx]
            st.info(f"선택된 품목: {st.session_state.release_search_results[sel_idx]['name']} "
                    f"({st.session_state.release_search_results[sel_idx]['code']})")
        else:
            st.warning("검색 결과가 없습니다.")

        # 출고 입력 폼
        with st.form("release_form", clear_on_submit=True):
            r1c1, r1c2, r1c3 = st.columns([1,1,1])
            with r1c1:
                st.caption("출고 수량")
                out_qty = st.number_input("출고 수량", min_value=1, step=1, value=1,
                                          key="release_qty_input", label_visibility="collapsed")
            with r1c2:
                st.caption("④ 출고일")
                out_date = st.date_input("출고일", key="release_date_input", value=date.today(), label_visibility="collapsed")
            with r1c3:
                st.caption("담당자")
                staff_name = st.selectbox("담당자", options=st.session_state.staff_list, key="release_staff_select", label_visibility="collapsed")

            r2c1, r2c2 = st.columns([2,1])
            with r2c1:
                st.caption("⑤ 출고 사유 및 메모")
                out_reason = st.text_area("출고 사유 및 메모", key="release_reason_input",
                                         placeholder="예: 유통기한 경과로 우유 3팩 폐기, 신메뉴 테스트로 원두 100g 소모 등",
                                         height=100, label_visibility="collapsed")
            with r2c2:
                st.markdown("<div style='height: 100px'></div>", unsafe_allow_html=True)
                submitted = st.form_submit_button("출고 등록", use_container_width=True, type="primary")

            if submitted:
                if st.session_state.release_selected_product is None:
                    st.warning("품목을 선택하세요.")
                else:
                    code = st.session_state.release_selected_product["code"]
                    name = st.session_state.release_selected_product["name"]
                    current_stock = calc_stock_map().get(code, {"stock": 0})["stock"]

                    if out_qty > max(0, int(current_stock)):
                        st.error(f"재고 부족: 현재 재고 {current_stock}개, 요청 {out_qty}개")
                    else:
                        st.session_state.releases.append({
                            "product_code": code,
                            "product_name": name,
                            "qty": int(out_qty),
                            "price": 0,  # 직접 출고는 가격 없음
                            "date": str(out_date),
                            "note": out_reason or f"{release_type}",
                            "release_type": release_type,
                            "staff": staff_name,
                            "reason": out_reason or f"{release_type}"
                        })
                        st.success("출고 내역이 등록되었습니다.")
                        st.session_state.release_search_results = []
                        st.session_state.release_selected_product = None
                        st.rerun()

# ------------------------------------------------------------------
# 출고 내역
# ------------------------------------------------------------------
with history_tab:
    st.subheader("출고 내역")
    
    # ⑥ 출고 내역 조회 및 검색 (Form 형태)
    st.markdown("#### ⑥ 출고 내역 조회 및 검색")
    with st.form("release_history_search_form", clear_on_submit=False):
        search_col1, search_col2, search_col3, search_col4 = st.columns([2, 1, 1, 1])
        with search_col1:
            search_query = st.text_input("검색", key="release_history_search",
                                        placeholder="품목명, 출고일, 비고, 담당자 등 모든 항목으로 검색 가능",
                                        label_visibility="collapsed")
        with search_col2:
            st.caption("기간 시작")
            start_date_q = st.date_input("시작일", key="release_start_date", value=date.today().replace(day=1), label_visibility="collapsed")
        with search_col3:
            st.caption("기간 종료")
            end_date_q = st.date_input("종료일", key="release_end_date", value=date.today(), label_visibility="collapsed")
        with search_col4:
            st.caption("출고 유형")
            release_type_filter = st.selectbox("출고 유형", 
                                               options=["전체", "판매 출고", "재료 소모", "폐기 처분", "기타 출고"],
                                               key="release_type_filter", label_visibility="collapsed")
        
        search_col5, search_col6 = st.columns([1, 1])
        with search_col5:
            st.caption("담당자")
            staff_filter = st.selectbox("담당자 필터", 
                                       options=["전체"] + st.session_state.staff_list,
                                       key="release_staff_filter", label_visibility="collapsed")
        with search_col6:
            st.markdown("<div style='height: 37px'></div>", unsafe_allow_html=True)
            search_submitted = st.form_submit_button("검색", use_container_width=True, type="primary")
    
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    
    # 필터링 적용
    filtered = list(st.session_state.releases)
    
    # 통합 검색 (모든 필드 검색)
    if search_query and search_query.strip():
        search_term = search_query.strip().lower()
        filtered = [x for x in filtered 
                   if search_term in x.get("product_name", "").lower()
                   or search_term in x.get("product_code", "").lower()
                   or search_term in x.get("date", "")
                   or search_term in x.get("note", "").lower()
                   or search_term in x.get("reason", "").lower()
                   or search_term in x.get("staff", "").lower()
                   or search_term in x.get("release_type", "").lower()]
    
    # 기간 필터
    if start_date_q and end_date_q:
        temp_filtered = []
        for x in filtered:
            try:
                release_date = datetime.strptime(x.get("date", ""), "%Y-%m-%d").date()
                if start_date_q <= release_date <= end_date_q:
                    temp_filtered.append(x)
            except:
                pass
        filtered = temp_filtered
    
    # 출고 유형 필터
    if release_type_filter and release_type_filter != "전체":
        filtered = [x for x in filtered if x.get("release_type") == release_type_filter]
    
    # 담당자 필터
    if staff_filter and staff_filter != "전체":
        filtered = [x for x in filtered if x.get("staff") == staff_filter]

    # 테이블 (편집/삭제)
    with st.form("release_list_form"):
        if st.session_state.release_edit_mode:
            tcol, b1, b2 = st.columns([5,1,1])
            with tcol: st.subheader("출고 내역")
            with b1:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("선택 삭제", use_container_width=True):
                    if not st.session_state.release_selected:
                        st.info("삭제할 항목을 선택하세요.")
                    else:
                        # 삭제 전 재고 검증: 삭제하면 재고가 증가(되돌림)이므로 별도 검증 불필요
                        for i in sorted(st.session_state.release_selected, reverse=True):
                            if 0 <= i < len(st.session_state.releases):
                                st.session_state.releases.pop(i)
                        st.session_state.release_selected = set()
                        st.session_state.release_edit_mode = False
                        st.success("선택한 출고 내역을 삭제했습니다."); st.rerun()
            with b2:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("전체 삭제", use_container_width=True):
                    st.session_state.releases = []
                    st.session_state.release_selected = set()
                    st.session_state.release_edit_mode = False
                    st.success("전체 출고 내역을 삭제했습니다."); st.rerun()
        else:
            tcol, b = st.columns([5,1])
            with tcol: st.subheader("출고 내역")
            with b:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("수정", use_container_width=True):
                    st.session_state.release_edit_mode = True; st.rerun()

        if len(st.session_state.releases) == 0:
            st.warning("등록된 출고 내역이 없습니다"); st.form_submit_button("", use_container_width=True, help="")
        elif len(filtered) == 0:
            st.warning("검색 결과가 없습니다"); st.form_submit_button("", use_container_width=True, help="")
        else:
            if search_query or release_type_filter != "전체" or staff_filter != "전체" or (start_date_q and end_date_q):
                st.info(f"검색 결과: {len(filtered)}건")
            
            h1, h2, h3, h4, h5, h6, h7, h8, h9 = st.columns([0.8, 1.2, 1.8, 1, 0.8, 1, 1.2, 1.2, 1.5])
            with h1: st.write("**선택**")
            with h2: st.write("**출고일**")
            with h3: st.write("**품목명**")
            with h4: st.write("**출고수량**")
            with h5: st.write("**출고유형**")
            with h6: st.write("**담당자**")
            with h7: st.write("**출고사유**")
            with h8: st.write("**비고**")
            with h9: st.write("**상태**")

            for _, row in enumerate(filtered):
                idx = next(i for i, r in enumerate(st.session_state.releases) if r == row)
                c1, c2, c3, c4, c5, c6, c7, c8, c9 = st.columns([0.8, 1.2, 1.8, 1, 0.8, 1, 1.2, 1.2, 1.5])
                with c1:
                    is_checked = idx in st.session_state.release_selected
                    checked = st.checkbox("", value=is_checked, key=f"release_sel_{idx}")
                    if checked: st.session_state.release_selected.add(idx)
                    else:       st.session_state.release_selected.discard(idx)
                with c2: 
                    st.write(row.get("date", "-"))
                with c3: 
                    st.write(f"{row.get('product_name', '-')} ({row.get('product_code', '-')})")
                with c4: 
                    st.write(f"{row.get('qty', 0):,}")
                with c5: 
                    release_type_display = row.get("release_type", "-")
                    st.write(release_type_display)
                with c6: 
                    st.write(row.get("staff", "-"))
                with c7: 
                    reason = row.get("reason", "-")
                    if reason and reason != "-":
                        st.write(reason[:20] + "..." if len(reason) > 20 else reason)
                    else:
                        st.write("-")
                with c8: 
                    note = row.get("note", "")
                    if note and note.strip():
                        st.write(note[:20] + "..." if len(note) > 20 else note)
                    else:
                        st.write("-")
                with c9:
                    st.success("✅ 등록됨")