# import os
# import json
# from uuid import UUID

# import streamlit as st
# import pandas as pd
# import requests
# from dotenv import load_dotenv
# # -----------------------------
# # 헬퍼 함수: 리스트 정규화
# # -----------------------------
# def as_list(value):
#     """단일 값이 들어와도 항상 리스트로 변환"""
#     if value is None:
#         return []
#     if isinstance(value, list):
#         return value
#     return [value]

# # -----------------------------
# # 방어적 정규화 헬퍼
# # -----------------------------
# def _as_list(x):
#     if x is None:
#         return []
#     if isinstance(x, list):
#         return x
#     if isinstance(x, dict):
#         # 흔한 컨테이너 키 우선
#         for k in ("data", "rows", "items", "result", "results"):
#             v = x.get(k)
#             if isinstance(v, list):
#                 return v
#         # 단일 객체일 수도 있음
#         return [x]
#     # 그 외(문자열 등) 단일값은 리스트로 감싸기
#     return [x]

# def build_ref_map(refs, name_keys=("name",), id_keys=("id",)):
#     """
#     refs: list[dict] | list[list|tuple] | list[str] | dict 컨테이너/단일객체 등
#     name_keys/id_keys: 우선순위 후보 키 튜플
#     """
#     out = {}
#     for obj in _as_list(refs):
#         if isinstance(obj, dict):
#             nk = next((k for k in name_keys if k in obj), None)
#             ik = next((k for k in id_keys if k in obj), None)
#             if nk and ik:
#                 out[str(obj[nk])] = str(obj[ik])
#         elif isinstance(obj, (list, tuple)) and len(obj) >= 2:
#             # [name, id] 또는 (name, id) 형태로 가정
#             out[str(obj[0])] = str(obj[1])
#         elif isinstance(obj, str):
#             # 문자열만 온 경우: 키=값 동일 매핑
#             out[obj] = obj
#     return out



# # -----------------------------
# # 환경설정
# # -----------------------------
# load_dotenv()
# API = os.getenv("API_URL", "http://127.0.0.1:8000")

# st.set_page_config(page_title="Cafe Inventory", layout="wide")
# st.title("☕ Cafe Inventory Dashboard")

# # -----------------------------
# # 헬퍼
# # -----------------------------
# def api_get(path: str, params: dict | None = None, timeout: int = 10):
#     try:
#         r = requests.get(f"{API}{path}", params=params, timeout=timeout)
#         r.raise_for_status()
#         return r.json(), None
#     except Exception as e:
#         return None, str(e)

# def api_post(path: str, payload: dict, timeout: int = 15):
#     try:
#         r = requests.post(f"{API}{path}", json=payload, timeout=timeout)
#         if r.status_code == 200:
#             return r.json(), None
#         # FastAPI 에러 통일 처리
#         try:
#             detail = r.json().get("detail", r.text)
#         except Exception:
#             detail = r.text
#         return None, f"{r.status_code} {detail}"
#     except Exception as e:
#         return None, str(e)

# def safe_uuid(s: str) -> str | None:
#     try:
#         return str(UUID(s))
#     except Exception:
#         return None

# def normalize_name_id_list(
#     raw,
#     name_keys=("name", "category_name", "label", "title"),
#     id_keys=("id", "category_id", "uuid", "value"),
# ):
#     """
#     다양한 응답(raw)을 [{name,id}, ...] 로 통일
#     허용:
#       - [{"id": "...", "name": "카테고리"}]
#       - [{"category_id": "...", "category_name": "..."}]
#       - {"data": [...]}, {"items": [...]}, {"categories": [...]}, {"results": [...]}
#       - 기타 키들: label/title, uuid/value 등
#     """
#     # dict 래핑이면 내부 list로 파고들기
#     if isinstance(raw, dict):
#         for key in ("data", "items", "categories", "results"):
#             if isinstance(raw.get(key), list):
#                 raw = raw[key]
#                 break

#     out = []
#     if not isinstance(raw, list):
#         return out

#     for item in raw:
#         if isinstance(item, dict):
#             name = next((item.get(k) for k in name_keys if item.get(k) is not None), None)
#             _id  = next((item.get(k) for k in id_keys   if item.get(k) is not None), None)
#             if name and _id:
#                 out.append({"name": name, "id": _id})
#         elif isinstance(item, (list, tuple)) and len(item) >= 2:
#             out.append({"name": str(item[0]), "id": str(item[1])})
#     return out

