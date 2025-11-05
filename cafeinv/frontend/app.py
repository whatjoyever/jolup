
import os
import json
from uuid import UUID

import streamlit as st
import pandas as pd
import requests
from dotenv import load_dotenv
from urllib.parse import quote

# -----------------------------
# 환경설정
# -----------------------------
load_dotenv()
API = os.getenv("API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Cafe Inventory", layout="wide")
st.title("☕ Cafe Inventory Dashboard")

# -----------------------------
# 헬퍼 함수: 리스트 정규화
# -----------------------------
def as_list(value):
    """단일 값이 들어와도 항상 리스트로 변환"""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]

# -----------------------------
# 방어적 정규화 헬퍼
# -----------------------------
def _as_list(x):
    if x is None:
        return []
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        # 흔한 컨테이너 키 우선
        for k in ("data", "rows", "items", "result", "results"):
            v = x.get(k)
            if isinstance(v, list):
                return v
        return [x]
    return [x]

def build_ref_map(refs, name_keys=("name",), id_keys=("id",)):
    """
    refs: list[dict] | list[list|tuple] | list[str] | dict 컨테이너/단일객체 등
    name_keys/id_keys: 우선순위 후보 키 튜플
    """
    out = {}
    for obj in _as_list(refs):
        if isinstance(obj, dict):
            nk = next((k for k in name_keys if k in obj), None)
            ik = next((k for k in id_keys if k in obj), None)
            if nk and ik:
                out[str(obj[nk])] = str(obj[ik])
        elif isinstance(obj, (list, tuple)) and len(obj) >= 2:
            out[str(obj[0])] = str(obj[1])
        elif isinstance(obj, str):
            out[obj] = obj
    return out

# -----------------------------
# HTTP
# -----------------------------
def api_get(path: str, params: dict | None = None, timeout: int = 10):
    try:
        r = requests.get(f"{API}{path}", params=params, timeout=timeout)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)

def api_post(path: str, payload: dict, timeout: int = 15):
    try:
        r = requests.post(f"{API}{path}", json=payload, timeout=timeout)
        if r.status_code == 200:
            return r.json(), None
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        return None, f"{r.status_code} {detail}"
    except Exception as e:
        return None, str(e)

def safe_uuid(s: str) -> str | None:
    try:
        return str(UUID(s))
    except Exception:
        return None

def normalize_name_id_list(
    raw,
    name_keys=("name", "category_name", "label", "title"),
    id_keys=("id", "category_id", "uuid", "value"),
):
    """다양한 응답(raw)을 [{name,id}, ...] 로 통일"""
    if isinstance(raw, dict):
        for key in ("data", "items", "categories", "results"):
            if isinstance(raw.get(key), list):
                raw = raw[key]
                break

    out = []
    if not isinstance(raw, list):
        return out

    for item in raw:
        if isinstance(item, dict):
            name = next((item.get(k) for k in name_keys if item.get(k) is not None), None)
            _id  = next((item.get(k) for k in id_keys   if item.get(k) is not None), None)
            if name and _id:
                out.append({"name": name, "id": _id})
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            out.append({"name": str(item[0]), "id": str(item[1])})
    return out

# -----------------------------
# 탭 구성
# -----------------------------
tab_health, tab_inventory, tab_sale, tab_alerts = st.tabs(
    ["Health", "Inventory", "Make Sale", "Alerts"]
)

# -----------------------------
# 1) Health
# -----------------------------
with tab_health:
    st.subheader("API / DB 상태")
    data, err = api_get("/health")
    col1, col2 = st.columns([1, 2])
    with col1:
        if err:
            st.error(f"Health 체크 실패: {err}")
        else:
            ok = data.get("ok", False)
            db_ok = data.get("db", None)
            if ok:
                st.success("✅ API 서버 OK")
            else:
                st.error("❌ API 서버 오류")
            if db_ok is None:
                st.info("DB 핑 정보는 비활성화되어 있습니다 (선택 기능).")
            elif db_ok:
                st.success("✅ DB 연결 OK")
            else:
                st.error("❌ DB 연결 실패")
    with col2:
        st.code(json.dumps(data if data else {"error": err}, indent=2), language="json")
    st.caption(f"API_URL = {API}")

