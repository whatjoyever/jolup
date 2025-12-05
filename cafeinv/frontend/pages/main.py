import os
import streamlit as st
from dotenv import load_dotenv
import requests
from datetime import date, datetime, timedelta
import pandas as pd

# -----------------------------
# 환경 설정
# -----------------------------
load_dotenv()
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Stock Mate", layout="wide")

# -----------------------------
# 세션 상태 초기화
# -----------------------------
if "products" not in st.session_state:
    st.session_state.products = []
if "received_items" not in st.session_state:
    st.session_state.received_items = []
if "releases" not in st.session_state:
    st.session_state.releases = []

# -----------------------------
# 헬퍼 함수
# -----------------------------
def api_get(path: str, params: dict | None = None, timeout: int = 10):
    """FastAPI 백엔드 GET 요청"""
    try:
        r = requests.get(f"{API_URL}{path}", params=params, timeout=timeout)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)

# 단위 변환 유틸
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
    """품목별 기준 단위 결정."""
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
    """해당 품목의 현재 재고를 (수량, 기준단위) 형태로 반환."""
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

# -----------------------------
# CSS (버튼 크기, 정렬)
# -----------------------------
st.markdown("""
<style>
/* 메인 컨테이너 살짝 넓게 */
.block-container {
    max-width: 1100px !important;
    margin: 0 auto !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
}

/* 버튼 스타일 */
.stButton > button {
    display: block;                 /* 가운데 정렬 위해 block 으로 */
    margin: 0 auto;                 /* 좌우 중앙 정렬 */
    width: 260px !important;        /* 버튼 가로폭 */
    height: 160px !important;
    font-size: 28px !important;
    font-weight: 800 !important;
    border-radius: 22px !important;
    background: #f8f9fa !important;
    border: 2px solid #e0e0e0 !important;
    color: #1f1f1f !important;
    box-shadow: 0 6px 15px rgba(0,0,0,0.15) !important;
    transition: all .2s ease !important;
}
.stButton > button:hover {
    background: #e9ecef !important;
    transform: translateY(-3px) !important;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# 타이틀
# -----------------------------
st.markdown(
    "<h1 style='text-align:center; font-size:72px; color:#1f4e79; font-weight:800; margin:24px 0 8px;'>Stock Mate</h1>",
    unsafe_allow_html=True
)

# -----------------------------
# 대시보드: 안전재고 이하 & 유통기한 임박 품목
# -----------------------------
st.markdown("<div style='height: 30px'></div>", unsafe_allow_html=True)

# 안전재고 이하 품목 계산
low_stock_items = []
for p in st.session_state.products:
    code = p.get("code", "")
    if not code:
        continue
    
    safety = float(p.get("safety", 0) or 0)
    if safety <= 0:
        continue
    
    base_qty, base_unit = get_stock_by_code(code)
    display_unit = (p.get("unit") or "").strip() or base_unit
    stock_disp = convert_qty(base_qty, base_unit, display_unit)
    stock_disp_round = round(stock_disp, 3)
    
    if stock_disp_round < safety:
        low_stock_items.append({
            "품목코드": code,
            "품목명": p.get("name", ""),
            "카테고리": p.get("category", ""),
            "현재고": stock_disp_round,
            "안전재고": safety,
            "단위": display_unit,
        })

# 유통기한 임박 품목 계산 (7일 이내)
expiring_items = []
today = date.today()
warning_days = 7

for item in st.session_state.received_items:
    expiry_str = item.get("expiry", "")
    if not expiry_str:
        continue
    
    try:
        if isinstance(expiry_str, date):
            expiry_date = expiry_str
        elif isinstance(expiry_str, str):
            expiry_date = datetime.strptime(expiry_str[:10], "%Y-%m-%d").date()
        else:
            continue
        
        days_left = (expiry_date - today).days
        
        if 0 <= days_left <= warning_days:
            product_code = item.get("product_code", "")
            product_name = item.get("product_name", "")
            actual_qty = item.get("actual_qty", 0)
            unit = item.get("unit", "")
            
            expiring_items.append({
                "품목코드": product_code,
                "품목명": product_name,
                "유통기한": expiry_date,
                "남은일수": days_left,
                "수량": actual_qty,
                "단위": unit,
            })
    except Exception:
        continue

# 대시보드 헤더 (카드 형식)
st.markdown("""
<style>
.dashboard-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 20px;
    border-radius: 15px;
    color: white;
    margin-bottom: 20px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}