# # -----------------------------
# # 레이아웃
# # -----------------------------
# tab_health, tab_inventory, tab_sale, tab_alerts = st.tabs(
#     ["Health", "Inventory", "Make Sale", "Alerts"]
# )

# # -----------------------------
# # 1) Health
# # -----------------------------
# with tab_health:
#     st.subheader("API / DB 상태")
#     data, err = api_get("/health")
#     col1, col2 = st.columns([1, 2])
#     with col1:
#         if err:
#             st.error(f"Health 체크 실패: {err}")
#         else:
#             ok = data.get("ok", False)
#             db_ok = data.get("db", None)
#             if ok:
#                 st.success("✅ API 서버 OK")
#             else:
#                 st.error("❌ API 서버 오류")
#             if db_ok is None:
#                 st.info("DB 핑 정보는 비활성화되어 있습니다 (선택 기능).")
#             elif db_ok:
#                 st.success("✅ DB 연결 OK")
#             else:
#                 st.error("❌ DB 연결 실패")
#     with col2:
#         st.code(json.dumps(data if data else {"error": err}, indent=2), language="json")
#     st.caption(f"API_URL = {API}")

# # -----------------------------
# # 2) Inventory
# # -----------------------------
# with tab_inventory:
#     st.subheader("현재고 조회")
#     with st.form("inv_form"):
#         location_id = st.text_input("location_id (옵션, 비우면 전체)", value="")
#         submitted = st.form_submit_button("조회")
#     params = {}
#     if location_id.strip():
#         uuid_norm = safe_uuid(location_id.strip())
#         if not uuid_norm:
#             st.error("location_id가 UUID 형식이 아닙니다.")
#         else:
#             params["location_id"] = uuid_norm
#     data, err = api_get("/inventory", params=params if params else None)
#     if err:
#         st.error(f"Inventory 호출 실패: {err}")
#     else:
#         df = pd.DataFrame(data)
#         if df.empty:
#             st.info("데이터가 없습니다.")
#         else:
#             st.dataframe(df, use_container_width=True)
#             st.caption("※ inventory 스키마: ingredient_id, location_id, qty_on_hand")

# # -----------------------------
# # 3) Make Sale (레시피 자동 차감)
# # -----------------------------
# with tab_sale:
#     st.subheader("판매 등록 (트리거로 재고 자동 차감)")

#     with st.expander("📌 사용 팁", expanded=False):
#         st.markdown(
#             """
#             - `location_id`는 **가능하면 입력**하세요. (메뉴의 `default_location_id`가 없으면 필수)
#             - `menu_item_id`는 메뉴 UUID입니다.
#             - 레시피(`recipes`)에 정의된 원재료가 판매수량 × 필요량 만큼 자동 차감됩니다.
#             - 재고가 부족하면 **409 / INSUFFICIENT_STOCK** 에러가 납니다.
#             """
#         )

#     # 여러 라인 입력 상태 초기화
#     if "sale_lines" not in st.session_state:
#         st.session_state.sale_lines = [
#             {"menu_item_id": "", "qty": 1.0, "unit_price": 4500.0, "discount": 0.0}
#         ]

#     def add_line():
#         st.session_state.sale_lines.append(
#             {"menu_item_id": "", "qty": 1.0, "unit_price": 4500.0, "discount": 0.0}
#         )

#     def clear_lines():
#         st.session_state.sale_lines = [
#             {"menu_item_id": "", "qty": 1.0, "unit_price": 4500.0, "discount": 0.0}
#         ]

#     # 폼 바깥 버튼들
#     b1, b2 = st.columns(2)
#     if b1.button("➕ 라인 추가", use_container_width=True):
#         add_line()
#     if b2.button("🧹 라인 초기화", use_container_width=True):
#         clear_lines()

#     # 폼 내부
#     with st.form("sale_form", clear_on_submit=False):
#         colA, colB = st.columns([1, 1])
#         with colA:
#             location_id_in = st.text_input("location_id (권장, UUID)", value="")
#             channel = st.text_input("channel", value="POS")
#         with colB:
#             st.write("")

