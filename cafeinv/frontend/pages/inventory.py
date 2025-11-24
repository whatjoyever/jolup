# file: inventory.py
import os, sys
import pandas as pd
import streamlit as st

# --- sidebar import 경로 보정 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

from sidebar import render_sidebar
# --------------------------------

# -------------------------------
# 페이지 설정 & 커스텀 사이드바
# -------------------------------
st.set_page_config(page_title="재고현황", page_icon="📦", layout="wide")
render_sidebar("inventory")

# -------------------------------
# 세션 상태 초기화
# -------------------------------
if "products" not in st.session_state:
    st.session_state.products = []  # [{code, category, name, unit, status, safety}, ...]

if "received_items" not in st.session_state:
    st.session_state.received_items = []  # [{product_code, product_name, unit, actual_qty, ...}, ...]

if "releases" not in st.session_state:
    st.session_state.releases = []  # [{product_code, product_name, unit, qty, ...}, ...]

# =========================================================
# 🔁 단위 변환 유틸 (release.py와 동일하게 맞춤)
# =========================================================
UNIT_CONVERT = {
    ("kg", "g"): 1000.0,
    ("g", "kg"): 0.001,
    ("L", "ml"): 1000.0,
    ("ml", "L"): 0.001,
}

def convert_qty(qty: float, from_unit: str | None, to_unit: str | None) -> float:
    """단위 변환 (kg↔g, L↔ml). 정의되지 않은 조합은 값 그대로."""
    if qty is None:
        return 0.0
    if not from_unit or not to_unit or from_unit == to_unit:
        return float(qty)
    factor = UNIT_CONVERT.get((from_unit, to_unit))
    if factor is None:
        return float(qty)
    return float(qty) * factor


def get_product_base_unit(product_code: str) -> str:
    """
    품목별 기준 단위 결정.
    - 원두 등 kg/g → g 기준
    - 액체 L/ml → ml 기준
    - 그 외는 products에 정의된 unit 그대로
    """
    for p in st.session_state.products:
        if p.get("code") == product_code:
            u = (p.get("unit") or "").strip()
            if u in ("kg", "g"):
                return "g"
            if u in ("L", "ml"):
                return "ml"
            return u or "g"
    return "g"


def get_stock_by_code(product_code: str) -> tuple[float, str]:
    """
    release.py와 동일한 방식으로
    해당 품목의 현재 재고를 (수량, 기준단위) 형태로 반환.
    - 입고: received_items.actual_qty, unit 기준
    - 출고: releases.qty, unit 기준
    둘 다 기준 단위로 변환해서 합산.
    """
    base_unit = get_product_base_unit(product_code)

    total_in = 0.0
    for r in st.session_state.received_items:
        if r.get("product_code") != product_code:
            continue
        qty = float(r.get("actual_qty", 0) or 0)
        from_unit = (r.get("unit") or base_unit).strip()
        total_in += convert_qty(qty, from_unit, base_unit)

    total_out = 0.0
    for o in st.session_state.releases:
        if o.get("product_code") != product_code:
            continue
        qty = float(o.get("qty", 0) or 0)
        from_unit = (o.get("unit") or base_unit).strip()
        total_out += convert_qty(qty, from_unit, base_unit)

    return total_in - total_out, base_unit


# -------------------------------
# 스타일
# -------------------------------
st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)

# -------------------------------
# 헤더
# -------------------------------
title_col, right_col = st.columns([4, 2])
with title_col:
    st.title("재고현황")
    st.caption("현재 창고의 재고 현황을 조회합니다.")
with right_col:
    st.write("")
    st.write("")
    if st.button("HOME", use_container_width=True):
        st.switch_page("pages/main.py")

st.markdown("<div style='height: 8px'></div>", unsafe_allow_html=True)

# -------------------------------
# 필터 & 검색
# -------------------------------
flt_col1, flt_col2, flt_col3 = st.columns([2, 1, 1])

with flt_col1:
    search_term = st.text_input(
        "검색 (코드 / 품목명 / 카테고리)",
        key="inventory_search_term",
        placeholder="예: pr_001, 카라멜 시럽, 시럽 등",
    )