# -----------------------------
# 2) Inventory
# -----------------------------
with tab_inventory:
    st.subheader("현재고 조회")
    with st.form("inv_form"):
        location_id = st.text_input("location_id (옵션, 비우면 전체)", value="")
        submitted = st.form_submit_button("조회")
    params = {}
    if location_id.strip():
        uuid_norm = safe_uuid(location_id.strip())
        if not uuid_norm:
            st.error("location_id가 UUID 형식이 아닙니다.")
        else:
            params["location_id"] = uuid_norm
    data, err = api_get("/inventory", params=params if params else None)
    if err:
        st.error(f"Inventory 호출 실패: {err}")
    else:
        df = pd.DataFrame(data)
        if df.empty:
            st.info("데이터가 없습니다.")
        else:
            st.dataframe(df, use_container_width=True)
            st.caption("※ inventory 스키마: ingredient_id, location_id, qty_on_hand")

# -----------------------------
# 3) Make Sale (레시피 자동 차감)
# -----------------------------
with tab_sale:
    st.subheader("판매 등록 (레시피 기반 자동 차감)")

    with st.expander("📌 사용 팁", expanded=False):
        st.markdown(
            """
            - `location_id`는 **가능하면 입력**하세요. (메뉴의 `default_location_id`가 없으면 필수)
            - `menu_item_id`는 메뉴 UUID입니다.
            - 레시피(`recipes`)에 정의된 원재료가 판매수량 × 필요량 만큼 자동 차감됩니다.
            - 재고가 부족하면 **409 / INSUFFICIENT_STOCK** 에러가 납니다.
            """
        )

    # 여러 라인 입력 상태 초기화
    if "sale_lines" not in st.session_state:
        st.session_state.sale_lines = [
            {"menu_item_id": "", "qty": 1.0, "unit_price": 4500.0, "discount": 0.0}
        ]

    def add_line():
        st.session_state.sale_lines.append(
            {"menu_item_id": "", "qty": 1.0, "unit_price": 4500.0, "discount": 0.0}
        )

    def clear_lines():
        st.session_state.sale_lines = [
            {"menu_item_id": "", "qty": 1.0, "unit_price": 4500.0, "discount": 0.0}
        ]

    b1, b2 = st.columns(2)
    if b1.button("➕ 라인 추가", use_container_width=True):
        add_line()
    if b2.button("🧹 라인 초기화", use_container_width=True):
        clear_lines()

    with st.form("sale_form", clear_on_submit=False):
        colA, colB = st.columns([1, 1])
        with colA:
            location_id_in = st.text_input("location_id (권장, UUID)", value="")
            channel = st.text_input("channel", value="POS")
        with colB:
            st.write("")

        for idx, line in enumerate(st.session_state.sale_lines, start=1):
            st.markdown(f"**라인 {idx}**")
            l1, l2, l3, l4 = st.columns([2, 1, 1, 1])
            line["menu_item_id"] = l1.text_input("menu_item_id (UUID)", key=f"mid_{idx}", value=line["menu_item_id"])
            line["qty"] = l2.number_input("qty", min_value=0.0, step=1.0, value=float(line["qty"]), key=f"qty_{idx}")
            line["unit_price"] = l3.number_input("unit_price", min_value=0.0, step=100.0, value=float(line["unit_price"]), key=f"price_{idx}")
            line["discount"] = l4.number_input("discount", min_value=0.0, step=100.0, value=float(line["discount"]), key=f"disc_{idx}")
            st.divider()

        submitted = st.form_submit_button("🧾 판매 등록", type="primary")

    if submitted:
        items = []
        all_ok = True
        for line in st.session_state.sale_lines:
            mid = safe_uuid(line["menu_item_id"].strip())
            if not mid:
                st.error("menu_item_id가 UUID 형식이 아닙니다.")
                all_ok = False
                break
            if float(line["qty"]) <= 0:
                st.error("qty는 1 이상이어야 합니다.")
                all_ok = False
                break
            items.append(
                {
                    "menu_item_id": mid,
                    "qty": float(line["qty"]),
                    "unit_price": float(line["unit_price"]),
                    "discount": float(line["discount"]),
                }
            )

        payload = {"items": items, "channel": channel}
        if location_id_in.strip():
            loc_norm = safe_uuid(location_id_in.strip())
            if not loc_norm:
                st.error("location_id가 UUID 형식이 아닙니다.")
                all_ok = False
            else:
                payload["location_id"] = loc_norm

        if all_ok:
            resp, err = api_post("/sales", payload)
            if err:
                if "INSUFFICIENT_STOCK" in err:
                    st.error("❌ 재고 부족(INSUFFICIENT_STOCK)")
                else:
                    st.error(f"❌ 판매 등록 실패: {err}")
            else:
                st.success(f"✅ 판매 등록 완료! sale_id={resp.get('sale_id')}, total_amount={resp.get('total_amount')}")
                st.balloons()

