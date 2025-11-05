import os, sys
<<<<<<< Updated upstream
import streamlit as st
from client import api_get, api_post
=======
from typing import List, Dict, Any, Optional
>>>>>>> Stashed changes

import streamlit as st

# -------------------------------
# import 경로 보정
# -------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

from sidebar import render_sidebar
from client import api_get, api_post

<<<<<<< Updated upstream

# ===============================
# 페이지 설정 & 커스텀 사이드바
# ===============================
st.set_page_config(page_title="출고관리", page_icon="📤", layout="wide")
=======
# -------------------------------
# 페이지 설정 & 사이드바
# -------------------------------
st.set_page_config(page_title="출고 관리", page_icon="📤", layout="wide")
>>>>>>> Stashed changes
render_sidebar("release")

# -------------------------------
# 전역 스타일
# -------------------------------
st.markdown("""
<style>
<<<<<<< Updated upstream
  .main .block-container { max-width: 100%; padding: 1rem; }
  div[data-testid="stHorizontalBlock"] { padding-left: 1rem; }
=======
  .main .block-container {max-width: 100%; padding: 1rem 4rem;}
  [data-testid="stHorizontalBlock"] { padding-left: 1rem; }
  .muted {color:#6b7280}
>>>>>>> Stashed changes
</style>
""", unsafe_allow_html=True)

# -------------------------------
# 유틸: 참조 데이터
# -------------------------------
@st.cache_data(ttl=60)
def load_menu_items() -> List[Dict[str, Any]]:
    data, err = api_get("/menu_items", params={"active_only": True})
    if err:
        return []
    if isinstance(data, dict):
        for k in ("data", "items", "results"):
            if isinstance(data.get(k), list):
                data = data[k]
                break
    if not isinstance(data, list):
        return []
    out = []
    for m in data:
        if isinstance(m, dict) and m.get("id") and m.get("name"):
            out.append({
                "id": str(m["id"]),
                "name": str(m["name"]),
                "price": m.get("price") or 0,
                "category_id": m.get("category_id")
            })
    return out

@st.cache_data(ttl=60)
def load_locations() -> List[Dict[str, Any]]:
    data, err = api_get("/locations")
    if err:
        return []
    if isinstance(data, dict):
        for k in ("data", "items", "results"):
            if isinstance(data.get(k), list):
                data = data[k]
                break
    if not isinstance(data, list):
        return []
    out = []
    for x in data:
        if isinstance(x, dict) and x.get("id") and x.get("name"):
            out.append({"id": str(x["id"]), "name": str(x["name"])})
    return out

<<<<<<< Updated upstream
# releases: 이 페이지에서 관리하는 출고 내역
if "releases" not in st.session_state:
    st.session_state.releases = []        # [{product_code, product_name, qty, price, date, note}]
if "release_selected" not in st.session_state:
    st.session_state.release_selected = set()
if "release_edit_mode" not in st.session_state:
    st.session_state.release_edit_mode = False

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
=======
# -------------------------------
# 세션 초기화
# -------------------------------
if "cart" not in st.session_state:
    st.session_state.cart: List[Dict[str, Any]] = []  # [{"menu_item_id","menu_name","qty","unit_price","discount"}]
if "selected_location_id" not in st.session_state:
    st.session_state.selected_location_id: Optional[str] = None

# -------------------------------
>>>>>>> Stashed changes
# 헤더
# -------------------------------
left, right = st.columns([4, 1])
with left:
    st.title("출고 관리")
    st.caption("판매된 메뉴를 등록하면 DB가 레시피를 참조하여 원재료 재고를 자동 차감합니다.")
with right:
    st.markdown("<div style='height: 18px'></div>", unsafe_allow_html=True)
    if st.button("← 입고/발주로", use_container_width=True):
        st.switch_page("pages/receive.py")

st.divider()

