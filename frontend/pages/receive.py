import os, sys
import streamlit as st

# --- sidebar import 경로 보정 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))  # ../frontend
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

from sidebar import render_sidebar
from client import api_get, api_post
# --------------------------------


# ===============================
# 페이지 설정 & 커스텀 사이드바
# ===============================
st.set_page_config(page_title="입고관리", page_icon="📥", layout="wide")
render_sidebar("receive")

# ===============================
# 글로벌 스타일
# ===============================
st.markdown("""
<style>
  .main .block-container { max-width: 1200px; padding: 1rem 1rem 3rem; }
  .section { margin: 8px 0 18px; }
  .muted { color:#9aa0a6; font-size:0.9rem }
  div[data-testid="stPopover"] button { background-color:#ff69b4 !important; color:white !important; border:none !important; }
  div[data-testid="stPopover"] button:hover { background-color:#ff1493 !important; }
</style>
""", unsafe_allow_html=True)


# ===============================
# 유틸
# ===============================
def _toast_ok(msg: str):
    st.success(msg, icon="✅")

def _toast_err(msg: str):
    st.error(msg, icon="🚨")


# ===============================
# 캐시 / 초기 데이터 로드
# ===============================
if "ref_suppliers" not in st.session_state:
    st.session_state.ref_suppliers = []
if "ref_ingredients" not in st.session_state:
    st.session_state.ref_ingredients = []
if "ref_locations" not in st.session_state:
    st.session_state.ref_locations = []

with st.spinner("참조 데이터 불러오는 중..."):
    suppliers, e1 = api_get("/catalog/suppliers")
    if not e1 and isinstance(suppliers, list):
        st.session_state.ref_suppliers = suppliers

    ingredients, e2 = api_get("/catalog/ingredients")
    if not e2 and isinstance(ingredients, list):
        st.session_state.ref_ingredients = ingredients

    locations, e3 = api_get("/catalog/locations")
    if not e3 and isinstance(locations, list):
        st.session_state.ref_locations = locations


# ===============================
# 헤더
# ===============================
title_col, button_col = st.columns([4, 1])
with title_col:
    st.title("입고관리")
    st.caption("발주 → 부분 입고 → 재고 반영까지 한 화면에서 처리합니다.")
with button_col:
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
    if st.button("HOME", use_container_width=True):
        st.switch_page("main.py")


# ===============================
# 탭
# ===============================
po_tab, recv_tab = st.tabs(["발주 등록", "입고 등록"])


