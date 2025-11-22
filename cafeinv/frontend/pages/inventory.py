import os, sys
import pandas as pd
import streamlit as st

# --- sidebar import 경로 보정 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))  # ../frontend
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
    # 입고 완료된 항목들 (receive / receive_register 에서 append)
    st.session_state.received_items = []  # [{product_code, product_name, actual_qty, ...}, ...]

if "releases" not in st.session_state:
    # 출고 내역 (release.py에서 append)
    st.session_state.releases = []  # [{product_code, product_name, qty, ...}, ...]


# -------------------------------
# 유틸: 세션 기반 재고 계산
# -------------------------------
def calc_stock_map():
    """
    세션의 received_items / releases를 이용해 품목별 재고를 dict로 반환.
    { product_code: {"name": name, "stock": int} }
    """
    stock = {}

    # 1) 입고 합산
    for r in st.session_state.received_items:
        code = r.get("product_code")
        if not code:
            continue
        name = r.get("product_name", code)
        try:
            qty = int(r.get("actual_qty", 0) or 0)
        except Exception:
            qty = 0

        if code not in stock:
            stock[code] = {"name": name, "stock": 0}
        stock[code]["stock"] += qty

    # 2) 출고 차감
    for o in st.session_state.releases:
        code = o.get("product_code")
        if not code:
            continue
        name = o.get("product_name", code)
        try:
            qty = int(o.get("qty", 0) or 0)
        except Exception:
            qty = 0

        if code not in stock:
            # 입고 없이 출고만 있으면 음수 재고가 될 수 있음 (비정상 케이스도 그대로 노출)
            stock[code] = {"name": name, "stock": 0}
        stock[code]["stock"] -= qty

    return stock


# -------------------------------
# 스타일 (기존 여백 조정 유지)
# -------------------------------
st.markdown("""
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
""", unsafe_allow_html=True)

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
        placeholder="예: d01, 카라멜시럽, 시럽류 등"
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
# 데이터 계산 (세션 기반 재고)
# -------------------------------
stock_map = calc_stock_map()

rows = []
existing_codes = set()

# 1) 기본정보에 등록된 품목 기준으로 재고 매핑
for p in st.session_state.products:
    code = p.get("code", "")
    name = p.get("name", "")
    category = p.get("category", "")
    unit = p.get("unit", "")
    status = p.get("status", "")
    safety = int(p.get("safety", 0) or 0)

    stock_qty = int(stock_map.get(code, {}).get("stock", 0))

    low_flag = safety > 0 and stock_qty < safety
    note = ""
    if low_flag:
        note = "⚠️ 안전재고 이하"

    rows.append(
        {
            "코드번호": code,
            "카테고리": category,
            "품목명": name,
            "단위": unit,
            "현재고": stock_qty,
            "안전재고": safety,
            "상태": status,
            "안전재고_부족": low_flag,
            "비고": note,
        }
    )
    existing_codes.add(code)

# 2) 혹시 재고에만 존재하고 품목등록에는 없는 코드도 표시
for code, info in stock_map.items():
    if code in existing_codes:
        continue
    name = info.get("name", code)
    stock_qty = int(info.get("stock", 0))

    rows.append(
        {
            "코드번호": code,
            "카테고리": "",
            "품목명": name,
            "단위": "",
            "현재고": stock_qty,
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
        # 내부용 컬럼은 숨기고, 보여줄 컬럼만 선택
        display_cols = ["코드번호", "카테고리", "품목명", "단위",
                        "현재고", "안전재고", "상태", "비고"]

        st.markdown("### 재고 리스트")
        st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

        # CSV 다운로드
        csv = df[display_cols].to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "CSV 다운로드",
            csv,
            file_name="inventory_session_based.csv",
            mime="text/csv"
        )