#         for idx, line in enumerate(st.session_state.sale_lines, start=1):
#             st.markdown(f"**라인 {idx}**")
#             l1, l2, l3, l4 = st.columns([2, 1, 1, 1])
#             line["menu_item_id"] = l1.text_input("menu_item_id (UUID)", key=f"mid_{idx}", value=line["menu_item_id"])
#             line["qty"] = l2.number_input("qty", min_value=0.0, step=1.0, value=float(line["qty"]), key=f"qty_{idx}")
#             line["unit_price"] = l3.number_input("unit_price", min_value=0.0, step=100.0, value=float(line["unit_price"]), key=f"price_{idx}")
#             line["discount"] = l4.number_input("discount", min_value=0.0, step=100.0, value=float(line["discount"]), key=f"disc_{idx}")
#             st.divider()

#         submitted = st.form_submit_button("🧾 판매 등록", type="primary")

#     if submitted:
#         items = []
#         all_ok = True
#         for line in st.session_state.sale_lines:
#             mid = safe_uuid(line["menu_item_id"].strip())
#             if not mid:
#                 st.error("menu_item_id가 UUID 형식이 아닙니다.")
#                 all_ok = False
#                 break
#             if float(line["qty"]) <= 0:
#                 st.error("qty는 1 이상이어야 합니다.")
#                 all_ok = False
#                 break
#             items.append(
#                 {
#                     "menu_item_id": mid,
#                     "qty": float(line["qty"]),
#                     "unit_price": float(line["unit_price"]),
#                     "discount": float(line["discount"]),
#                 }
#             )

#         payload = {"items": items, "channel": channel}
#         if location_id_in.strip():
#             loc_norm = safe_uuid(location_id_in.strip())
#             if not loc_norm:
#                 st.error("location_id가 UUID 형식이 아닙니다.")
#                 all_ok = False
#             else:
#                 payload["location_id"] = loc_norm

#         if all_ok:
#             resp, err = api_post("/sales", payload)
#             if err:
#                 if "INSUFFICIENT_STOCK" in err:
#                     st.error("❌ 재고 부족(INSUFFICIENT_STOCK)")
#                 else:
#                     st.error(f"❌ 판매 등록 실패: {err}")
#             else:
#                 st.success(f"✅ 판매 등록 완료! sale_id={resp.get('sale_id')}, total_amount={resp.get('total_amount')}")
#                 st.balloons()

# # -----------------------------
# # 4) Alerts
# # -----------------------------
# with tab_alerts:
#     st.subheader("미해제 알림")
#     data, err = api_get("/alerts")
#     if err:
#         st.error(f"Alerts 호출 실패: {err}")
#     else:
#         df = pd.DataFrame(data)
#         if df.empty:
#             st.info("열린 알림이 없습니다.")
#         else:
#             st.dataframe(df, use_container_width=True)
#             st.caption("※ 임계치 이하(low_stock) 등 알림이 누적됩니다.")

# # =========================================
# # STEP1: Stock Ops / Tx History / PO Tabs
# # =========================================
# tab_stock, tab_tx, tab_po = st.tabs(["Stock Ops", "Tx History", "PO / Receiving"])

# # --- A) 수동 입·출고 ---
# with tab_stock:
#     st.subheader("수동 입·출고 (apply_stock_change)")

#     with st.form("stock_form"):
#         ingredient_id = st.text_input("ingredient_id (UUID)")
#         location_id = st.text_input("location_id (UUID)")
#         qty_delta = st.number_input("qty_delta (양수=입고, 음수=출고)", value=0.0, step=1.0, format="%.3f")
#         tx_type = st.selectbox("tx_type", ["adjustment","purchase","waste","transfer_in","transfer_out","return"])
#         note = st.text_input("note", value="")
#         submitted = st.form_submit_button("적용")
#     if submitted:
#         payload = {
#             "ingredient_id": ingredient_id.strip(),
#             "location_id": location_id.strip(),
#             "qty_delta": float(qty_delta),
#             "tx_type": tx_type,
#             "note": note.strip() or None
#         }
#         resp, err = api_post("/stock_change", payload)
#         if err:
#             st.error(f"실패: {err}")
#         else:
#             st.success(f"OK. 현재고={resp.get('balance')}")

