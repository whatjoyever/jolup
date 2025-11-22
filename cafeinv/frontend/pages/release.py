# file: release.py
import os
import sys
from datetime import datetime

import streamlit as st

# -----------------------------
# 경로 보정 & 공통 모듈 import
# -----------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

from sidebar import render_sidebar
from client import api_get, api_post  # 나중에 백엔드 연동용으로 사용 가능


# -----------------------------
# 페이지 설정 & 사이드바
# -----------------------------
st.set_page_config(page_title="출고관리", page_icon="📤", layout="wide")
render_sidebar("release")

# -----------------------------
# 공통 스타일
# -----------------------------
st.markdown(
    """
<style>
    .main .block-container {
        max-width: 900px;
        padding-top: 1rem;
        padding-right: 1.5rem;
        padding-left: 1.5rem;
        padding-bottom: 2rem;
    }
    div[data-testid="stHorizontalBlock"] { padding-left: 0.5rem; }
</style>
""",
    unsafe_allow_html=True,
)


# -----------------------------
# 세션 상태 기본값
# -----------------------------
if "received_items" not in st.session_state:
    st.session_state.received_items = []  # 입고 내역 (세션 기반)

if "releases" not in st.session_state:
    st.session_state.releases = []  # 출고 내역 (세션 기반)

if "products" not in st.session_state:
    st.session_state.products = []

if "recipes" not in st.session_state:
    st.session_state.recipes = {}

# 혹시 예전에 session_recipes 같은 이름을 썼다면 합쳐주기
if "session_recipes" in st.session_state and st.session_state.session_recipes:
    if not st.session_state.recipes:
        st.session_state.recipes = st.session_state.session_recipes


# =========================================================
# 🔁 단위 변환 유틸
# =========================================================

# 기본 변환 계수: (from_unit, to_unit) -> factor
UNIT_CONVERT = {
    ("kg", "g"): 1000.0,
    ("g", "kg"): 0.001,
    ("L", "ml"): 1000.0,
    ("ml", "L"): 0.001,
}


def convert_qty(qty: float, from_unit: str | None, to_unit: str | None) -> float:
    """단위 변환 (kg↔g, L↔ml). 정의되지 않은 조합은 그대로 리턴."""
    if qty is None:
        return 0.0
    if not from_unit or not to_unit or from_unit == to_unit:
        return float(qty)

    factor = UNIT_CONVERT.get((from_unit, to_unit))
    if factor is None:
        # 변환 정의 안 되어 있으면 그냥 값 그대로 사용 (예: 개, 병 등)
        return float(qty)
    return float(qty) * factor


def get_product_base_unit(product_code: str) -> str:
    """
    품목별 '기준 단위'를 결정.
    - 원두: kg / g → g 기준
    - 액체: L / ml → ml 기준
    - 그 외: products에 정의된 unit 그대로
    """
    for p in st.session_state.products:
        if p.get("code") == product_code:
            u = (p.get("unit") or "").strip()
            if u in ("kg", "g"):
                return "g"
            if u in ("L", "ml"):
                return "ml"
            return u or "g"
    # 품목 정보가 없으면 일단 g로
    return "g"


def get_stock_by_code(product_code: str) -> tuple[float, str]:
    """
    해당 품목의 현재 재고를 계산해서 (수량, 기준단위) 튜플로 반환.

    - 입고: received_items.actual_qty + unit
    - 출고: releases.qty + unit
    둘 다 기준 단위로 변환해서 합산한다.
    """
    base_unit = get_product_base_unit(product_code)

    # 입고 합계
    total_in = 0.0
    for r in st.session_state.received_items:
        if r.get("product_code") == product_code:
            qty = float(r.get("actual_qty", 0) or 0)
            from_unit = (r.get("unit") or base_unit).strip()
            qty_base = convert_qty(qty, from_unit, base_unit)
            total_in += qty_base

    # 출고 합계
    total_out = 0.0
    for r in st.session_state.releases:
        if r.get("product_code") == product_code:
            qty = float(r.get("qty", 0) or 0)
            from_unit = (r.get("unit") or base_unit).strip()
            qty_base = convert_qty(qty, from_unit, base_unit)
            total_out += qty_base

    return total_in - total_out, base_unit