with flt_col2:
    category_options = ["전체"] + sorted(
        list({p.get("category", "") for p in st.session_state.products if p.get("category")})
    )
    category_filter = st.selectbox("카테고리", options=category_options, index=0)

with flt_col3:
    only_low = st.checkbox("안전재고 이하만 보기", value=False)

st.markdown("<div style='height: 8px'></div>", unsafe_allow_html=True)

# -------------------------------
# 재고 계산 (단위 변환 적용)
# -------------------------------
rows = []
used_codes: set[str] = set()

# 1) products에 등록된 품목 기준
for p in st.session_state.products:
    code = p.get("code", "")
    if not code:
        continue

    name = p.get("name", "")
    category = p.get("category", "")
    display_unit = (p.get("unit") or "").strip() or None
    status = p.get("status", "")
    safety = float(p.get("safety", 0) or 0)

    # 기준 단위 기준 재고 계산
    base_qty, base_unit = get_stock_by_code(code)

    # 화면에 보여줄 단위(품목 단위)에 맞게 변환
    final_unit = display_unit or base_unit
    stock_disp = convert_qty(base_qty, base_unit, final_unit)

    # 너무 자잘한 소수는 3자리까지만
    stock_disp_round = round(stock_disp, 3)

    low_flag = safety > 0 and stock_disp_round < safety

    note = ""
    if low_flag:
        note = "⚠️ 안전재고 이하"
    if stock_disp_round < 0:
        # 마이너스 재고면 경고 메시지 덧붙이기
        note = (note + " / " if note else "") + "출고가 입고보다 많음 (데이터 확인 필요)"

    rows.append(
        {
            "코드번호": code,
            "카테고리": category,
            "품목명": name,
            "단위": final_unit or "",
            "현재고": stock_disp_round,
            "안전재고": safety,
            "상태": status,
            "안전재고_부족": low_flag or stock_disp_round < 0,
            "비고": note,
        }
    )
    used_codes.add(code)

# 2) 입고/출고에는 있는데 품목 등록이 안 된 코드도 표시
extra_codes: set[str] = set()

for r in st.session_state.received_items:
    c = r.get("product_code")
    if c and c not in used_codes:
        extra_codes.add(c)
for o in st.session_state.releases:
    c = o.get("product_code")
    if c and c not in used_codes:
        extra_codes.add(c)

for code in extra_codes:
    # 이름은 마지막 기록에서 하나 가져오기
    name = code
    for r in st.session_state.received_items:
        if r.get("product_code") == code:
            name = r.get("product_name", code)
    for o in st.session_state.releases:
        if o.get("product_code") == code:
            name = o.get("product_name", name)

    base_qty, base_unit = get_stock_by_code(code)
    stock_disp_round = round(base_qty, 3)

    rows.append(
        {
            "코드번호": code,
            "카테고리": "",
            "품목명": name,
            "단위": base_unit,
            "현재고": stock_disp_round,
            "안전재고": 0,
            "상태": "미등록",
            "안전재고_부족": False,
            "비고": "품목 미등록",
        }
    )

# -------------------------------
# DataFrame 생성 & 필터 적용
# -------------------------------
if not rows:
    st.warning("표시할 재고 데이터가 없습니다. 먼저 입출고/품목을 등록해 주세요.")
else:
    df = pd.DataFrame(rows)

    # 검색 필터
    if search_term:
        s = search_term.strip().lower()
        df = df[
            df["코드번호"].astype(str).str.lower().str.contains(s)
            | df["품목명"].astype(str).str.lower().str.contains(s)
            | df["카테고리"].astype(str).str.lower().str.contains(s)
        ]

    # 카테고리 필터
    if category_filter and category_filter != "전체":
        df = df[df["카테고리"] == category_filter]

    # 안전재고 이하만
    if only_low:
        df = df[df["안전재고_부족"] == True]

    if df.empty:
        st.warning("조건에 맞는 재고 데이터가 없습니다.")
    else:
        display_cols = [
            "코드번호",
            "카테고리",
            "품목명",
            "단위",
            "현재고",
            "안전재고",
            "상태",
            "비고",
        ]

        st.markdown("### 재고 리스트")
        st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

        csv = df[display_cols].to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "CSV 다운로드",
            csv,
            file_name="inventory_session_based.csv",
            mime="text/csv",
        )