# # --- B) 재고 이력 ---
# with tab_tx:
#     st.subheader("재고 이력 조회 (inventory_tx)")
#     with st.form("tx_form"):
#         ing = st.text_input("ingredient_id (옵션, UUID)")
#         loc = st.text_input("location_id (옵션, UUID)")
#         since = st.text_input("since (옵션, 예: 2025-09-01T00:00:00)")
#         limit = st.number_input("limit", min_value=1, max_value=500, value=50, step=1)
#         submitted = st.form_submit_button("조회")
#     params = {}
#     if ing.strip(): params["ingredient_id"] = ing.strip()
#     if loc.strip(): params["location_id"] = loc.strip()
#     if since.strip(): params["since"] = since.strip()
#     params["limit"] = int(limit)
#     data, err = api_get("/inventory_tx", params=params)
#     if err:
#         st.error(f"조회 실패: {err}")
#     else:
#         df = pd.DataFrame(data)
#         if df.empty:
#             st.info("데이터 없음")
#         else:
#             st.dataframe(df, use_container_width=True)

# # --- C) 발주 / 입고 ---
# with tab_po:
#     st.subheader("발주 생성 / 품목 추가 / 입고 처리")

#     st.markdown("### 1) 발주 생성")
#     with st.form("po_create_form"):
#         supplier_id = st.text_input("supplier_id (옵션, UUID)")
#         order_date = st.date_input("order_date (옵션)")
#         expected_date = st.date_input("expected_date (옵션)")
#         note = st.text_input("note", value="")
#         submitted_po = st.form_submit_button("발주 생성")
#     if submitted_po:
#         payload = {
#             "supplier_id": supplier_id.strip() or None,
#             "order_date": str(order_date) if order_date else None,
#             "expected_date": str(expected_date) if expected_date else None,
#             "note": note.strip() or None
#         }
#         resp, err = api_post("/purchase_orders", payload)
#         if err:
#             st.error(f"발주 생성 실패: {err}")
#         else:
#             st.success(f"발주 생성 완료. PO ID = {resp.get('id')}  (status={resp.get('status')})")

#     st.markdown("### 2) 발주 품목 추가 (라인)")
#     with st.form("po_item_form"):
#         po_id = st.text_input("purchase_order_id (UUID)")
#         ingredient_id2 = st.text_input("ingredient_id (UUID)")
#         qty_ordered = st.number_input("qty_ordered", min_value=0.0, value=0.0, step=1.0)
#         unit_cost = st.number_input("unit_cost", min_value=0.0, value=0.0, step=100.0)
#         submitted_item = st.form_submit_button("라인 추가")
#     if submitted_item:
#         payload = {
#             "purchase_order_id": po_id.strip(),
#             "ingredient_id": ingredient_id2.strip(),
#             "qty_ordered": float(qty_ordered),
#             "unit_cost": float(unit_cost)
#         }
#         resp, err = api_post("/po_items", payload)
#         if err:
#             st.error(f"라인 추가 실패: {err}")
#         else:
#             st.success(f"라인 추가 완료. item_id={resp.get('id')}")

#     st.markdown("### 3) 입고 처리 (여러 품목)")
#     with st.form("po_recv_form"):
#         po_id2 = st.text_input("purchase_order_id (UUID)")
#         loc_recv = st.text_input("location_id (UUID)")
#         items_json = st.text_area(
#             "items JSON",
#             value='[{"ingredient_id":"INGREDIENT-UUID-1","qty_received":10}]',
#             height=120
#         )
#         submitted_recv = st.form_submit_button("입고")
#     if submitted_recv:
#         try:
#             items = json.loads(items_json)
#             payload = {
#                 "purchase_order_id": po_id2.strip(),
#                 "location_id": loc_recv.strip(),
#                 "items": items
#             }
#             resp, err = api_post(f"/purchase_orders/{po_id2.strip()}/receive", payload)
#             if err:
#                 st.error(f"입고 실패: {err}")
#             else:
#                 st.success(f"입고 완료. count={resp.get('received_count')}, status={resp.get('status')}")
#         except Exception as e:
#             st.error(f"JSON 파싱 실패: {e}")

# # =========================================
# # STEP2: Menu & Recipes / Suppliers
# # =========================================
# tab_menu, tab_suppliers = st.tabs(["Menu & Recipes", "Suppliers"])

