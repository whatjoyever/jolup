import os, sys
from typing import List, Dict, Any

import streamlit as st

# --- sidebar / client import 경로 보정 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

from sidebar import render_sidebar
from client import api_get, api_post

# -------------------------------
# 페이지 설정 & 커스텀 사이드바
# -------------------------------
st.set_page_config(page_title="레시피 등록", page_icon="📖", layout="wide")
render_sidebar("info")

# -------------------------------
# 글로벌 스타일
# -------------------------------
st.markdown("""
<style>
  .main .block-container {
    max-width: 100%;
    padding-top: 1rem; padding-right: 4rem; padding-left: 4rem; padding-bottom: 1rem;
  }
  div[data-testid="stHorizontalBlock"] { padding-left: 1rem; }
</style>
""", unsafe_allow_html=True)

# -------------------------------
# 유틸 & 참조 데이터 로드
# -------------------------------
@st.cache_data(ttl=60)
def load_categories_menu() -> List[Dict[str, Any]]:
    """메뉴 카테고리 목록 로드"""
    data, err = api_get("/categories", params={"cat_type": "menu"})
    if err or not isinstance(data, list):
        return []
    # 기대 형식: [{"id": "...", "name": "..."}]
    return [r for r in data if isinstance(r, dict) and r.get("id") and r.get("name")]

@st.cache_data(ttl=60)
def load_ingredients() -> List[Dict[str, Any]]:
    """원재료 목록 로드 (표시용: id, name)"""
    data, err = api_get("/ref/ingredients")
    if err:
        # 대체 엔드포인트 시도
        data, err = api_get("/ingredients")
        if err:
            return []
    # 다양한 응답을 허용: [{"id","name"}, ...] or {"data":[...]}
    if isinstance(data, dict):
        for k in ("data", "items", "results"):
            if isinstance(data.get(k), list):
                data = data[k]
                break
    if not isinstance(data, list):
        return []
    out = []
    for item in data:
        if isinstance(item, dict) and item.get("id") and item.get("name"):
            out.append({"id": str(item["id"]), "name": str(item["name"])})
    return out

@st.cache_data(ttl=30)
def load_menu_items() -> List[Dict[str, Any]]:
    """메뉴 목록 로드 (활성 메뉴 기준)"""
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
    # 기대: [{"id","name","category_id","price",...}]
    out = []
    for m in data:
        if isinstance(m, dict) and m.get("id") and m.get("name"):
            out.append({
                "id": str(m["id"]),
                "name": str(m["name"]),
                "category_id": str(m.get("category_id")) if m.get("category_id") else None,
                "price": m.get("price")
            })
    return out

def find_or_create_menu_item(menu_name: str, category_id: str | None, price: int | None) -> str | None:
    """메뉴가 존재하면 id 반환, 없으면 생성 후 id 반환"""
    menus = load_menu_items()
    for m in menus:
        if m["name"] == menu_name:
            return m["id"]

    payload = {
        "name": menu_name,
        "category_id": category_id,
        "price": int(price) if price else 0,
        "is_active": True
    }
    resp, err = api_post("/menu_items", payload)
    if err:
        st.error(f"메뉴 생성 실패: {err}")
        return None
    return str(resp.get("id")) if isinstance(resp, dict) else None

def get_recent_unit_price(ingredient_id: str) -> float:
    """최근 단가 추정: 필요 시 백엔드에 /receipt_items 등 별도 엔드포인트 마련 권장.
       여기선 0 반환(표시용)."""
    return 0.0

# -------------------------------
# 세션 상태 초기화
# -------------------------------
if "recipe_ingredients" not in st.session_state:
    st.session_state.recipe_ingredients = []  # [{"ingredient_id","ingredient_name","qty","unit"}]
if "recipe_options" not in st.session_state:
    st.session_state.recipe_options = []      # UI 표시용 (DB 확장 예정)
if "recipe_menu_price" not in st.session_state:
    st.session_state.recipe_menu_price = 0

# -------------------------------
# 헤더 & 뒤로가기
# -------------------------------
title_col, button_col = st.columns([4, 1])
with title_col:
    st.title("레시피 관리")
    st.caption("메뉴별 레시피를 등록하고 관리합니다. 판매와 동시에 원재료 재고가 자동 차감되도록 DB에 저장합니다.")
with button_col:
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
    if st.button("← 뒤로가기", use_container_width=True, key="back_button"):
        st.switch_page("pages/info.py")

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# -------------------------------
# 참조 데이터
# -------------------------------
categories = load_categories_menu()
ingredients_ref = load_ingredients()
menu_items_ref = load_menu_items()