.dashboard-card-warning {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}
.dashboard-card-info {
    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}
.dashboard-number {
    font-size: 48px;
    font-weight: bold;
    margin: 10px 0;
}
.dashboard-label {
    font-size: 18px;
    opacity: 0.9;
}
/* 대시보드 버튼 스타일 */
button[key="low_stock_dashboard_btn"],
button[key="expiring_dashboard_btn"] {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%) !important;
    color: white !important;
    font-size: 24px !important;
    font-weight: bold !important;
    height: 120px !important;
    border-radius: 15px !important;
    border: none !important;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1) !important;
    white-space: pre-line !important;
}
button[key="expiring_dashboard_btn"] {
    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%) !important;
}
button[key="low_stock_dashboard_btn"]:hover,
button[key="expiring_dashboard_btn"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15) !important;
}
</style>
""", unsafe_allow_html=True)

# 대시보드 카드 (popover 기능 포함)
dashboard_col1, dashboard_col2 = st.columns(2, gap="large")

with dashboard_col1:
    # 대시보드 카드 표시
    st.markdown(f"""
    <div class="dashboard-card dashboard-card-warning">
        <div class="dashboard-label">⚠️ 안전재고 이하 품목</div>
        <div class="dashboard-number">{len(low_stock_items)}</div>
        <div class="dashboard-label">개 품목</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Popover로 상세 정보 표시
    if low_stock_items:
        with st.popover("📋 상세 정보 보기", use_container_width=True):
            st.markdown("### ⚠️ 안전재고 이하 품목 상세")
            display_low = []
            for item in low_stock_items:
                display_low.append({
                    "품목명": item["품목명"],
                    "현재고": f"{item['현재고']} {item['단위']}",
                    "안전재고": f"{item['안전재고']} {item['단위']}",
                })
            df_low = pd.DataFrame(display_low)
            st.dataframe(df_low, use_container_width=True, hide_index=True)
    else:
        st.info("✅ 안전재고 이하 품목이 없습니다.")

with dashboard_col2:
    # 대시보드 카드 표시
    st.markdown(f"""
    <div class="dashboard-card dashboard-card-info">
        <div class="dashboard-label">📅 유통기한 임박 품목</div>
        <div class="dashboard-number">{len(expiring_items)}</div>
        <div class="dashboard-label">개 품목 (7일 이내)</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Popover로 상세 정보 표시
    if expiring_items:
        with st.popover("📋 상세 정보 보기", use_container_width=True):
            st.markdown("### 📅 유통기한 임박 품목 상세")
            # 남은일수 기준으로 정렬
            expiring_items_sorted = sorted(expiring_items, key=lambda x: x["남은일수"])
            display_expiring = []
            for item in expiring_items_sorted:
                display_expiring.append({
                    "품목명": item["품목명"],
                    "유통기한": str(item["유통기한"]),
                })
            df_expiring = pd.DataFrame(display_expiring)
            st.dataframe(df_expiring, use_container_width=True, hide_index=True)
    else:
        st.info("✅ 유통기한 임박 품목이 없습니다.")

st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)

# 모든 품목이 정상일 때 메시지
if not low_stock_items and not expiring_items:
    st.success("🎉 모든 품목이 정상 상태입니다! 안전재고 이하 품목과 유통기한 임박 품목이 없습니다.")

st.markdown("<div style='height: 30px'></div>", unsafe_allow_html=True)

# -----------------------------
# 메인 버튼 (중앙 2x2)
# -----------------------------
left, center, right = st.columns([1, 8, 1])

with center:
    # 첫 번째 줄
    row1_col1, row1_col2 = st.columns(2, gap="large")
    with row1_col1:
        if st.button("⚙️ 기본정보", use_container_width=False):
            st.switch_page("pages/info.py")
    with row1_col2:
        if st.button("🧾 입고관리", use_container_width=False):
            st.switch_page("pages/receive.py")

    # 두 번째 줄
    row2_col1, row2_col2 = st.columns(2, gap="large")
    with row2_col1:
        if st.button("📤 출고관리", use_container_width=False):
            st.switch_page("pages/release.py")
    with row2_col2:
        if st.button("📦 재고현황", use_container_width=False):
            st.switch_page("pages/inventory.py")