# # ---- 공용 헬퍼(옵션 목록) ----
# def opt_categories(cat_type="menu"):
#     d, e = api_get("/categories", params={"cat_type": cat_type})
#     return normalize_name_id_list(d)

# def opt_locations():
#     d, e = api_get("/ref/locations")
#     return normalize_name_id_list(d)

# def opt_ingredients():
#     d, e = api_get("/ref/ingredients")
#     return normalize_name_id_list(d)

# def opt_menu_items():
#     d, e = api_get("/menu_items", params={"active_only": True})
#     return normalize_name_id_list(d)

# # ===================== 메뉴/레시피 섹션 교체 시작 =====================
# from urllib.parse import quote

# # 1) 메뉴 아이템 로드
# menu_items_raw, _ = api_get("/menu_items?active_only=True")
# menu_items = as_list(menu_items_raw)  # 앞서 추가한 정규화 헬퍼 사용 (없으면 리스트 그대로 쓰세요)

# # 2) "보여줄 라벨(name) → 내부값(id)" 매핑
# menu_map = {
#     m.get("name"): m.get("id")
#     for m in menu_items
#     if isinstance(m, dict) and m.get("name") and m.get("id")
# }

# # 3) 선택 UI: 화면엔 이름, 내부 값은 id로 사용
# menu_name = st.selectbox("메뉴 선택", ["(선택)"] + list(menu_map.keys()))

# # 4) 메뉴가 선택되면 반드시 ID로 /recipes 호출
# recipes = []
# if menu_name != "(선택)":
#     menu_id = menu_map[menu_name]
#     recipes_raw, err = api_get(f"/recipes?menu_item_id={quote(str(menu_id))}")
#     if err:
#         st.error(f"레시피 조회 실패: {err}")
#     else:
#         # 응답이 {"data":[...]} 형태일 수도 있으니 정규화
#         recipes = as_list(recipes_raw)

# # 5) 레시피 표시 (예시)
# if menu_name != "(선택)":
#     st.write(f"**선택한 메뉴:** {menu_name}")
#     if not recipes:
#         st.info("등록된 레시피가 없습니다.")
#     else:
#         # 원하는 UI로 바꾸세요
#         for r in recipes:
#             ing_name = r.get("ingredient_name", r.get("ingredient_id", ""))
#             qty = r.get("qty", "")
#             unit = r.get("unit_name", r.get("unit_id", ""))
#             st.write(f"- {ing_name}: {qty} {unit}")
# # ===================== 메뉴/레시피 섹션 교체 끝 =====================


# # ---- 공급사 ----
# with tab_suppliers:
#     st.subheader("공급사 목록")
#     sup, e = api_get("/suppliers", params={"active_only": False})
#     if e: st.error(e); sup = []
#     df_sup = pd.DataFrame(sup)
#     st.dataframe(df_sup if not df_sup.empty else pd.DataFrame([{"info":"공급사 없음"}]), use_container_width=True)

#     st.markdown("### 공급사 생성")
#     with st.form("sup_create"):
#         s_name = st.text_input("이름")
#         s_contact = st.text_input("담당자")
#         s_phone = st.text_input("전화")
#         s_email = st.text_input("이메일")
#         s_addr = st.text_input("주소")
#         s_sub = st.form_submit_button("생성")
#     if s_sub:
#         payload = {
#             "name": s_name, "contact": s_contact or None, "phone": s_phone or None,
#             "email": s_email or None, "address": s_addr or None, "is_active": True
#         }
#         resp, e2 = api_post("/suppliers", payload)
#         if e2: st.error(e2)
#         else: st.success(f"생성 완료: {resp['id']}")

#     st.markdown("### 공급사 비활성화")
#     if not df_sup.empty:
#         with st.form("sup_deact"):
#             opts = {f"{r['name']} ({r['id']})": r["id"] for _, r in df_sup.iterrows()}
#             sel = st.selectbox("대상 선택", options=list(opts.keys()))
#             subx = st.form_submit_button("비활성화")
#         if subx and sel:
#             sid = opts[sel]
#             resp, e3 = api_post(f"/suppliers/{sid}/deactivate", {})
#             if e3: st.error(e3)
#             else: st.success("비활성화 완료")