# -----------------------------
# 4) Alerts
# -----------------------------
with tab_alerts:
    st.subheader("미해제 알림")
    data, err = api_get("/alerts")
    if err:
        st.error(f"Alerts 호출 실패: {err}")
    else:
        df = pd.DataFrame(data)
        if df.empty:
            st.info("열린 알림이 없습니다.")
        else:
            st.dataframe(df, use_container_width=True)
            st.caption("※ 임계치 이하(low_stock) 등 알림이 누적됩니다.")

# =========================================
# STEP1: Stock Ops / Tx History / PO Tabs
# =========================================
tab_stock, tab_tx, tab_po = st.tabs(["Stock Ops", "Tx History", "PO / Receiving"])

# --- A) 수동 입·출고 ---
with tab_stock:
    st.subheader("수동 입·출고 (apply_stock_change)")

    with st.form("stock_form"):
        ingredient_id = st.text_input("ingredient_id (UUID)")
        location_id = st.text_input("location_id (UUID)")
        qty_delta = st.number_input("qty_delta (양수=입고, 음수=출고)", value=0.0, step=1.0, format="%.3f")
        tx_type = st.selectbox("tx_type", ["adjustment","purchase","waste","transfer_in","transfer_out","return"])
        note = st.text_input("note", value="")
        submitted = st.form_submit_button("적용")
    if submitted:
        payload = {
            "ingredient_id": ingredient_id.strip(),
            "location_id": location_id.strip(),
            "qty_delta": float(qty_delta),
            "tx_type": tx_type,
            "note": note.strip() or None
        }
        resp, err = api_post("/stock_change", payload)
        if err:
            st.error(f"실패: {err}")
        else:
            st.success(f"OK. 현재고={resp.get('balance')}")

# --- B) 재고 이력 ---
with tab_tx:
    st.subheader("재고 이력 조회 (inventory_tx)")
    with st.form("tx_form"):
        ing = st.text_input("ingredient_id (옵션, UUID)")
        loc = st.text_input("location_id (옵션, UUID)")
        since = st.text_input("since (옵션, 예: 2025-09-01T00:00:00)")
        limit = st.number_input("limit", min_value=1, max_value=500, value=50, step=1)
        submitted = st.form_submit_button("조회")
    params = {}
    if ing.strip(): params["ingredient_id"] = ing.strip()
    if loc.strip(): params["location_id"] = loc.strip()
    if since.strip(): params["since"] = since.strip()
    params["limit"] = int(limit)
    data, err = api_get("/inventory_tx", params=params)
    if err:
        st.error(f"조회 실패: {err}")
    else:
        df = pd.DataFrame(data)
        if df.empty:
            st.info("데이터 없음")
        else:
            st.dataframe(df, use_container_width=True)

# --- C) 발주 / 입고 ---
with tab_po:
    st.subheader("발주 생성 / 품목 추가 / 입고 처리")

    st.markdown("### 1) 발주 생성")
    with st.form("po_create_form"):
        supplier_id = st.text_input("supplier_id (옵션, UUID)")
        order_date = st.date_input("order_date (옵션)")
        expected_date = st.date_input("expected_date (옵션)")
        note = st.text_input("note", value="")
        submitted_po = st.form_submit_button("발주 생성")
    if submitted_po:
        payload = {
            "supplier_id": supplier_id.strip() or None,
            "order_date": str(order_date) if order_date else None,
            "expected_date": str(expected_date) if expected_date else None,
            "note": note.strip() or None
        }
        resp, err = api_post("/purchase_orders", payload)
        if err:
            st.error(f"발주 생성 실패: {err}")
        else:
            st.success(f"발주 생성 완료. PO ID = {resp.get('id')}  (status={resp.get('status')})")

    st.markdown("### 2) 발주 품목 추가 (라인)")
    with st.form("po_item_form"):
        po_id = st.text_input("purchase_order_id (UUID)")
        ingredient_id2 = st.text_input("ingredient_id (UUID)")
        qty_ordered = st.number_input("qty_ordered", min_value=0.0, value=0.0, step=1.0)
        unit_cost = st.number_input("unit_cost", min_value=0.0, value=0.0, step=0.1)
        submitted_item = st.form_submit_button("라인 추가")
    if submitted_item:
        payload = {
            "purchase_order_id": po_id.strip(),
            "ingredient_id": ingredient_id2.strip(),
            "qty_ordered": float(qty_ordered),
            "unit_cost": float(unit_cost)
        }
        resp, err = api_post("/po_items", payload)
        if err:
            st.error(f"라인 추가 실패: {err}")
        else:
            st.success(f"라인 추가 완료. item_id={resp.get('id')}")

    st.markdown("### 3) 입고 처리 (여러 품목)")
    with st.form("po_recv_form"):
        po_id2 = st.text_input("purchase_order_id (UUID)")
        loc_recv = st.text_input("location_id (UUID)")
        items_json = st.text_area(
            "items JSON",
            value='[{"ingredient_id":"INGREDIENT-UUID-1","qty_received":10}]',
            height=120
        )
        submitted_recv = st.form_submit_button("입고")
    if submitted_recv:
        try:
            items = json.loads(items_json)
            payload = {
                "purchase_order_id": po_id2.strip(),
                "location_id": loc_recv.strip(),
                "items": items
            }
            resp, err = api_post(f"/purchase_orders/{po_id2.strip()}/receive", payload)
            if err:
                st.error(f"입고 실패: {err}")
            else:
                st.success(f"입고 완료. count={resp.get('received_count')}, status={resp.get('status')}")
        except Exception as e:
            st.error(f"JSON 파싱 실패: {e}")