<<<<<<< Updated upstream
# ------------------------------------------------------------------
# 출고 등록
# ------------------------------------------------------------------
with register_tab:
    st.subheader("출고 등록")

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
        st.info(f"선택된 품목: {st.session_state.release_selected_product['name']} "
                f"({st.session_state.release_selected_product['code']})")
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
            st.caption("출고 단가")
            # 품목에 price 속성이 있다면 기본값으로 사용
            default_price = st.session_state.release_selected_product.get("price", 0) \
                if st.session_state.release_selected_product else 0
            default_price_str = f"{default_price:,}" if default_price > 0 else ""
            price_input = st.text_input("출고 단가", value=default_price_str,
                                        key="release_price_input", label_visibility="collapsed",
                                        placeholder="100000")
            if price_input:
                clean = ''.join(filter(str.isdigit, price_input.replace(",", "")))
                out_price = int(clean) if clean else 0
                if out_price:
                    st.caption(f"입력값: {out_price:,}원")
            else:
                out_price = 0
        with r1c3:
            st.caption("출고일")
            out_date = st.date_input("출고일", key="release_date_input", label_visibility="collapsed")

        r2c1, r2c2 = st.columns([2,1])
        with r2c1:
            st.caption("비고")
            out_note = st.text_input("비고", key="release_note_input",
                                     label_visibility="collapsed", placeholder="출고 관련 메모")
        with r2c2:
            st.markdown("<div style='height: 37px'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button("출고 등록", use_container_width=True)

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
                    # (백엔드 저장으로 전환하려면 아래 주석을 사용)
                    payload = {
                      "product_code": code, "qty": out_qty, "price": out_price,
                      "release_date": str(out_date), "note": out_note
                    }
                    resp, err = api_post("/inventory/release/orders", payload)
                    if err: st.error(f"출고 등록 실패: {err}")
                    else: st.success("출고가 등록되었습니다."); st.rerun()

                    st.session_state.releases.append({
                        "product_code": code,
                        "product_name": name,
                        "qty": int(out_qty),
                        "price": int(out_price),
                        "date": str(out_date),
                        "note": out_note
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

    # 검색
    f1, f2, f3 = st.columns([1,1,1])
    with f1:
        st.caption("품목명으로 검색")
        name_q = st.text_input("품목명으로 검색", key="release_name_q",
                               label_visibility="collapsed", placeholder="품목명 입력")
    with f2:
        st.caption("출고일로 검색")
        date_q = st.text_input("출고일로 검색", key="release_date_q",
                               label_visibility="collapsed", placeholder="2025-01-01")
    with f3:
        st.caption("비고로 검색")
        note_q = st.text_input("비고로 검색", key="release_note_q",
                               label_visibility="collapsed", placeholder="메모")

    filtered = st.session_state.releases
    if name_q:
        filtered = [x for x in filtered if name_q.lower() in x.get("product_name","").lower()]
    if date_q:
        filtered = [x for x in filtered if date_q in x.get("date","")]
    if note_q:
        filtered = [x for x in filtered if note_q.lower() in x.get("note","").lower()]

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
            h1, h2, h3, h4, h5, h6, h7 = st.columns([0.8, 1.5, 2, 1.2, 1.2, 1.2, 2])
            with h1: st.write("**선택**")
            with h2: st.write("**품목코드**")
            with h3: st.write("**품목명**")
            with h4: st.write("**출고수량**")
            with h5: st.write("**단가**")
            with h6: st.write("**금액**")
            with h7: st.write("**비고**")

            for _, row in enumerate(filtered):
                idx = next(i for i, r in enumerate(st.session_state.releases) if r == row)
                c1, c2, c3, c4, c5, c6, c7 = st.columns([0.8, 1.5, 2, 1.2, 1.2, 1.2, 2])
                with c1:
                    is_checked = idx in st.session_state.release_selected
                    checked = st.checkbox("", value=is_checked, key=f"release_sel_{idx}")
                    if checked: st.session_state.release_selected.add(idx)
                    else:       st.session_state.release_selected.discard(idx)
                with c2: st.text_input("품목코드", value=row["product_code"], key=f"release_code_{idx}", disabled=True, label_visibility="collapsed")
                with c3: st.text_input("품목명", value=row["product_name"], key=f"release_name_{idx}", disabled=True, label_visibility="collapsed")
                with c4: st.text_input("출고수량", value=str(row["qty"]), key=f"release_qty_{idx}", disabled=True, label_visibility="collapsed")
                with c5: st.text_input("단가", value=f"{row['price']:,}", key=f"release_price_{idx}", disabled=True, label_visibility="collapsed")
                with c6:
                    total = int(row["qty"]) * int(row["price"])
                    st.text_input("금액", value=f"{total:,}", key=f"release_total_{idx}", disabled=True, label_visibility="collapsed")
                with c7:
                    if (row.get("note") or "").strip():
                        st.write(row["note"])
                    else:
                        st.write("-")
=======
# -------------------------------
# 참조 데이터 로드
# -------------------------------
menus = load_menu_items()
locations = load_locations()
menu_labels = [f"{m['name']} ({m['id'][:8]})" for m in menus]

# -------------------------------
# 1) 출고 등록(장바구니 스타일)
# -------------------------------
st.subheader("① 판매/출고 등록")

c1, c2 = st.columns([3, 2])
with c1:
    if not menus:
        st.warning("등록된 메뉴가 없습니다. 먼저 메뉴와 레시피를 등록하세요.")
    else:
        st.caption("메뉴 선택")
        sel = st.selectbox("메뉴", options=menu_labels, index=0, key="rel_menu", label_visibility="collapsed")
        sel_idx = menu_labels.index(sel)
        sel_menu = menus[sel_idx]

        cols = st.columns([1, 1, 1, 1])
        with cols[0]:
            qty = st.number_input("수량", min_value=1, value=1, step=1, key="rel_qty")
        with cols[1]:
            up = st.number_input("단가(원)", min_value=0, value=int(sel_menu.get("price") or 0), step=100, key="rel_price")
        with cols[2]:
            dc = st.number_input("할인(원)", min_value=0, value=0, step=100, key="rel_dc")
        with cols[3]:
            st.markdown("<div class='muted'> </div>", unsafe_allow_html=True)
            if st.button("장바구니 담기", use_container_width=True):
                st.session_state.cart.append({
                    "menu_item_id": sel_menu["id"],
                    "menu_name": sel_menu["name"],
                    "qty": int(qty),
                    "unit_price": int(up),
                    "discount": int(dc)
                })
                st.success(f"담김: {sel_menu['name']} × {qty}")
                st.rerun()

with c2:
    st.caption("출고(차감) 위치")
    if locations:
        loc_labels = [f"{l['name']} ({l['id'][:8]})" for l in locations]
        li = 0
        sel_loc = st.selectbox("로케이션", options=loc_labels, index=li, key="rel_loc", label_visibility="collapsed")
        st.session_state.selected_location_id = locations[loc_labels.index(sel_loc)]["id"]
    else:
        st.info("로케이션이 없습니다. 전체 재고에서 차감 또는 백엔드 기본 규칙 적용.")

# -------------------------------
# 2) 장바구니 내역
# -------------------------------
st.markdown("#### ② 장바구니")
if not st.session_state.cart:
    st.info("장바구니가 비어 있습니다.")
else:
    total_amount = 0
    for i, it in enumerate(st.session_state.cart):
        line_total = it["unit_price"] * it["qty"] - it["discount"]
        total_amount += line_total
        cc1, cc2, cc3, cc4, cc5 = st.columns([3, 1, 1, 1, 1])
        with cc1:
            st.write(f"• {it['menu_name']} ({it['menu_item_id'][:8]})")
        with cc2:
            st.write(f"수량: {it['qty']}")
        with cc3:
            st.write(f"단가: {it['unit_price']:,}원")
        with cc4:
            st.write(f"할인: {it['discount']:,}원")
        with cc5:
            if st.button("삭제", key=f"rel_del_{i}", use_container_width=True):
                st.session_state.cart.pop(i)
                st.rerun()
    st.info(f"총 결제 예정 금액: **{total_amount:,}원**")

# -------------------------------
# 3) 판매 등록 → /sales 호출
# -------------------------------
st.markdown("#### ③ 판매 등록")

colf1, colf2 = st.columns([2, 1])
with colf1:
    channel = st.selectbox("거래 채널", options=["POS", "ONLINE", "ETC"], index=0)
with colf2:
    commit = st.button("판매 등록(재고 자동 차감)", type="primary", use_container_width=True)

if commit:
    if not st.session_state.cart:
        st.warning("장바구니가 비어 있습니다.")
    else:
        payload = {
            "items": [
                {
                    "menu_item_id": it["menu_item_id"],
                    "qty": int(it["qty"]),
                    "unit_price": int(it["unit_price"]),
                    "discount": int(it["discount"]),
                }
                for it in st.session_state.cart
            ],
            "channel": channel
        }
        if st.session_state.selected_location_id:
            payload["location_id"] = st.session_state.selected_location_id

        resp, err = api_post("/sales", payload)
        if err:
            # 재고 부족 등
            if "INSUFFICIENT_STOCK" in (err or ""):
                st.error("재고가 부족합니다. 로케이션/수량을 확인하세요.")
            else:
                st.error(f"판매 등록 실패: {err}")
        else:
            sale_id = (resp or {}).get("sale_id")
            st.success(f"판매 등록 완료! sale_id={sale_id}")
            st.session_state.cart = []
            st.rerun()

# -------------------------------
# 4) 최근 판매 내역(선택)
# -------------------------------
st.markdown("#### ④ 최근 판매 (옵션)")
recent, err = api_get("/sales", params={"limit": 10})
if not err and isinstance(recent, list) and recent:
    for s in recent:
        st.write(f"- {s}")
else:
    st.caption("최근 판매 내역이 없거나 조회 엔드포인트가 비활성화입니다.")
>>>>>>> Stashed changes