# # =========================================
# # STEP3: Transfers & Audit Logs
# # =========================================
# tab_tr, tab_audit = st.tabs(["Transfers", "Audit Logs"])

# # -------- Transfers --------
# with tab_tr:
#     st.subheader("이동(Transfer) 등록 / 진행")

#     st.markdown("### 1) 이동 생성")
#     with st.form("tr_create"):
#         from_loc = st.text_input("from_location_id (UUID, 옵션)")
#         to_loc = st.text_input("to_location_id (UUID, 옵션)")
#         status = st.selectbox("초기 상태", ["draft","shipped","received","canceled"], index=0)
#         sub_trc = st.form_submit_button("생성")
#     if sub_trc:
#         payload = {
#             "from_location_id": from_loc.strip() or None,
#             "to_location_id": to_loc.strip() or None,
#             "status": status
#         }
#         resp, err = api_post("/transfers", payload)
#         if err: st.error(err)
#         else: st.success(f"생성 완료: {resp.get('id')} (status={resp.get('status')})")

#     st.markdown("### 2) 이동 품목 추가")
#     with st.form("tr_item_add"):
#         tr_id = st.text_input("transfer_id (UUID)")
#         ing_id = st.text_input("ingredient_id (UUID)")
#         qty = st.number_input("qty", min_value=0.0, value=1.0, step=1.0)
#         sub_tri = st.form_submit_button("라인 추가")
#     if sub_tri:
#         payload = {"transfer_id": tr_id.strip(), "ingredient_id": ing_id.strip(), "qty": float(qty)}
#         resp, err = api_post("/transfer_items", payload)
#         if err: st.error(err)
#         else: st.success(f"라인 추가 완료: {resp.get('id')}")

#     st.markdown("### 3) Ship / Receive")
#     with st.form("tr_ship"):
#         tr_id_s = st.text_input("transfer_id (UUID) - Ship")
#         sub_ts = st.form_submit_button("📦 Ship (from에서 차감)")
#     if sub_ts:
#         resp, err = api_post(f"/transfers/{tr_id_s.strip()}/ship", {"transfer_id": tr_id_s.strip()})
#         if err: st.error(err)
#         else: st.success("Ship 완료")

#     with st.form("tr_recv"):
#         tr_id_r = st.text_input("transfer_id (UUID) - Receive")
#         sub_tr = st.form_submit_button("📥 Receive (to에 입고)")
#     if sub_tr:
#         resp, err = api_post(f"/transfers/{tr_id_r.strip()}/receive", {"transfer_id": tr_id_r.strip()})
#         if err: st.error(err)
#         else: st.success("Receive 완료")

#     st.markdown("### 4) 이동 목록 / 라인 조회")
#     with st.form("tr_list"):
#         stx = st.selectbox("상태 필터", ["(전체)","draft","shipped","received","canceled"])
#         limit = st.number_input("limit", min_value=1, max_value=500, value=100, step=1)
#         sub_tl = st.form_submit_button("조회")
#     if sub_tl:
#         params = {"limit": int(limit)}
#         if stx != "(전체)":
#             params["status"] = stx
#         data, err = api_get("/transfers", params=params)
#         if err: st.error(err); data=[]
#         df = pd.DataFrame(data)
#         st.dataframe(df if not df.empty else pd.DataFrame([{"info":"데이터 없음"}]), use_container_width=True)

#     with st.form("tr_items_list"):
#         trid = st.text_input("transfer_id (UUID) - 라인 조회")
#         sub_tli = st.form_submit_button("라인 조회")
#     if sub_tli and trid.strip():
#         data, err = api_get("/transfer_items", params={"transfer_id": trid.strip()})
#         if err: st.error(err); data=[]
#         df = pd.DataFrame(data)
#         st.dataframe(df if not df.empty else pd.DataFrame([{"info":"라인 없음"}]), use_container_width=True)

# # -------- Audit Logs --------
# with tab_audit:
#     st.subheader("감사 로그 조회 (audit_logs)")
#     with st.form("audit_form"):
#         tname = st.text_input("table_name (옵션, 예: 'inventory' / 'sale_items')")
#         since = st.text_input("since (옵션, 예: 2025-09-01T00:00:00)")
#         limit = st.number_input("limit", min_value=1, max_value=500, value=100, step=1)
#         sub_al = st.form_submit_button("조회")
#     if sub_al:
#         params = {"limit": int(limit)}
#         if tname.strip(): params["table_name"] = tname.strip()
#         if since.strip(): params["since"] = since.strip()
#         data, err = api_get("/audit_logs", params=params)
#         if err: st.error(err); data=[]
#         df = pd.DataFrame(data)
#         st.dataframe(df if not df.empty else pd.DataFrame([{"info":"로그 없음"}]), use_container_width=True)