# =========================================
# STEP2: Menu & Recipes / Suppliers
# =========================================
tab_menu, tab_suppliers = st.tabs(["Menu & Recipes", "Suppliers"])

# ---- 공용 헬퍼(옵션 목록) ----
def opt_categories(cat_type="menu"):
    d, e = api_get("/categories", params={"cat_type": cat_type})
    return normalize_name_id_list(d)

def opt_locations():
    d, e = api_get("/ref/locations")
    return normalize_name_id_list(d)

def opt_ingredients():
    d, e = api_get("/ref/ingredients")
    return normalize_name_id_list(d)

def opt_menu_items():
    d, e = api_get("/menu_items", params={"active_only": True})
    return normalize_name_id_list(d)

# ===================== 메뉴/레시피 섹션 =====================

# 1) 메뉴 아이템 로드
menu_items_raw, _ = api_get("/menu_items", params={"active_only": True})
menu_items = as_list(menu_items_raw)

# 2) "보여줄 라벨(name) → 내부값(id)" 매핑
menu_map = {
    m.get("name"): m.get("id")
    for m in menu_items
    if isinstance(m, dict) and m.get("name") and m.get("id")
}

# 3) 선택 UI: 화면엔 이름, 내부 값은 id로 사용
menu_name = st.selectbox("메뉴 선택", ["(선택)"] + list(menu_map.keys()))

# 4) 메뉴가 선택되면 반드시 ID로 /recipes 호출
recipes = []
if menu_name != "(선택)":
    menu_id = menu_map[menu_name]
    recipes_raw, err = api_get("/recipes", params={"menu_item_id": str(menu_id)})
    if err:
        st.error(f"레시피 조회 실패: {err}")
    else:
        recipes = as_list(recipes_raw)

# 5) 레시피 표시 (예시)
if menu_name != "(선택)":
    st.write(f"**선택한 메뉴:** {menu_name}")
    if not recipes:
        st.info("등록된 레시피가 없습니다.")
    else:
        for r in recipes:
            ing_name = r.get("ingredient_name", r.get("ingredient_id", ""))
            qty = r.get("qty_required") or r.get("qty") or ""
            unit = r.get("unit_name", r.get("unit_id", ""))
            st.write(f"- {ing_name}: {qty} {unit}")

# ---- 공급사 ----
with tab_suppliers:
    st.subheader("공급사 목록")
    sup, e = api_get("/suppliers", params={"active_only": False})
    if e: st.error(e); sup = []
    df_sup = pd.DataFrame(sup)
    st.dataframe(df_sup if not df_sup.empty else pd.DataFrame([{"info":"공급사 없음"}]), use_container_width=True)

    st.markdown("### 공급사 생성")
    with st.form("sup_create"):
        s_name = st.text_input("이름")
        s_contact = st.text_input("담당자")
        s_phone = st.text_input("전화")
        s_email = st.text_input("이메일")
        s_addr = st.text_input("주소")
        s_sub = st.form_submit_button("생성")
    if s_sub:
        payload = {
            "name": s_name, "contact": s_contact or None, "phone": s_phone or None,
            "email": s_email or None, "address": s_addr or None, "is_active": True
        }
        resp, e2 = api_post("/suppliers", payload)
        if e2: st.error(e2)
        else: st.success(f"생성 완료: {resp['id']}")

    st.markdown("### 공급사 비활성화")
    if not df_sup.empty:
        with st.form("sup_deact"):
            opts = {f"{r['name']} ({r['id']})": r["id"] for _, r in df_sup.iterrows()}
            sel = st.selectbox("대상 선택", options=list(opts.keys()))
            subx = st.form_submit_button("비활성화")
        if subx and sel:
            sid = opts[sel]
            resp, e3 = api_post(f"/suppliers/{sid}/deactivate", {})
            if e3: st.error(e3)
            else: st.success("비활성화 완료")