def add_release_record(
    product_code: str,
    product_name: str,
    qty: float,
    unit: str,
    reason: str,
    tx_type: str,
    menu_name: str | None = None,
):
    """출고 내역을 세션에 추가 (단위까지 함께 저장)"""
    st.session_state.releases.append(
        {
            "product_code": product_code,
            "product_name": product_name,
            "qty": float(qty),
            "unit": unit,
            "reason": reason,
            "tx_type": tx_type,  # "레시피 출고" / "수동 출고"
            "menu_name": menu_name,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    )


# -----------------------------
# 헤더
# -----------------------------
top_col1, top_col2 = st.columns([4, 1])
with top_col1:
    st.markdown("## 출고관리")
    st.write("재고에서 출고(소모·폐기·기타)를 등록하고, 출고 이력을 조회합니다.")
with top_col2:
    st.markdown("<div style='height: 8px'></div>", unsafe_allow_html=True)
    if st.button("HOME", use_container_width=True):
        st.switch_page("pages/main.py")

st.markdown("---")

tab_register, tab_history = st.tabs(["출고 등록", "출고 내역"])

# =====================================================================
# 탭 1. 출고 등록
# =====================================================================
with tab_register:
    sub_tab_recipe, sub_tab_manual = st.tabs(["레시피 기반 출고", "수동 출고 등록"])

    # -------------------------------------------------
    # 1) 레시피 기반 출고
    # -------------------------------------------------
    with sub_tab_recipe:
        st.markdown("### 레시피 기반 출고")

        recipes = st.session_state.get("recipes") or {}
        if not recipes:
            st.info("등록된 레시피 정보가 없습니다. 먼저 레시피를 등록해 주세요.")
        else:
            menu_names = sorted(list(recipes.keys()))
            selected_menu = st.selectbox("메뉴 선택", options=menu_names)

            recipe_data = recipes.get(selected_menu, {})
            ingredients = recipe_data.get("ingredients", [])

            col_qty, _ = st.columns([1, 3])
            with col_qty:
                cups = st.number_input("출고 수량(잔/개)", min_value=1, step=1, value=1)

            st.markdown("#### 사용 예정 원재료")
            if not ingredients:
                st.warning("이 레시피에 등록된 원재료가 없습니다. 레시피를 먼저 수정해 주세요.")
            else:
                insufficient = False

                for ing in ingredients:
                    code = ing.get("ingredient_code")
                    name = ing.get("ingredient_name")
                    unit = ing.get("unit", "g")
                    base_qty = float(ing.get("qty", 0.0))

                    required_qty = base_qty * cups  # 레시피 단위 기준 필요량
                    current_stock, stock_unit = get_stock_by_code(code)

                    # 비교를 위해 '필요량'을 기준 단위로 변환
                    required_in_base = convert_qty(required_qty, unit, stock_unit)

                    line = (
                        f"- {name} ({code}) : 1잔당 {base_qty}{unit} × {cups} "
                        f"= {required_qty}{unit} 필요 / "
                        f"현재 재고: {current_stock:.2f}{stock_unit}"
                    )

                    if current_stock < required_in_base:
                        insufficient = True
                        st.markdown(
                            f"<span style='color:#f97373;'>{line}  (재고 부족)</span>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(line)

                st.markdown("---")
                reason = st.text_input("출고 사유", placeholder="예: 판매, 시음, 폐기 등", value="판매")

                disabled = insufficient or cups <= 0
                if insufficient:
                    st.warning("재고가 부족한 원재료가 있어 출고가 불가능합니다. 입고를 먼저 진행해 주세요.")

                if st.button(
                    "레시피 기반 출고 등록",
                    type="primary",
                    use_container_width=True,
                    disabled=disabled,
                ):
                    # 각 재료별로 출고 내역 추가 (레시피 단위 그대로 저장)
                    for ing in ingredients:
                        code = ing.get("ingredient_code")
                        name = ing.get("ingredient_name")
                        unit = ing.get("unit", "g")
                        base_qty = float(ing.get("qty", 0.0))
                        required_qty = base_qty * cups

                        add_release_record(
                            product_code=code,
                            product_name=name,
                            qty=required_qty,
                            unit=unit,
                            reason=f"[레시피:{selected_menu}] {reason}",
                            tx_type="레시피 출고",
                            menu_name=selected_menu,
                        )

                    st.success(f"'{selected_menu}' {cups}개 레시피 기반 출고가 등록되었습니다.")

    # -------------------------------------------------
    # 2) 수동 출고 등록
    # -------------------------------------------------
    with sub_tab_manual:
        st.markdown("### 수동 출고 등록")

        if not st.session_state.products:
            st.info("등록된 품목이 없습니다. 먼저 기본정보에서 품목을 등록하세요.")
        else:
            products = st.session_state.products
            options = [f"{p['name']} ({p['code']})" for p in products]
            selected_opt = st.selectbox("출고할 품목", options=options)
            idx = options.index(selected_opt)
            selected_product = products[idx]

            code = selected_product["code"]
            name = selected_product["name"]

            current_stock, stock_unit = get_stock_by_code(code)
            st.caption(f"현재 재고: {current_stock:.2f}{stock_unit} (기준 단위)")

            # 출고 단위 선택 (기본은 기준 단위)
            unit_options = ["g", "kg", "ml", "L", "개", "병"]
            default_unit = stock_unit if stock_unit in unit_options else selected_product.get("unit", stock_unit)
            if default_unit not in unit_options:
                unit_index = 0
            else:
                unit_index = unit_options.index(default_unit)

            col1, col2 = st.columns(2)
            with col1:
                qty = st.number_input("출고 수량", min_value=0.0, step=1.0, value=0.0)
            with col2:
                unit = st.selectbox("출고 단위", options=unit_options, index=unit_index)

            reason = st.text_input("출고 사유", placeholder="예: 폐기, 샘플 사용, 분실 등")

            # 재고 체크: 입력 단위를 기준 단위로 변환해서 비교
            required_in_base = convert_qty(qty, unit, stock_unit)
            disabled = qty <= 0 or current_stock < required_in_base

            if qty > 0 and current_stock < required_in_base:
                st.warning(
                    f"재고보다 많은 수량을 출고할 수 없습니다. "
                    f"(요청: {qty}{unit} ≒ {required_in_base:.2f}{stock_unit}, "
                    f"재고: {current_stock:.2f}{stock_unit})"
                )

            if st.button(
                "수동 출고 등록",
                type="primary",
                use_container_width=True,
                disabled=disabled,
            ):
                add_release_record(
                    product_code=code,
                    product_name=name,
                    qty=qty,
                    unit=unit,
                    reason=reason or "수동 출고",
                    tx_type="수동 출고",
                    menu_name=None,
                )
                st.success("수동 출고가 등록되었습니다.")


# =====================================================================
# 탭 2. 출고 내역
# =====================================================================
with tab_history:
    st.markdown("### 출고 내역")

    releases = st.session_state.get("releases", [])

    if not releases:
        st.info("등록된 출고 내역이 없습니다.")
    else:
        # 최신 순으로 정렬
        releases_sorted = sorted(
            releases,
            key=lambda x: x.get("created_at", ""),
            reverse=True,
        )

        st.markdown("#### 출고 목록")
        st.write("")

        for r in releases_sorted:
            created = r.get("created_at")
            code = r.get("product_code")
            name = r.get("product_name")
            qty = r.get("qty")
            unit = r.get("unit", "")
            tx_type = r.get("tx_type")
            reason = r.get("reason")
            menu_name = r.get("menu_name")

            c1, c2, c3, c4 = st.columns([1.6, 2.2, 1, 3.2])
            with c1:
                st.caption(str(created))
            with c2:
                if menu_name:
                    st.write(f"{name} ({code}) / 메뉴: {menu_name}")
                else:
                    st.write(f"{name} ({code})")
            with c3:
                st.write(f"{qty}{unit}")
            with c4:
                st.write(f"{tx_type} - {reason}")

        st.markdown("---")
        st.caption(f"총 출고 건수: {len(releases_sorted)}건")