# ------------------------------------------------------------------
# 발주 등록 탭
# ------------------------------------------------------------------
with po_tab:
    st.subheader("거래처 기준 멀티 품목 발주")

    if not st.session_state.ref_suppliers:
        st.info("등록된 거래처가 없습니다. 먼저 거래처를 등록하세요.")
    if not st.session_state.ref_ingredients:
        st.info("등록된 품목이 없습니다. 먼저 품목을 등록하세요.")

    # 거래처 선택
    sup_map = {s["name"]: s["id"] for s in st.session_state.ref_suppliers} if st.session_state.ref_suppliers else {}
    sup_name = st.selectbox("거래처", options=list(sup_map.keys()) or ["(거래처 없음)"])
    supplier_id = sup_map.get(sup_name)

    # 발주 품목 라인 편집용 상태
    if "po_lines" not in st.session_state:
        st.session_state.po_lines = [{"ingredient_name": "", "ingredient_id": None, "qty": 0.0, "unit_price": 0.0}]

    # 라인 렌더링
    st.markdown('<div class="section"></div>', unsafe_allow_html=True)
    st.write("**발주 품목**")
    ing_map = {i["name"]: i["id"] for i in st.session_state.ref_ingredients} if st.session_state.ref_ingredients else {}

    remove_idx = None
    for idx, line in enumerate(st.session_state.po_lines):
        c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 1])
        with c1:
            name = st.selectbox(
                f"품목 {idx+1}",
                options=[""] + list(ing_map.keys()),
                index=([""] + list(ing_map.keys())).index(line["ingredient_name"]) if line["ingredient_name"] in ing_map else 0,
                key=f"po_ing_{idx}"
            )
            st.session_state.po_lines[idx]["ingredient_name"] = name
            st.session_state.po_lines[idx]["ingredient_id"] = ing_map.get(name)
        with c2:
            st.session_state.po_lines[idx]["qty"] = st.number_input(
                "수량", key=f"po_qty_{idx}", min_value=0.0, step=1.0, value=float(line.get("qty") or 0.0)
            )
        with c3:
            st.session_state.po_lines[idx]["unit_price"] = st.number_input(
                "단가", key=f"po_price_{idx}", min_value=0.0, step=100.0, value=float(line.get("unit_price") or 0.0)
            )
        with c4:
            # 금액 미리보기
            st.text_input("금액(자동)", value=f"{(line.get('qty') or 0)*(line.get('unit_price') or 0):,.0f}", key=f"po_amt_{idx}", disabled=True)
        with c5:
            st.markdown("<div style='height: 1.8rem'></div>", unsafe_allow_html=True)
            if st.button("삭제", key=f"po_del_{idx}", use_container_width=True):
                remove_idx = idx
    if remove_idx is not None and len(st.session_state.po_lines) > 1:
        st.session_state.po_lines.pop(remove_idx)
        st.rerun()

    # 라인 추가
    c_add, c_note = st.columns([1, 3])
    with c_add:
        if st.button("＋ 품목 추가", use_container_width=True):
            st.session_state.po_lines.append({"ingredient_name": "", "ingredient_id": None, "qty": 0.0, "unit_price": 0.0})
            st.rerun()
    with c_note:
        note = st.text_input("비고(선택)", placeholder="납기, 특약 등")

    st.markdown('<div class="section"></div>', unsafe_allow_html=True)
    if st.button("발주 등록", type="primary", use_container_width=True):
        # 유효성 검증
        if not supplier_id:
            _toast_err("거래처를 선택하세요.")
        else:
            items = []
            for ln in st.session_state.po_lines:
                if not ln["ingredient_id"] or (ln["qty"] or 0) <= 0:
                    continue
                items.append({
                    "ingredient_id": ln["ingredient_id"],
                    "qty": float(ln["qty"]),
                    "unit_price": float(ln["unit_price"] or 0),
                })
            if not items:
                _toast_err("발주 품목을 1개 이상 입력하세요.")
            else:
                payload = {
                    "supplier_id": supplier_id,
                    "note": note or None,
                    "items": items
                }
                _, err = api_post("/purchase/orders", payload)
                if err:
                    _toast_err(f"발주 등록 실패: {err}")
                else:
                    _toast_ok("발주가 등록되었습니다.")
                    # 폼 초기화
                    st.session_state.po_lines = [{"ingredient_name": "", "ingredient_id": None, "qty": 0.0, "unit_price": 0.0}]
                    st.rerun()