category_names = ["선택하세요"] + [c["name"] for c in categories]
category_map = {c["name"]: c["id"] for c in categories}  # name -> id
ingredient_options = [f"{x['name']} ({x['id']})" for x in ingredients_ref]

# -------------------------------
# 탭
# -------------------------------
register_tab, list_tab = st.tabs(["레시피 등록/수정", "레시피 목록 조회"])

# ============================================================
# 레시피 등록/수정
# ============================================================
with register_tab:
    st.markdown("#### ② 원재료 추가 및 소모량 입력")
    st.info("레시피에 들어가는 모든 원재료를 추가하고, 1잔 기준 소모량을 입력하세요.")

    # 재료 추가 버튼
    if st.button("➕ 재료 추가", key="add_ingredient_btn", use_container_width=False):
        st.session_state.recipe_ingredients.append({
            "ingredient_id": "",
            "ingredient_name": "",
            "qty": 0.0,
            "unit": "g",
        })
        st.rerun()

    # 재료 리스트 편집
    if len(st.session_state.recipe_ingredients) == 0:
        st.info("재료를 추가하세요.")
    else:
        st.markdown("**재료 목록:**")
        for idx, ing in enumerate(st.session_state.recipe_ingredients):
            c1, c2, c3, c4, c5 = st.columns([3, 2, 1.5, 1.5, 1])
            with c1:
                st.caption("재료 선택")
                if ingredient_options:
                    selected_label = (
                        f"{ing.get('ingredient_name','')} ({ing.get('ingredient_id','')})"
                        if ing.get("ingredient_id") else ingredient_options[0]
                    )
                    try:
                        default_idx = ingredient_options.index(selected_label)
                    except Exception:
                        default_idx = 0
                    sel = st.selectbox(
                        "재료",
                        options=ingredient_options,
                        index=default_idx,
                        key=f"recipe_ing_select_{idx}",
                        label_visibility="collapsed",
                    )
                    sel_idx = ingredient_options.index(sel)
                    sel_ing = ingredients_ref[sel_idx]
                    st.session_state.recipe_ingredients[idx]["ingredient_id"] = sel_ing["id"]
                    st.session_state.recipe_ingredients[idx]["ingredient_name"] = sel_ing["name"]
                else:
                    st.warning("원재료 참조 데이터가 없습니다. 먼저 원재료를 등록하세요.")

            with c2:
                st.caption("소모량")
                qty = st.number_input(
                    "소모량", min_value=0.0, step=0.1,
                    value=float(ing.get("qty", 0.0)),
                    key=f"recipe_ing_qty_{idx}",
                    label_visibility="collapsed"
                )
                st.session_state.recipe_ingredients[idx]["qty"] = qty

            with c3:
                st.caption("단위")
                unit_options = ["g", "ml", "개", "컵", "스푼"]
                current_unit = ing.get("unit", "g")
                uidx = unit_options.index(current_unit) if current_unit in unit_options else 0
                unit = st.selectbox(
                    "단위", options=unit_options, index=uidx,
                    key=f"recipe_ing_unit_{idx}",
                    label_visibility="collapsed"
                )
                st.session_state.recipe_ingredients[idx]["unit"] = unit

            with c4:
                st.caption("최근 단가(참고)")
                price = get_recent_unit_price(ing.get("ingredient_id") or "")
                st.write(f"{int(price):,}원" if price else "정보 없음")

            with c5:
                st.caption("삭제")
                st.markdown("<div style='height: 37px'></div>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"recipe_ing_del_{idx}", use_container_width=True):
                    st.session_state.recipe_ingredients.pop(idx)
                    st.rerun()

    # 원가 추정(참고)
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    st.markdown("#### ④ 예상 원가(참고)")
    total_cost = 0.0
    for ing in st.session_state.recipe_ingredients:
        if ing.get("ingredient_id"):
            unit_price = get_recent_unit_price(ing["ingredient_id"])
            qty = float(ing.get("qty") or 0.0)
            # 단위 변환 로직은 단순화(실사용 시 단위 테이블 매핑 권장)
            cost = (unit_price * qty / 100.0) if ing.get("unit") in ("g", "ml") else (unit_price * qty)
            total_cost += cost
    colc1, colc2 = st.columns([1, 1])
    with colc1:
        st.metric("예상 제조 원가", f"{int(total_cost):,}원")
    with colc2:
        menu_price_preview = st.session_state.get("recipe_menu_price", 0)
        if menu_price_preview > 0:
            margin = menu_price_preview - int(total_cost)
            rate = (margin / menu_price_preview * 100) if menu_price_preview else 0
            st.metric("예상 마진", f"{margin:,}원 ({rate:.1f}%)")

    # 옵션 섹션(표시용)
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    st.markdown("#### ⑥ 옵션 레시피 관리 (선택)")
    st.info("옵션 소모량은 UI에 표시만 합니다. DB 저장 스키마(`/recipe_options`)는 추후 확장.")
    if st.button("➕ 옵션 추가", key="add_option_btn", use_container_width=False):
        st.session_state.recipe_options.append({
            "option_name": "",
            "ingredient_id": "",
            "ingredient_name": "",
            "qty": 0.0,
            "unit": "g"
        })
        st.rerun()
    if len(st.session_state.recipe_options) == 0:
        st.info("옵션을 추가하세요(선택사항).")
    else:
        st.markdown("**옵션 목록:**")
        for i, opt in enumerate(st.session_state.recipe_options):
            o1, o2, o3, o4, o5 = st.columns([2, 2, 1.5, 1, 1])
            with o1:
                st.caption("옵션명")
                st.session_state.recipe_options[i]["option_name"] = st.text_input(
                    "옵션명", value=opt.get("option_name",""),
                    key=f"opt_name_{i}", label_visibility="collapsed"
                )
            with o2:
                st.caption("재료 선택")
                if ingredient_options:
                    selected_label = (
                        f"{opt.get('ingredient_name','')} ({opt.get('ingredient_id','')})"
                        if opt.get("ingredient_id") else ingredient_options[0]
                    )
                    try:
                        default_idx = ingredient_options.index(selected_label)
                    except Exception:
                        default_idx = 0
                    sel = st.selectbox(
                        "재료",
                        options=ingredient_options,
                        index=default_idx,
                        key=f"opt_ing_{i}", label_visibility="collapsed"
                    )
                    sel_idx = ingredient_options.index(sel)
                    ing_ref = ingredients_ref[sel_idx]
                    st.session_state.recipe_options[i]["ingredient_id"] = ing_ref["id"]
                    st.session_state.recipe_options[i]["ingredient_name"] = ing_ref["name"]
                else:
                    st.warning("원재료 참조 데이터가 없습니다.")
            with o3:
                st.caption("추가 소모량")
                st.session_state.recipe_options[i]["qty"] = st.number_input(
                    "추가 소모량", min_value=0.0, step=0.1,
                    value=float(opt.get("qty", 0.0)),
                    key=f"opt_qty_{i}", label_visibility="collapsed"
                )
            with o4:
                st.caption("단위")
                unit_options = ["g","ml","개","컵","스푼"]
                cu = opt.get("unit","g")
                ui = unit_options.index(cu) if cu in unit_options else 0
                st.session_state.recipe_options[i]["unit"] = st.selectbox(
                    "단위", options=unit_options, index=ui,
                    key=f"opt_unit_{i}", label_visibility="collapsed"
                )
            with o5:
                st.caption("삭제")
                st.markdown("<div style='height: 37px'></div>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"opt_del_{i}", use_container_width=True):
                    st.session_state.recipe_options.pop(i)
                    st.rerun()

    # -------------------------------
    # 등록/수정 폼
    # -------------------------------
    with st.form("recipe_register_form", clear_on_submit=False):
        st.markdown("#### ① 레시피 기본 정보 입력")

        # 메뉴명 입력(또는 존재 메뉴 선택)
        colm1, colm2 = st.columns([2, 2])
        with colm1:
            menu_name = st.text_input(
                "메뉴명 (필수)", key="recipe_menu_name",
                placeholder="예: 아이스 아메리카노 (기존 메뉴명과 동일하면 자동 매칭)"
            )
        with colm2:
            # 카테고리 선택
            cat_idx = 0
            category = st.selectbox(
                "카테고리", options=category_names, index=cat_idx, key="recipe_category_select"
            )

        # 판매 가격
        price_str = st.text_input("판매 가격 (원)", key="recipe_price_input", placeholder="예: 4500")
        if price_str:
            price_clean = ''.join(filter(str.isdigit, price_str.replace(",", "")))
            menu_price = int(price_clean) if price_clean else 0
        else:
            menu_price = 0
        st.session_state.recipe_menu_price = menu_price

        submit_col1, submit_col2 = st.columns([1, 1])
        with submit_col1:
            submitted = st.form_submit_button("레시피 저장", use_container_width=True, type="primary")
        with submit_col2:
            cancel = st.form_submit_button("입력 초기화", use_container_width=True)

        if cancel:
            st.session_state.recipe_ingredients = []
            st.session_state.recipe_options = []
            st.session_state.recipe_menu_price = 0
            st.rerun()

        if submitted:
            # 검증
            if not menu_name or not menu_name.strip():
                st.warning("메뉴명을 입력하세요.")
                st.stop()
            if len(st.session_state.recipe_ingredients) == 0:
                st.warning("최소 1개 이상의 재료를 추가하세요.")
                st.stop()
            all_valid = all(bool(x.get("ingredient_id")) for x in st.session_state.recipe_ingredients)
            if not all_valid:
                st.warning("모든 재료를 선택하세요.")
                st.stop()

            # 메뉴 찾기/생성
            sel_cat_id = category_map.get(category) if category and category != "선택하세요" else None
            menu_id = find_or_create_menu_item(menu_name.strip(), sel_cat_id, menu_price)
            if not menu_id:
                st.stop()

            # /recipes 저장(덮어쓰기 방식: 동일 menu_item_id 기존 행 삭제 후 재삽입을 백엔드가 수행)
            ingredients_payload = []
            for ing in st.session_state.recipe_ingredients:
                ingredients_payload.append({
                    "ingredient_id": ing["ingredient_id"],
                    "qty_required": float(ing.get("qty") or 0.0)
                })
            payload = {
                "menu_item_id": menu_id,
                "ingredients": ingredients_payload
            }
            resp, err = api_post("/recipes", payload)
            if err:
                st.error(f"레시피 저장 실패: {err}")
                st.stop()

            # 입력 상태 정리
            st.session_state.recipe_ingredients = []
            st.session_state.recipe_options = []
            st.session_state.recipe_menu_price = 0
            st.success(f"'{menu_name.strip()}' 레시피가 저장되었습니다.")

# ============================================================
# 레시피 목록 조회
# ============================================================
with list_tab:
    st.markdown("#### ③ 레시피 목록 조회 및 검색")

    # 레시피 로드
    recipes_raw, err = api_get("/recipes")
    if err:
        st.error(f"레시피 조회 실패: {err}")
        recipes_raw = []

    # id → name 매핑
    ing_name_map = {x["id"]: x["name"] for x in ingredients_ref}
    menu_map = {m["id"]: {"name": m["name"], "price": m.get("price")} for m in menu_items_ref}

    # 메뉴별로 그룹화
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for r in recipes_raw if isinstance(recipes_raw, list) else []:
        mid = str(r.get("menu_item_id"))
        ing = str(r.get("ingredient_id"))
        qty = float(r.get("qty_required") or 0.0)
        grouped.setdefault(mid, []).append({
            "ingredient_id": ing,
            "ingredient_name": ing_name_map.get(ing, ing),
            "qty": qty
        })

    # 검색 UI
    with st.form("recipe_list_search_form", clear_on_submit=False):
        c1, c2 = st.columns([2, 1])
        with c1:
            q = st.text_input("검색", key="recipe_list_search",
                              placeholder="메뉴명 또는 재료명으로 검색",
                              label_visibility="collapsed")
        with c2:
            q_submit = st.form_submit_button("검색", use_container_width=True, type="primary")

    # 표시
    if not grouped:
        st.info("등록된 레시피가 없습니다.")
    else:
        # 필터 적용
        def match(mid: str, items: List[Dict[str, Any]]) -> bool:
            if not q or not q.strip():
                return True
            t = q.strip().lower()
            mname = menu_map.get(mid, {}).get("name", "").lower()
            if t in mname:
                return True
            for it in items:
                if t in (it.get("ingredient_name","").lower()):
                    return True
            return False

        total_shown = 0
        for mid, items in grouped.items():
            if not match(mid, items):
                continue
            total_shown += 1
            mname = menu_map.get(mid, {}).get("name", mid)
            mprice = menu_map.get(mid, {}).get("price")
            with st.expander(f"🍽️ {mname}", expanded=False):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown(f"**메뉴명:** {mname}")
                with col2:
                    if mprice is not None:
                        st.markdown(f"**판매 가격:** {int(mprice):,}원")
                st.markdown("**재료 목록:**")
                for it in items:
                    st.write(f"- {it['ingredient_name']} ({it['ingredient_id']}): {it['qty']}")

        if q and total_shown == 0:
            st.warning("검색 결과가 없습니다.")
