# file: inventory.py
import os
import sys
from datetime import datetime

import streamlit as st
import pandas as pd

# -----------------------------
# 경로 보정 & 공통 모듈 import
# -----------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

from sidebar import render_sidebar
from client import api_get, api_post  # 백엔드 연동용 (현재는 세션 기반)

# -----------------------------
# 페이지 설정 & 사이드바
# -----------------------------
st.set_page_config(page_title="재고현황", page_icon="📦", layout="wide")
render_sidebar("inventory")

# -----------------------------
# 공통 스타일
# -----------------------------
st.markdown(
    """
<style>
    .main .block-container {
        max-width: 960px;
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
# 세션 상태 초기값
# -----------------------------
if "products" not in st.session_state:
    st.session_state.products = []          # 기본정보 품목
if "received_items" not in st.session_state:
    st.session_state.received_items = []    # 입고 내역
if "releases" not in st.session_state:
    st.session_state.releases = []          # 출고 내역
if "partners" not in st.session_state:
    st.session_state.partners = []          # 거래처 기본정보

products = st.session_state.products
received_items = st.session_state.received_items
releases = st.session_state.releases
partners = st.session_state.partners

# =========================================================
# 단위 변환 유틸 (release.py와 동일 규칙)
# =========================================================

UNIT_CONVERT = {
    ("kg", "g"): 1000.0,
    ("g", "kg"): 0.001,
    ("L", "ml"): 1000.0,
    ("ml", "L"): 0.001,
}


def convert_qty(qty: float, from_unit: str | None, to_unit: str | None) -> float:
    """단위 변환 (kg↔g, L↔ml). 정의되지 않은 조합은 원래 값 반환."""
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
    - 무게: kg/g  -> 기준 g
    - 부피: L/ml  -> 기준 ml
    - 기타: 등록된 단위 그대로 사용
    """
    for p in products:
        if p.get("code") == product_code:
            u = (p.get("unit") or "").strip()
            if u in ("kg", "g"):
                return "g"
            if u in ("L", "ml"):
                return "ml"
            return u or "개"
    return "g"


def calc_stock_flows(product_code: str) -> tuple[float, float, float, str]:
    """
    해당 품목의 입고/출고 합계를 기준단위 기준으로 계산.
    반환: (total_in_base, total_out_base, current_base, base_unit)
    """
    base_unit = get_product_base_unit(product_code)

    # 제품 기본 단위 (입고/출고에서 단위 정보가 없을 때 fallback 용)
    product_unit = None
    for p in products:
        if p.get("code") == product_code:
            product_unit = (p.get("unit") or "").strip()
            break
    if not product_unit:
        product_unit = base_unit

    total_in = 0.0
    total_out = 0.0

    # 입고 합계
    for r in received_items:
        if r.get("product_code") != product_code:
            continue
        qty = float(r.get("actual_qty", 0) or 0)
        receive_unit = (r.get("unit") or product_unit).strip()
        qty_base = convert_qty(qty, receive_unit, base_unit)
        total_in += qty_base

    # 출고 합계
    for r in releases:
        if r.get("product_code") != product_code:
            continue
        qty = float(r.get("qty", 0) or 0)
        release_unit = (r.get("unit") or product_unit).strip()
        qty_base = convert_qty(qty, release_unit, base_unit)
        total_out += qty_base

    current = total_in - total_out
    return total_in, total_out, current, base_unit


def parse_date_safe(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d")
    except Exception:
        return None


def get_latest_partner_name(product_code: str) -> str:
    """
    해당 품목의 가장 최근 입고 건의 '거래처 이름' 반환.
    1) 입고 내역의 partner_code를 가져와서
    2) partners 목록(code == partner_code)에서 name(한글)을 찾음
    3) 없으면 partner_name → partner → partner_code 순으로 fallback
    """
    latest_partner_code = None
    latest_partner_name_raw = None

    for r in reversed(received_items):
        if r.get("product_code") != product_code:
            continue

        # 입고 내역에 저장된 값들
        latest_partner_code = (
            r.get("partner_code")
            or r.get("partner")
            or r.get("partner_id")
        )
        latest_partner_name_raw = (
            r.get("partner_name")
            or r.get("partner_kor")
            or r.get("partner")
        )
        break

    # 1단계: partner_code로 partners 테이블에서 한글 이름 찾기
    if latest_partner_code and partners:
        for p in partners:
            if p.get("code") == latest_partner_code:
                # 거래처 기본정보의 name 필드를 한글 이름으로 사용
                if p.get("name"):
                    return p["name"]

    # 2단계: 입고 내역 안에 이미 이름 비슷한 값이 있으면 사용
    if latest_partner_name_raw:
        return latest_partner_name_raw

    # 3단계: 그래도 없으면 코드라도 반환
    if latest_partner_code:
        return latest_partner_code

    return ""


def get_earliest_expiry(product_code: str) -> str:
    """해당 품목의 가장 빠른 유통기한 문자열 반환."""
    dates: list[datetime] = []
    for r in received_items:
        if r.get("product_code") != product_code:
            continue
        d = parse_date_safe(r.get("expiry"))
        if d:
            dates.append(d)
    if not dates:
        return ""
    return min(dates).strftime("%Y-%m-%d")


# -----------------------------
# 헤더
# -----------------------------
top_col1, top_col2 = st.columns([4, 1])
with top_col1:
    st.markdown("## 재고현황")
    st.write("현재 창고의 재고 현황을 조회합니다. (입고/출고 내역 기준 계산)")
with top_col2:
    st.markdown("<div style='height: 8px'></div>", unsafe_allow_html=True)
    if st.button("HOME", use_container_width=True):
        st.switch_page("pages/main.py")

st.markdown("---")

# -----------------------------
# 검색 / 필터 영역
# -----------------------------
search_col1, search_col2, search_col3 = st.columns([3, 1, 1])

with search_col1:
    keyword = st.text_input(
        "검색 (코드 / 품목명 / 카테고리 / 거래처 등)",
        placeholder="예: pr_001, 카라멜 시럽, 시럽, 스위트시럽상회 등",
    )

with search_col2:
    # 실제로 입고가 한 번이라도 있었던 품목들의 카테고리만 사용
    codes_with_receive = {
        r.get("product_code") for r in received_items if r.get("product_code")
    }
    categories = set()
    for p in products:
        if p.get("code") in codes_with_receive and p.get("category"):
            categories.add(p["category"])
    category_options = ["전체"] + sorted(list(categories))
    selected_category = st.selectbox("카테고리", options=category_options, index=0)

with search_col3:
    only_below_safety = st.checkbox("안전재고 이하만 보기", value=False)

st.markdown("---")

# -----------------------------
# 재고 데이터가 없는 경우
# -----------------------------
if not received_items:
    st.warning("표시할 재고 데이터가 없습니다. 먼저 입고/품목을 등록해 주세요.")
    st.stop()

# -----------------------------
# 재고 리스트 계산 (입고/출고 기반)
# -----------------------------
summary_rows = []

# 입고가 한 번이라도 있었던 품목 코드 기준
all_codes = sorted(
    {r.get("product_code") for r in received_items if r.get("product_code")}
)

for code in all_codes:
    # 제품 기본 정보 찾기
    product = next((p for p in products if p.get("code") == code), None)
    if not product:
        # 기본정보에 없는 품목이면 스킵
        continue

    name = product.get("name", "")
    category = product.get("category", "")
    product_unit = (product.get("unit") or "").strip() or "개"
    safety = int(product.get("safety", 0) or 0)
    status = product.get("status", "사용")

    # 입고/출고 합계 및 현재고 계산
    total_in_base, total_out_base, current_base, base_unit = calc_stock_flows(code)

    # 논리적으로는 음수가 나오면 안 되지만, 방어 코드로 0 미만은 0으로 보정
    if current_base < 0:
        current_base = 0.0

    # 화면 표시는 제품 기본 단위로 변환
    current_display = convert_qty(current_base, base_unit, product_unit)

    # 유통기한 / 거래처 정보
    expiry = get_earliest_expiry(code)
    partner_name = get_latest_partner_name(code)

    # 비고(경고 메시지) 결정
    remark_flags = []
    if current_display < safety:
        remark_flags.append("안전재고 이하")
    if total_out_base > total_in_base:
        remark_flags.append("출고가 입고보다 많음")
    remark = " / ".join(remark_flags)

    # 필터링: 카테고리
    if selected_category != "전체" and category != selected_category:
        continue

    # 필터링: 안전재고 이하
    if only_below_safety and not remark_flags:
        continue

    # 필터링: 검색 키워드
    if keyword and keyword.strip():
        kw = keyword.strip().lower()
        joined = " ".join(
            [
                code,
                name,
                category,
                product_unit,
                partner_name or "",
                status or "",
            ]
        ).lower()
        if kw not in joined:
            continue

    summary_rows.append(
        {
            "code": code,
            "category": category,
            "name": name,
            "unit": product_unit,
            "current_qty": current_display,
            "safety": safety,
            "status": status,
            "expiry": expiry,
            "partner": partner_name,
            "remark": remark,
        }
    )

# -----------------------------
# 재고 리스트 표로 출력
# -----------------------------
st.markdown("### 재고 리스트")

if not summary_rows:
    st.info("조건에 해당하는 재고 데이터가 없습니다.")
else:
    # 코드 기준 정렬
    summary_rows = sorted(summary_rows, key=lambda x: x["code"])

    # DataFrame 생성
    df = pd.DataFrame(summary_rows)

    # 컬럼 순서 & 한글 헤더 적용
    df = df[
        [
            "code",
            "category",
            "name",
            "unit",
            "current_qty",
            "safety",
            "status",
            "expiry",
            "partner",
            "remark",
        ]
    ].rename(
        columns={
            "code": "코드번호",
            "category": "카테고리",
            "name": "품목명",
            "unit": "단위",
            "current_qty": "현재고",
            "safety": "안전재고",
            "status": "상태",
            "expiry": "유통기한",
            "partner": "거래처",
            "remark": "비고",
        }
    )

    # 현재고는 정수/소수 깔끔하게 표현
    def fmt_qty(v):
        try:
            f = float(v)
        except Exception:
            return v
        if abs(f - int(f)) < 1e-6:
            return int(f)
        return round(f, 3)

    df["현재고"] = df["현재고"].apply(fmt_qty)

    st.dataframe(df, use_container_width=True, hide_index=True)

    # -----------------------------
    # CSV 다운로드
    # -----------------------------
    csv_data = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "CSV 다운로드",
        data=csv_data,
        file_name="inventory.csv",
        mime="text/csv",
    )

