import os, sys
import pandas as pd
import streamlit as st
from client import api_get 
# --- sidebar import 경로 보정 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))  # ../frontend
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

from sidebar import render_sidebar
from client import api_get, api_post   # ✅ 올바른 import
# --------------------------------


# -------------------------------
# 페이지 설정 & 커스텀 사이드바
# -------------------------------
st.set_page_config(page_title="재고현황", page_icon="📦", layout="wide")
render_sidebar("inventory")

# 스타일 (기존 여백 조정 유지)
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
    st.caption("현재 창고의 재고 현황을 조회합니다. (백엔드 연동)")
with right_col:
    st.write("")
    st.write("")
    if st.button("HOME", use_container_width=True):
        st.switch_page("pages/main.py")

# -------------------------------
# 필터 & 액션
# -------------------------------
ctl1, ctl2, ctl3 = st.columns([1, 1, 2])
with ctl1:
    limit = st.number_input("표시 개수", min_value=1, max_value=1000, value=50, step=10)
with ctl2:
    refresh = st.button("새로고침")

# -------------------------------
# 데이터 로드
# -------------------------------
with st.spinner("재고 불러오는 중..."):
    data, err = api_get("/inventory_tx", params={"limit": int(limit)})
    # 필요시 /inventory 로 바꿔도 됩니다: data, err = api_get("/inventory")

if err:
    st.error(f"재고 조회 실패: {err}")
else:
    # 응답이 None이면 빈 리스트로 처리
    rows = data or []
    if isinstance(rows, dict):
        # 혹시 dict 형태로 오면 rows 내부 키 추정
        rows = rows.get("items", []) or rows.get("data", []) or []

    if len(rows) == 0:
        st.warning("표시할 재고 데이터가 없습니다.")
    else:
        # 표로 보기 좋게 정리
        df = pd.DataFrame(rows)

        # 컬럼 정렬(있을 때만 적용)
        preferred = ["tx_id", "item_code", "item_name", "location", "qty", "unit",
                     "stock", "safety", "updated_at", "created_at", "type", "note"]
        cols = [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred]
        df = df[cols]

        st.markdown("### 재고 리스트")
        st.dataframe(df, use_container_width=True, hide_index=True)

        # 다운로드
        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("CSV 다운로드", csv, file_name="inventory.csv", mime="text/csv")

# 디버그: 현재 API URL 표시
st.caption(f"API_URL = {os.getenv('API_URL')}")