# # =========================
# # 등록 탭: 카테고리 / 품목 / 입고
# # =========================
# tab_reg_cat, tab_reg_item, tab_receipt = st.tabs(["카테고리 등록", "품목 등록", "입고 등록"])

# # --- 카테고리 등록 ---
# with tab_reg_cat:
#     st.subheader("카테고리 등록")
#     with st.form("cat_form"):
#         cat_name = st.text_input("카테고리명", "")
#         cat_type = st.selectbox("타입", ["ingredient", "menu"], index=0)
#         sub_cat = st.form_submit_button("등록")
#     if sub_cat:
#         if not cat_name.strip():
#             st.warning("카테고리명을 입력하세요.")
#         else:
#             resp, err = api_post("/categories", {"name": cat_name.strip(), "type": cat_type})
#             if err: st.error(err)
#             else: st.success(f"등록됨: {resp['name']} ({resp['type']})")

#     st.divider()
#     st.caption("기존 카테고리")
#     data, err = api_get("/categories")
#     if err: st.error(err); data=[]
#     st.dataframe(pd.DataFrame(data), use_container_width=True)

# # --- 품목(원재료) 등록 ---
# with tab_reg_item:
#     st.subheader("품목(원재료) 등록")

#     # 참조 로드
#     units_raw, _ = api_get("/ref/units")
#     cats_raw,  _  = api_get("/categories?type=ingredient")
#     users_raw, _ = api_get("/ref/users")

#     # ✅ 항상 list가 되도록 정규화
#     units = as_list(units_raw)
#     cats  = as_list(cats_raw)
#     users = as_list(users_raw)

#     # ✅ dict만, id가 있는 항목만 안전하게 사용
#     unit_map = {
#         f"{u.get('name', '?')} ({u.get('base', '?')})": u.get("id")
#         for u in units if isinstance(u, dict) and u.get("id") is not None
#     }
#     cat_map  = {
#         c.get("name", "?"): c.get("id")
#         for c in cats if isinstance(c, dict) and c.get("id") is not None
#     }
#     user_map = {
#         u.get("name", "?"): u.get("id")
#         for u in users if isinstance(u, dict) and u.get("id") is not None
#     }

#     with st.form("ing_form"):
#         name = st.text_input("품목명", "")
#         col1, col2 = st.columns(2)
#         with col1:
#             cat_sel = st.selectbox("카테고리", ["(선택안함)"] + list(cat_map.keys()))
#             unit_sel = st.selectbox("단위", list(unit_map.keys()) or ["단위 없음(먼저 등록)"])
#             ss = st.number_input("안전재고 기본값", min_value=0.0, value=0.0, step=1.0)
#         with col2:
#             rp = st.number_input("재주문점 기본값", min_value=0.0, value=0.0, step=1.0)
#             resp_user = st.selectbox("담당자", ["(선택안함)"] + list(user_map.keys()))
#             cost = st.number_input("단가(옵션)", min_value=0.0, value=0.0, step=0.1)
#         desc = st.text_area("설명", "")

#         sub_ing = st.form_submit_button("등록")
#     if sub_ing:
#         if not name.strip():
#             st.warning("품목명을 입력하세요.")
#         elif not unit_map:
#             st.error("단위가 없습니다. 먼저 단위를 등록하세요.")
#         else:
#             payload = {
#                 "name": name.strip(),
#                 "unit_id": unit_map.get(unit_sel),
#                 "category_id": cat_map.get(cat_sel) if cat_sel in cat_map else None,
#                 "description": desc or None,
#                 "safety_stock_default": ss,
#                 "reorder_point_default": rp,
#                 "responsible_user_id": user_map.get(resp_user) if resp_user in user_map else None,
#                 "cost_per_unit": cost,
#             }
#             resp, err = api_post("/ingredients", payload)
#             if err:
#                 st.error(err)
#             else:
#                 st.success(f"등록됨: {resp.get('name', name.strip())} (id={resp.get('id')})")