# ------------------------------------------------------------------
# 입고 등록 탭 (부분 입고 지원)
# ------------------------------------------------------------------
with recv_tab:
    st.subheader("발주 선택 → 부분 입고 처리")

    # 열린 발주 목록
    pos, err = api_get("/purchase/orders", params={"status": "open"})
    if err:
        _toast_err(f"발주 목록 조회 실패: {err}")
        pos = []

    # 거래처 필터
    col_f1, col_f2 = st.columns([2, 2])
    with col_f1:
        supplier_filter = st.selectbox(
            "거래처 필터", options=["(전체)"] + [s["name"] for s in st.session_state.ref_suppliers]
        )
    with col_f2:
        st.write(" ")

    if supplier_filter != "(전체)":
        sid = next((s["id"] for s in st.session_state.ref_suppliers if s["name"] == supplier_filter), None)
        pos = [p for p in pos if str(p.get("supplier_id")) == str(sid)]

    if not pos:
        st.info("열린 발주가 없습니다.")
        st.stop()

    # 발주 선택
    po_label_map = { p["id"]: f"{p['id'][:8]}… / 상태:{p['status']} / 주문:{int(p.get('ordered_qty',0))} / 수령:{int(p.get('received_qty',0))}" for p in pos }
    po_id = st.selectbox("발주 선택", options=list(po_label_map.keys()), format_func=lambda x: po_label_map[x])

    # 발주 상세(잔량 포함)
    detail, err2 = api_get(f"/purchase/orders/{po_id}")
    if err2 or not detail:
        _toast_err(f"발주 상세 조회 실패: {err2 or 'no data'}")
        st.stop()

    # 위치(창고) 선택
    loc_id = None
    if st.session_state.ref_locations:
        loc_name_map = {l["name"]: l["id"] for l in st.session_state.ref_locations}
        loc_name = st.selectbox("입고 위치(창고/매장)", options=list(loc_name_map.keys()))
        loc_id = loc_name_map.get(loc_name)
    else:
        st.caption("※ 위치 테이블이 없어서 위치 선택은 생략됩니다.")

    st.markdown('<div class="section"></div>', unsafe_allow_html=True)
    st.write("**입고 수량 입력 (남은 수량만큼 부분 입고 가능)**")

    # 품목별 입력 상태
    if "recv_lines" not in st.session_state or st.session_state.get("recv_po_id") != po_id:
        st.session_state.recv_po_id = po_id
        st.session_state.recv_lines = {}
        for it in detail["items"]:
            st.session_state.recv_lines[it["po_item_id"]] = {
                "qty": 0.0,
                "unit_price": float(it["unit_price"] or 0),
                "expiry_date": None,
                "note": ""
            }

    # 테이블 렌더
    headers = st.columns([3, 1, 1, 1, 2, 2])
    with headers[0]: st.write("**품목**")
    with headers[1]: st.write("**주문수량**")
    with headers[2]: st.write("**잔량**")
    with headers[3]: st.write("**입고수량**")
    with headers[4]: st.write("**단가**")
    with headers[5]: st.write("**유통기한/비고**")

    for it in detail["items"]:
        rem = float(it["remaining_qty"])
        ing_name = next((i["name"] for i in st.session_state.ref_ingredients if i["id"] == it["ingredient_id"]), it["ingredient_id"])
        row = st.columns([3, 1, 1, 1, 2, 2])

        with row[0]:
            st.text_input("품목", value=ing_name, key=f"lbl_ing_{it['po_item_id']}", disabled=True, label_visibility="collapsed")
        with row[1]:
            st.text_input("주문수량", value=str(it["ordered_qty"]), key=f"lbl_ord_{it['po_item_id']}", disabled=True, label_visibility="collapsed")
        with row[2]:
            st.text_input("잔량", value=str(rem), key=f"lbl_rem_{it['po_item_id']}", disabled=True, label_visibility="collapsed")
        with row[3]:
            st.session_state.recv_lines[it["po_item_id"]]["qty"] = st.number_input(
                "입고수량", min_value=0.0, max_value=rem, step=1.0,
                key=f"recv_qty_{it['po_item_id']}",
                value=float(st.session_state.recv_lines[it["po_item_id"]]["qty"] or 0.0)
            )
        with row[4]:
            st.session_state.recv_lines[it["po_item_id"]]["unit_price"] = st.number_input(
                "단가", min_value=0.0, step=100.0,
                key=f"recv_price_{it['po_item_id']}",
                value=float(st.session_state.recv_lines[it["po_item_id"]]["unit_price"] or 0.0)
            )
        with row[5]:
            ec1, ec2 = st.columns(2)
            with ec1:
                st.session_state.recv_lines[it["po_item_id"]]["expiry_date"] = st.date_input(
                    "유통기한", key=f"recv_exp_{it['po_item_id']}", format="YYYY-MM-DD"
                )
            with ec2:
                st.session_state.recv_lines[it["po_item_id"]]["note"] = st.text_input(
                    "비고", key=f"recv_note_{it['po_item_id']}", placeholder=""
                )

    st.markdown('<div class="section"></div>', unsafe_allow_html=True)
    if st.button("입고 완료", type="primary", use_container_width=True):
        # 수량 > 0인 라인만 전송
        items = []
        for po_item_id, v in st.session_state.recv_lines.items():
            q = float(v.get("qty") or 0)
            if q <= 0:
                continue
            items.append({
                "po_item_id": po_item_id,
                "qty": q,
                "unit_price": float(v.get("unit_price") or 0),
                "expiry_date": str(v["expiry_date"]) if v.get("expiry_date") else None,
                "note": v.get("note") or None
            })

        if not items:
            _toast_err("입고 수량을 1개 이상 입력하세요.")
        else:
            payload = {
                "location_id": loc_id,
                "note": "부분 입고",
                "items": items
            }
            _, errx = api_post(f"/purchase/receipts/from-po/{po_id}", payload)
            if errx:
                _toast_err(f"입고 처리 실패: {errx}")
            else:
                _toast_ok("입고 처리되었습니다. (재고는 트리거로 반영)")
                # 현재 선택 발주만 초기화 → 다시 잔량 조회
                st.session_state.pop("recv_lines", None)
                st.session_state.pop("recv_po_id", None)
                st.rerun()