# # --- 입고 등록 (헤더+아이템) ---
# with tab_receipt:
#     st.subheader("입고 등록")

#     # 참조 로드 (가벼운 /ref/* 사용)
#     locs, _  = api_get("/ref/locations"); locs = locs or []
#     sups, _  = api_get("/ref/suppliers"); sups = sups or []
#     ings, _  = api_get("/ref/ingredients"); ings = ings or []
#     users, _ = api_get("/ref/users"); users = users or []

#     # 다양한 응답 스키마를 커버 (id/name, *_id/*_name 등)
#     loc_map  = build_ref_map(locs,  name_keys=("name","location_name","title"), id_keys=("id","location_id","uuid"))
#     sup_map  = build_ref_map(sups,  name_keys=("name","supplier_name","title"), id_keys=("id","supplier_id","uuid"))
#     ing_map  = build_ref_map(ings,  name_keys=("name","ingredient_name","title"), id_keys=("id","ingredient_id","uuid"))
#     user_map = build_ref_map(users, name_keys=("name","user_name","full_name","title"), id_keys=("id","user_id","uuid"))

#     with st.form("rcp_form", clear_on_submit=True):
#         col1, col2 = st.columns(2)
#         with col1:
#             loc_options = list(loc_map.keys()) if loc_map else ["(위치 없음)"]
#             sup_options = ["(없음)"] + (list(sup_map.keys()) if sup_map else [])
#             loc_sel = st.selectbox("입고 위치", loc_options)
#             sup_sel = st.selectbox("공급사(옵션)", sup_options)
#             note = st.text_input("비고", "")
#         with col2:
#             recv_at = st.text_input("입고일시(ISO, 빈칸=지금)", "")

#         st.markdown("#### 입고 품목")
#         rows = st.number_input("입력 행 수", min_value=1, value=1, step=1)
#         items = []
#         for idx in range(rows):
#             st.write(f"행 {idx+1}")
#             c1, c2, c3, c4, c5 = st.columns([2,1,1.3,1.5,1.5])
#             with c1:
#                 ing_options = list(ing_map.keys()) if ing_map else ["(품목 없음)"]
#                 ing_sel = st.selectbox("품목", ing_options, key=f"ri_ing_{idx}")
#             with c2:
#                 qty = st.number_input("수량", min_value=0.0, value=0.0, step=1.0, key=f"ri_qty_{idx}")
#             with c3:
#                 ucost = st.number_input("단가", min_value=0.0, value=0.0, step=0.1, key=f"ri_uc_{idx}")
#             with c4:
#                 exp = st.text_input("유통기한(YYYY-MM-DD)", value="", key=f"ri_exp_{idx}")
#             with c5:
#                 lot = st.text_input("로트", value="", key=f"ri_lot_{idx}")
#             if ing_sel in ing_map and qty > 0:
#                 items.append({
#                     "ingredient_id": ing_map[ing_sel],
#                     "qty": qty,
#                     "unit_cost": ucost or None,
#                     "expiry_date": exp.strip() or None,
#                     "lot_code": lot.strip() or None
#                 })

#         user_options = ["(없음)"] + (list(user_map.keys()) if user_map else [])
#         created_by = st.selectbox("작성자(옵션)", user_options)
#         sub_rcp = st.form_submit_button("입고 등록")

#     if sub_rcp:
#         if not loc_map:
#             st.error("위치가 없습니다. 먼저 위치를 등록하세요.")
#         elif not items:
#             st.warning("유효한 입고 품목이 없습니다(수량>0 필요).")
#         else:
#             payload = {
#                 "supplier_id": sup_map.get(sup_sel) if sup_sel in sup_map else None,
#                 "location_id": loc_map.get(loc_sel) if loc_sel in loc_map else None,
#                 "received_at": (recv_at.strip() or None),
#                 "note": (note.strip() or None),
#                 "created_by": user_map.get(created_by) if created_by in user_map else None,
#                 "items": items
#             }
#             resp, err = api_post("/receipts", payload)
#             if err:
#                 st.error(err)
#             else:
#                 st.success(f"입고 등록 완료: receipt_id={resp.get('receipt_id')}")
