# ========================================================================
# 입고 내역 / 거래명세서 / PDF 생성 (receive_history.py)
# ========================================================================
import os, sys
import streamlit as st
import pandas as pd
from datetime import datetime, date
from collections import defaultdict
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# --- sidebar import 경로 보정 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

from sidebar import render_sidebar
from client import api_get, api_post


# ========================================================================
# 폰트 등록: 한글 출력용
# ========================================================================
def register_korean_font(font_name="KoreanFont", font_path=None):
    """한글 폰트를 등록하고 폰트 이름을 반환"""
    try:
        import platform

        if platform.system() == "Darwin":  # macOS
            font_paths = [
                "/System/Library/Fonts/AppleGothic.ttf",
                "/Library/Fonts/AppleGothic.ttf",
                "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
            ]
            for path in font_paths:
                if os.path.exists(path):
                    pdfmetrics.registerFont(TTFont(font_name, path))
                    return font_name
        elif platform.system() == "Windows":  # Windows
            win_path = r"C:\Windows\Fonts\malgun.ttf"
            if os.path.exists(win_path):
                pdfmetrics.registerFont(TTFont(font_name, win_path))
                return font_name

        # 폴백: UnicodeCIDFont 사용
        pdfmetrics.registerFont(UnicodeCIDFont("HYSMyeongJo-Medium"))
        return "HYSMyeongJo-Medium"
    except Exception:
        try:
            pdfmetrics.registerFont(UnicodeCIDFont("HYSMyeongJo-Medium"))
            return "HYSMyeongJo-Medium"
        except:
            return "Helvetica"


# ========================================================================
# 숫자 → 한글 금액 (소수/콤마 안전하게 처리)
# ========================================================================
def number_to_korean(num):
    # 1) 먼저 안전하게 정수로 변환
    try:
        if isinstance(num, str):
            cleaned = num.replace(",", "").strip()
            # 소수점이 있으면 소수점 앞부분만 사용
            if "." in cleaned:
                cleaned = cleaned.split(".")[0]
            if cleaned == "" or cleaned == "-":
                num_int = 0
            else:
                num_int = int(cleaned)
        else:
            # float 이면 소수점 버리고 정수로
            num_int = int(num)
    except Exception:
        # 혹시라도 문제가 나면 0 처리
        num_int = 0

    num = num_int

    korean_numbers = ["", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구"]
    units = ["", "십", "백", "천"]
    units_10k = ["", "만", "억", "조"]

    if num == 0:
        return "영"

    result = []
    num_str = str(num)
    length = len(num_str)

    # 4자리씩 끊어서 처리
    for i in range(0, length, 4):
        segment = num_str[max(0, length - 4 - i): length - i]
        if not segment:
            continue
        segment_num = int(segment)
        if segment_num == 0:
            continue

        segment_str = ""
        segment_len = len(segment)
        for j, digit in enumerate(segment):
            if digit == "0":
                continue
            digit_num = int(digit)
            # 십, 백, 천의 '일십' 같은 표현에서 앞의 '일'은 생략
            if digit_num > 1 or j == segment_len - 1:
                segment_str += korean_numbers[digit_num]
            segment_str += units[segment_len - j - 1]

        unit_index = (length - i - 1) // 4
        segment_str += units_10k[unit_index]
        result.insert(0, segment_str)

    return "".join(result)


# ========================================================================
# 공통 스타일
# ========================================================================
def _build_styles(font_name):
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "TitleK",
            parent=styles["Title"],
            fontName=font_name,
            fontSize=20,
            alignment=TA_LEFT,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            "MetaLabel",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=9,
            textColor=colors.black,
            leading=12,
        )
    )
    styles.add(
        ParagraphStyle(
            "SectionHeader",
            parent=styles["Heading4"],
            fontName=font_name,
            fontSize=12,
            spaceBefore=6,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            "Cell",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=9,
            leading=12,
        )
    )
    styles.add(
        ParagraphStyle(
            "RightCell",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=9,
            alignment=TA_RIGHT,
            leading=12,
        )
    )
    styles.add(
        ParagraphStyle(
            "Small",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=8,
            leading=11,
        )
    )
    styles.add(
        ParagraphStyle(
            "NoticeStyle",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=10,
            alignment=TA_LEFT,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            "TotalStyle",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=12,
            alignment=TA_LEFT,
            textColor=colors.black,
            spaceAfter=10,
        )
    )
    return styles


def _table_style_base(first_col_header_gray=False, header_gray=False):
    ts = [
        ("FONT", (0, 0), (-1, -1), "KoreanFont", 9),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header_gray:
        ts += [
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ]
    if first_col_header_gray:
        ts += [
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#d0d0d0")),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.black),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ]
    return TableStyle(ts)


# ========================================================================
# 거래처 정보 테이블 (PDF용)
# ========================================================================
def _build_partner_table(partner_info, font_name):
    labels = ["등록번호", "상호(법인명)", "성명", "사업장주소", "업태", "종목", "전화번호"]
    values = [
        partner_info.get("business_number", "-"),
        partner_info.get("name", "-"),
        partner_info.get("representative", "-"),
        partner_info.get("address", "-"),
        "-",
        "-",
        partner_info.get("phone", "-"),
    ]

    left_table_data = []
    for label, value in zip(labels, values):
        label_para = Paragraph(
            label, ParagraphStyle("Label", fontName=font_name, fontSize=10)
        )
        value_para = Paragraph(
            str(value), ParagraphStyle("Value", fontName=font_name, fontSize=10)
        )
        left_table_data.append([label_para, value_para])

    left_table = Table(left_table_data, colWidths=[35 * mm, 65 * mm])
    left_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e6e6e6")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.black),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (1, 0), (1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    buyer_info = Paragraph(
        "구매처 1귀하",
        ParagraphStyle(
            "BuyerInfo", fontName=font_name, fontSize=12, alignment=TA_CENTER
        ),
    )

    return left_table, buyer_info


# ========================================================================
# 상품 테이블 (PDF용)
# ========================================================================
def _build_items_table(items_data, font_name):
    table = Table(
        items_data,
        colWidths=[
            24.3 * mm,
            24.3 * mm,
            17 * mm,
            24.3 * mm,
            24.3 * mm,
            24.3 * mm,
            31.5 * mm,
        ],
    )
    table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), font_name, 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ALIGN", (2, 1), (6, -2), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


# ========================================================================
# partner 헬퍼들 (코드 → 한글 이름 매핑)
# ========================================================================
def get_partner_name(partner):
    """
    거래처가 dict 또는 문자열로 들어와도
    항상 한글 이름(예: '서울커피유통')을 돌려주도록 처리
    """
    code = ""
    name = None

    # 1) dict 로 들어온 경우
    if isinstance(partner, dict):
        name = partner.get("name") or partner.get("partner_name")
        code = partner.get("code") or partner.get("partner_code") or ""
        # 이미 한글 이름이 있다면 그대로 사용
        if name and not name.startswith("pt_"):
            return name

    # 2) 문자열로 들어온 경우
    elif isinstance(partner, str):
        s = partner.strip()
        if not s:
            return "-"
        # pt_00n 형태면 코드로 간주
        if s.startswith("pt_"):
            code = s
        else:
            # 그냥 '서울커피유통' 같이 이름으로 들어온 경우
            return s

    # 3) 여기까지 왔으면 code 로 세션에 있는 partners 에서 이름 찾기
    if code:
        for p in st.session_state.get("partners", []):
            if p.get("code") == code:
                return p.get("name", code)

    # 4) 그래도 못 찾으면 남은 값들로 fallback
    if name:
        return name
    if code:
        return code
    return "-"


def get_partner_code(partner):
    """
    partner 객체에서 코드만 뽑고 싶을 때 사용
    """
    if isinstance(partner, dict):
        return partner.get("code") or partner.get("partner_code") or ""
    elif isinstance(partner, str):
        return partner.strip()
    return ""


def ensure_partner_dict(partner):
    """
    거래처가 코드 문자열 / 이름 문자열 / dict 로 들어와도
    항상 동일한 dict 형태로 변환해 줌.
    코드만 있으면 session_state.partners 에서 정보 채워 넣기.
    """
    # 1) 이미 dict 인 경우: 이름이 없으면 세션에서 보충
    if isinstance(partner, dict):
        code = partner.get("code") or partner.get("partner_code")
        name = partner.get("name") or partner.get("partner_name")
        if code and not name:
            for p in st.session_state.get("partners", []):
                if p.get("code") == code:
                    merged = dict(p)
                    merged.update(partner)
                    return merged
        return partner

    # 2) 문자열인 경우
    if isinstance(partner, str):
        s = partner.strip()
        if not s:
            return None

        # 2-1) 코드(pt_00n) 일 가능성이 높으니 먼저 코드로 조회
        for p in st.session_state.get("partners", []):
            if p.get("code") == s:
                return dict(p)

        # 2-2) 코드로도 못 찾으면 그냥 '이름'으로 취급
        return {
            "code": "",
            "name": s,
            "business_number": "",
            "representative": "",
            "address": "",
            "phone": "",
        }

    return None


# ========================================================================
# 수량/단위 변환 (내부 g/mL → 화면에만 kg/L)
# ========================================================================
def convert_qty_unit(order_qty, actual_qty, unit):
    """내부 데이터는 g/mL 유지, 화면에만 kg/L로 변환"""
    if unit is None:
        return order_qty, actual_qty, unit

    unit_str = str(unit)

    # g -> kg
    if unit_str in ["g", "그램"]:
        if (isinstance(order_qty, (int, float)) and order_qty >= 1000) or (
            isinstance(actual_qty, (int, float)) and actual_qty >= 1000
        ):
            return (
                round(order_qty / 1000, 3)
                if isinstance(order_qty, (int, float))
                else order_qty,
                round(actual_qty / 1000, 3)
                if isinstance(actual_qty, (int, float))
                else actual_qty,
                "kg",
            )
        return order_qty, actual_qty, "g"

    # mL -> L
    if unit_str.lower() in ["ml", "밀리리터"]:
        if (isinstance(order_qty, (int, float)) and order_qty >= 1000) or (
            isinstance(actual_qty, (int, float)) and actual_qty >= 1000
        ):
            return (
                round(order_qty / 1000, 3)
                if isinstance(order_qty, (int, float))
                else order_qty,
                round(actual_qty / 1000, 3)
                if isinstance(actual_qty, (int, float))
                else actual_qty,
                "L",
            )
        return order_qty, actual_qty, "mL"

    # 그 외 단위(개, 팩 등)
    return order_qty, actual_qty, unit_str


# ========================================================================
# Streamlit 기본 설정 & 세션 초기화
# ========================================================================
st.set_page_config(page_title="입고 내역", page_icon="📊", layout="wide")
render_sidebar("receive")

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

if "received_items" not in st.session_state:
    st.session_state.received_items = []
if "partners" not in st.session_state:
    st.session_state.partners = []
if "releases" not in st.session_state:
    st.session_state.releases = []


# ========================================================================
# 헤더 & 뒤로가기 버튼
# ========================================================================
title_col, button_col = st.columns([4, 1])
with title_col:
    st.title("입고 내역")
with button_col:
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
    if st.button("← 뒤로가기", use_container_width=True, key="back_button"):
        st.switch_page("pages/receive.py")

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)


# ========================================================================
# 입고 내역 섹션
# ========================================================================
st.subheader("입고 내역")

if len(st.session_state.received_items) == 0:
    st.warning("입고 처리된 내역이 없습니다.")
else:
    # --- 검색 폼 ---
    st.markdown("### 🔍 검색")
    with st.form("receive_history_search_form", clear_on_submit=False):
        st.caption("품목명, 카테고리명, 입고일, 담당자 등으로 검색 가능")

        if "receive_history_search_term" not in st.session_state:
            st.session_state.receive_history_search_term = ""

        search_query = st.text_input(
            "검색",
            key="receive_history_search",
            label_visibility="collapsed",
            value=st.session_state.receive_history_search_term,
            placeholder="품목명, 카테고리명, 입고일(YYYY-MM-DD), 담당자명 등 입력",
        )

        c1, c2 = st.columns([3, 1])
        with c1:
            submitted_search = st.form_submit_button(
                "검색", use_container_width=True, type="primary"
            )
        with c2:
            reset_search = st.form_submit_button(
                "검색 초기화", use_container_width=True
            )

        if submitted_search:
            st.session_state.receive_history_search_term = search_query.strip()
        if reset_search:
            st.session_state.receive_history_search_term = ""
            st.experimental_rerun()

    # --- 필터링 ---
    filtered_received = list(st.session_state.received_items)
    term = st.session_state.get("receive_history_search_term", "").strip()

    if term:
        search_lower = term.lower()
        filtered_received = [
            r
            for r in filtered_received
            if (
                search_lower in r.get("product_name", "").lower()
                or search_lower in r.get("category", "").lower()
                or term in r.get("receive_date", "")
                or search_lower in r.get("staff", "").lower()
            )
        ]

    if len(filtered_received) == 0:
        if term:
            st.warning(
                "검색 결과가 없습니다. '검색 초기화' 버튼을 눌러 전체 내역을 다시 볼 수 있습니다."
            )
        else:
            st.warning("입고 처리된 내역이 없습니다.")
    else:
        if term:
            st.info(f"검색 결과: {len(filtered_received)}개")

        # --- 표 데이터 구성 (단위 변환 + 거래처 이름 표시) ---
        table_rows = []
        for item in filtered_received:
            raw_unit = item.get("unit", "-")
            order_qty = item.get("order_qty", 0) or 0
            actual_qty = item.get("actual_qty", 0) or 0

            disp_order_qty, disp_actual_qty, disp_unit = convert_qty_unit(
                order_qty, actual_qty, raw_unit
            )

            table_rows.append(
                {
                    "품목코드": item.get("product_code", "-"),
                    "품목명": item.get("product_name", "-"),
                    "카테고리": item.get("category", "-"),
                    "단위": disp_unit,
                    "발주 수량": disp_order_qty,
                    "입고 수량": disp_actual_qty,
                    "발주 단가(원)": item.get("order_price", 0),
                    "입고 단가(원)": item.get("actual_price", 0),
                    "유통기한": item.get("expiry", "-"),
                    "담당자": item.get("staff", "-"),
                    "거래처": get_partner_name(item.get("partner")),
                }
            )

        df_receive = pd.DataFrame(table_rows)

        st.markdown("### 📊 입고 내역 (표 보기)")
        st.dataframe(df_receive, use_container_width=True, hide_index=True)


# ========================================================================
# 거래명세서 섹션 (입출고 통합)
# ========================================================================
st.markdown("---")
st.subheader("거래명세서 내역 (입출고 통합)")

all_transactions = []
for item in st.session_state.received_items:
    all_transactions.append(
        {
            **item,
            "transaction_type": "매입(입고)",
            "transaction_date": item.get("receive_date", ""),
            "qty": item.get("actual_qty", 0),
            "price": item.get("actual_price", 0),
        }
    )
for item in st.session_state.releases:
    all_transactions.append(
        {
            **item,
            "transaction_type": "매출(출고)",
            "transaction_date": item.get("date", ""),
            "qty": item.get("qty", 0),
            "price": item.get("price", 0),
            "actual_qty": item.get("qty", 0),
            "actual_price": item.get("price", 0),
            "category": item.get("category", ""),
            "unit": item.get("unit", ""),
            "partner": item.get("partner"),
            "special_note": item.get("note", ""),
        }
    )

if len(all_transactions) == 0:
    st.warning("거래 내역이 없습니다. 거래명세서를 생성할 수 없습니다.")
else:
    # 간편 기간 설정
    if "invoice_quick_period" in st.session_state:
        quick_period = st.session_state.invoice_quick_period
        if quick_period != "직접 선택":
            if (
                "invoice_quick_period_applied" not in st.session_state
                or st.session_state.invoice_quick_period_applied != quick_period
            ):
                today = date.today()
                if quick_period == "이번 달":
                    st.session_state.invoice_start_date = today.replace(day=1)
                    st.session_state.invoice_end_date = today
                elif quick_period == "지난달":
                    if today.month == 1:
                        st.session_state.invoice_start_date = date(
                            today.year - 1, 12, 1
                        )
                        st.session_state.invoice_end_date = date(
                            today.year - 1, 12, 31
                        )
                    else:
                        st.session_state.invoice_start_date = date(
                            today.year, today.month - 1, 1
                        )
                        if today.month - 1 in [1, 3, 5, 7, 8, 10, 12]:
                            st.session_state.invoice_end_date = date(
                                today.year, today.month - 1, 31
                            )
                        elif today.month - 1 in [4, 6, 9, 11]:
                            st.session_state.invoice_end_date = date(
                                today.year, today.month - 1, 30
                            )
                        else:
                            if today.year % 4 == 0 and (
                                today.year % 100 != 0 or today.year % 400 == 0
                            ):
                                st.session_state.invoice_end_date = date(
                                    today.year, 2, 29
                                )
                            else:
                                st.session_state.invoice_end_date = date(
                                    today.year, 2, 28
                                )
                elif quick_period == "올해":
                    st.session_state.invoice_start_date = date(today.year, 1, 1)
                    st.session_state.invoice_end_date = today
                elif quick_period == "이번 분기":
                    quarter = (today.month - 1) // 3
                    st.session_state.invoice_start_date = date(
                        today.year, quarter * 3 + 1, 1
                    )
                    st.session_state.invoice_end_date = today
                st.session_state.invoice_quick_period_applied = quick_period
                st.rerun()

    # --------------------- 거래명세서 검색 폼 ---------------------
    with st.form("invoice_search_form", clear_on_submit=False):
        st.markdown("#### 🔍 거래명세서 검색 조건")

        # ① 기간 설정
        st.markdown("**① 기간 설정 (필수)**")
        date_col1, date_col2, date_col3 = st.columns(3)
        with date_col1:
            if "invoice_start_date" not in st.session_state:
                st.session_state.invoice_start_date = date.today().replace(day=1)
            start_date = st.date_input("시작 날짜", key="invoice_start_date")
        with date_col2:
            if "invoice_end_date" not in st.session_state:
                st.session_state.invoice_end_date = date.today()
            end_date = st.date_input("종료 날짜", key="invoice_end_date")
        with date_col3:
            quick_period = st.selectbox(
                "간편 설정",
                options=["직접 선택", "이번 달", "지난달", "올해", "이번 분기"],
                key="invoice_quick_period",
            )

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        # ② 거래처 선택
        st.markdown("**② 거래처 선택 (필수)**")
        partner_dict = {}
        for trans in all_transactions:
            partner_raw = trans.get("partner")
            partner = ensure_partner_dict(partner_raw)
            if partner:
                partner_key = f"{get_partner_code(partner)}_{get_partner_name(partner)}"
                if partner_key not in partner_dict:
                    partner_dict[partner_key] = partner

        if len(st.session_state.partners) > 0:
            for p in st.session_state.partners:
                key = f"{p.get('code', '')}_{p.get('name', '')}"
                if key not in partner_dict:
                    partner_dict[key] = p

            partner_list = list(partner_dict.values())
            partner_options = ["전체 거래처"] + [
                f"{p.get('name', '')} ({p.get('code', '')})" for p in partner_list
            ]

            selected_partner_text = st.selectbox(
                "거래처 선택",
                options=partner_options,
                key="invoice_partner_select",
                help="여러 거래처를 선택하려면 '전체 거래처'를 선택하세요.",
            )

            if selected_partner_text == "전체 거래처":
                selected_partner_codes = None
            else:
                selected_code = (
                    selected_partner_text.split("(")[1].split(")")[0]
                    if "(" in selected_partner_text
                    else None
                )
                selected_partner_codes = [selected_code] if selected_code else None
        else:
            st.info("💡 거래처를 먼저 등록해주세요. (기본정보 > 목록보기 > 거래처 목록)")
            selected_partner_codes = None

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        # ③ 거래 구분
        st.markdown("**③ 거래 구분**")
        transaction_type = st.selectbox(
            "거래 구분",
            options=["전체", "매입(입고)", "매출(출고)"],
            key="invoice_transaction_type",
        )

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        # ④ 품목별 필터링
        st.markdown("**④ 품목별 필터링**")
        all_products = set()
        for trans in all_transactions:
            product_name = trans.get("product_name", "")
            if product_name:
                all_products.add(product_name)

        product_options = ["전체 품목"] + sorted(list(all_products))
        selected_product = st.selectbox(
            "품목 선택",
            options=product_options,
            key="invoice_product_select",
            help="특정 품목만 필터링하여 조회할 수 있습니다.",
        )

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        # ⑤ 검색 버튼
        search_submitted = st.form_submit_button(
            "🔍 조회하기", use_container_width=True, type="primary"
        )

    # --------------------- 거래명세서 필터링 ---------------------
    if search_submitted or "invoice_search_executed" not in st.session_state:
        st.session_state.invoice_search_executed = True

        filtered_transactions = list(all_transactions)

        if start_date and end_date:
            tmp = []
            for t in filtered_transactions:
                trans_date_str = t.get("transaction_date")
                if trans_date_str:
                    try:
                        trans_date = datetime.strptime(
                            trans_date_str, "%Y-%m-%d"
                        ).date()
                        if start_date <= trans_date <= end_date:
                            tmp.append(t)
                    except:
                        pass
            filtered_transactions = tmp

        if selected_partner_codes is not None:
            filtered_transactions = [
                t
                for t in filtered_transactions
                if get_partner_code(ensure_partner_dict(t.get("partner")))
                in selected_partner_codes
            ]

        if transaction_type == "매입(입고)":
            filtered_transactions = [
                t
                for t in filtered_transactions
                if t.get("transaction_type") == "매입(입고)"
            ]
        elif transaction_type == "매출(출고)":
            filtered_transactions = [
                t
                for t in filtered_transactions
                if t.get("transaction_type") == "매출(출고)"
            ]

        if selected_product != "전체 품목":
            filtered_transactions = [
                t
                for t in filtered_transactions
                if t.get("product_name") == selected_product
            ]

        st.session_state.filtered_invoice_transactions = filtered_transactions
    else:
        filtered_transactions = st.session_state.get(
            "filtered_invoice_transactions", []
        )

    if len(filtered_transactions) == 0:
        st.warning("검색 조건에 맞는 거래 내역이 없습니다.")
    else:
        st.success(f"검색 결과: {len(filtered_transactions)}건")

        # --------------------- 거래처별 그룹 ---------------------
        transactions_by_partner = defaultdict(list)
        transactions_without_partner = []

        for trans in filtered_transactions:
            partner_raw = trans.get("partner")
            partner = ensure_partner_dict(partner_raw)
            if partner and (get_partner_code(partner) or get_partner_name(partner) != "-"):
                partner_key = f"{get_partner_name(partner)} ({get_partner_code(partner)})"
                t_copy = dict(trans)
                t_copy["partner"] = partner
                transactions_by_partner[partner_key].append(t_copy)
            else:
                transactions_without_partner.append(trans)

        st.markdown("---")
        st.markdown("#### 📊 거래 내역 목록")

        total_supply_all = 0
        total_vat_all = 0

        st.markdown(
            """
        <style>
        div[data-testid="stDownloadButton"] > button {
            background-color: #FF69B4 !important;
            color: white !important;
            border: none !important;
            font-weight: 600 !important;
        }
        div[data-testid="stDownloadButton"] > button:hover {
            background-color: #FF1493 !important;
        }
        </style>
        """,
            unsafe_allow_html=True,
        )

        selected_date = (
            f"{start_date} ~ {end_date}" if start_date and end_date else "전체"
        )

        # --------------------- 개별 거래처 PDF 함수 ---------------------
        def generate_invoice_pdf_local(
            invoice_items, invoice_date, partner_info, show_partner_info=False
        ):
            from io import BytesIO

            font_name = register_korean_font()
            styles = _build_styles(font_name)

            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                topMargin=15 * mm,
                bottomMargin=15 * mm,
                leftMargin=20 * mm,
                rightMargin=20 * mm,
            )
            elements = []

            if invoice_date == "전체":
                date_str = datetime.now().strftime("%Y년 %m월 %d일")
            else:
                try:
                    if " ~ " in invoice_date:
                        date_str = invoice_date
                    else:
                        date_obj = datetime.strptime(invoice_date, "%Y-%m-%d")
                        date_str = date_obj.strftime("%Y년 %m월 %d일")
                except:
                    date_str = invoice_date

            date_para = Paragraph(
                date_str,
                ParagraphStyle(
                    "DateStyle",
                    parent=styles["Normal"],
                    fontName=font_name,
                    fontSize=11,
                    alignment=TA_LEFT,
                ),
            )
            elements.append(date_para)

            title_para = Paragraph(
                "거래명세서",
                ParagraphStyle(
                    "TitleStyle",
                    parent=styles["Title"],
                    fontName=font_name,
                    fontSize=20,
                    alignment=TA_CENTER,
                    spaceAfter=6,
                ),
            )
            elements.append(title_para)
            elements.append(Spacer(1, 8 * mm))

            left_table, buyer_info = _build_partner_table(partner_info, font_name)
            partner_wrapper_data = [[left_table, buyer_info]]
            partner_wrapper = Table(partner_wrapper_data, colWidths=[85 * mm, 85 * mm])
            partner_wrapper.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ]
                )
            )
            elements.append(partner_wrapper)
            elements.append(Spacer(1, 5 * mm))

            items_data = [["품목명", "규격", "수량", "단가", "공급가액", "세액", "비고"]]
            total_amount = 0
            total_vat = 0

            for item in invoice_items:
                product_name = item.get("product_name", "-")

                raw_unit = item.get("unit", "")
                raw_qty = item.get("qty", 0) or item.get("actual_qty", 0) or 0
                _, conv_qty, conv_unit = convert_qty_unit(raw_qty, raw_qty, raw_unit)

                category = item.get("category", "") or ""
                if category and conv_unit:
                    spec = f"{category} / {conv_unit}"
                elif category:
                    spec = category
                else:
                    spec = conv_unit or "-"

                qty = conv_qty
                price = item.get("price", 0) or item.get("actual_price", 0) or 0
                supply_amount = qty * price
                vat_amount = int(supply_amount * 0.1)
                note = item.get("special_note", "") or item.get("note", "") or "-"

                if show_partner_info:
                    item_partner = ensure_partner_dict(item.get("partner"))
                    if item_partner and get_partner_name(item_partner) != "-":
                        partner_nm = get_partner_name(item_partner)
                        product_name = f"{partner_nm} - {product_name}"

                total_amount += supply_amount
                total_vat += vat_amount

                items_data.append(
                    [
                        Paragraph(
                            product_name,
                            ParagraphStyle("Item", fontName=font_name, fontSize=9),
                        ),
                        Paragraph(
                            spec,
                            ParagraphStyle("Item", fontName=font_name, fontSize=9),
                        ),
                        Paragraph(
                            f"{qty:,}",
                            ParagraphStyle(
                                "Item",
                                fontName=font_name,
                                fontSize=9,
                                alignment=TA_RIGHT,
                            ),
                        ),
                        Paragraph(
                            f"{price:,}",
                            ParagraphStyle(
                                "Item",
                                fontName=font_name,
                                fontSize=9,
                                alignment=TA_RIGHT,
                            ),
                        ),
                        Paragraph(
                            f"{supply_amount:,}",
                            ParagraphStyle(
                                "Item",
                                fontName=font_name,
                                fontSize=9,
                                alignment=TA_RIGHT,
                            ),
                        ),
                        Paragraph(
                            f"{vat_amount:,}",
                            ParagraphStyle(
                                "Item",
                                fontName=font_name,
                                fontSize=9,
                                alignment=TA_RIGHT,
                            ),
                        ),
                        Paragraph(
                            note,
                            ParagraphStyle("Item", fontName=font_name, fontSize=9),
                        ),
                    ]
                )

            items_table = _build_items_table(items_data, font_name)
            center_items_wrapper_data = [[items_table]]
            center_items_wrapper = Table(center_items_wrapper_data, colWidths=[170 * mm])
            center_items_wrapper.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (0, 0), "CENTER"),
                        ("VALIGN", (0, 0), (0, 0), "TOP"),
                    ]
                )
            )
            elements.append(center_items_wrapper)
            elements.append(Spacer(1, 5 * mm))

            summary_table_data = [
                [
                    Paragraph(
                        "합계",
                        ParagraphStyle("Summary", fontName=font_name, fontSize=10),
                    ),
                    Paragraph(
                        f"{total_amount:,}",
                        ParagraphStyle(
                            "Summary",
                            fontName=font_name,
                            fontSize=10,
                            alignment=TA_RIGHT,
                        ),
                    ),
                    Paragraph(
                        f"{total_vat:,} 부가가치세",
                        ParagraphStyle(
                            "Summary",
                            fontName=font_name,
                            fontSize=10,
                            alignment=TA_RIGHT,
                        ),
                    ),
                ]
            ]
            summary_table = Table(
                summary_table_data, colWidths=[30 * mm, 40 * mm, 100 * mm]
            )
            summary_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#e6e6e6")),
                        ("ALIGN", (0, 0), (0, 0), "LEFT"),
                        ("ALIGN", (1, 0), (2, 0), "RIGHT"),
                        ("FONTNAME", (0, 0), (-1, -1), font_name),
                        ("FONTSIZE", (0, 0), (-1, -1), 10),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 5),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )

            center_summary_wrapper_data = [[summary_table]]
            center_summary_wrapper = Table(
                center_summary_wrapper_data, colWidths=[170 * mm]
            )
            center_summary_wrapper.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (0, 0), "CENTER"),
                        ("VALIGN", (0, 0), (0, 0), "TOP"),
                    ]
                )
            )
            elements.append(center_summary_wrapper)
            elements.append(Spacer(1, 5 * mm))

            account_style = ParagraphStyle(
                "AccountStyle",
                parent=styles["Normal"],
                fontSize=10,
                alignment=TA_LEFT,
                fontName=font_name,
            )
            elements.append(Paragraph("[결제계좌]-", account_style))

            doc.build(elements)
            buffer.seek(0)
            return buffer

        # --------------------- 거래처별 표 + 다운로드 버튼 ---------------------
        for idx_p, (partner_name, partner_transactions) in enumerate(
            transactions_by_partner.items()
        ):
            st.markdown("---")
            st.markdown(f"### 🏢 {partner_name}")
            st.info(f"거래처: {partner_name} | 총 {len(partner_transactions)}건")

            header_cols = st.columns([1.2, 1.5, 1, 1, 1, 1, 1, 1, 1.5])
            with header_cols[0]:
                st.write("**거래일자**")
            with header_cols[1]:
                st.write("**품목명**")
            with header_cols[2]:
                st.write("**규격/단위**")
            with header_cols[3]:
                st.write("**수량**")
            with header_cols[4]:
                st.write("**단가**")
            with header_cols[5]:
                st.write("**공급가액**")
            with header_cols[6]:
                st.write("**세액**")
            with header_cols[7]:
                st.write("**거래구분**")
            with header_cols[8]:
                st.write("**비고**")

            partner_supply = 0
            partner_vat = 0

            for trans in partner_transactions:
                trans_date = trans.get("transaction_date", "-")
                product_name = trans.get("product_name", "-")

                raw_unit = trans.get("unit", "")
                raw_qty = trans.get("qty", 0) or trans.get("actual_qty", 0) or 0
                _, conv_qty, conv_unit = convert_qty_unit(raw_qty, raw_qty, raw_unit)

                category = trans.get("category", "") or ""
                if category and conv_unit:
                    spec = f"{category} / {conv_unit}"
                elif category:
                    spec = category
                else:
                    spec = conv_unit or "-"

                qty = conv_qty
                price = trans.get("price", 0) or trans.get("actual_price", 0) or 0
                supply_amount = qty * price
                vat_amount = int(supply_amount * 0.1)
                trans_type = trans.get("transaction_type", "-")
                note = trans.get("special_note", "") or trans.get("note", "") or "-"

                partner_supply += supply_amount
                partner_vat += vat_amount
                total_supply_all += supply_amount
                total_vat_all += vat_amount

                row_cols = st.columns([1.2, 1.5, 1, 1, 1, 1, 1, 1, 1.5])
                with row_cols[0]:
                    st.write(trans_date)
                with row_cols[1]:
                    st.write(product_name)
                with row_cols[2]:
                    st.write(spec)
                with row_cols[3]:
                    st.write(f"{qty:,}")
                with row_cols[4]:
                    st.write(f"{price:,}")
                with row_cols[5]:
                    st.write(f"{supply_amount:,}")
                with row_cols[6]:
                    st.write(f"{vat_amount:,}")
                with row_cols[7]:
                    st.write(trans_type)
                with row_cols[8]:
                    st.write(note)

            partner_total = partner_supply + partner_vat
            st.markdown(
                f"**{partner_name} 합계:** 공급가액 {partner_supply:,}원 + 세액 {partner_vat:,}원 = **{partner_total:,}원**"
            )

            partner_info_raw = (
                partner_transactions[0].get("partner") if partner_transactions else None
            )
            partner_info = ensure_partner_dict(partner_info_raw) or {
                "code": "",
                "name": partner_name,
                "business_number": "",
                "representative": "",
                "address": "",
                "phone": "",
            }

            pdf_buffer = generate_invoice_pdf_local(
                partner_transactions, selected_date, partner_info
            )

            if selected_date == "전체":
                filename = (
                    f"거래명세서_{partner_name}_{datetime.now().strftime('%Y%m%d')}.pdf"
                )
            else:
                date_part = selected_date.replace(" ~ ", "_").replace("-", "")
                filename = f"거래명세서_{partner_name}_{date_part}.pdf"

            st.download_button(
                label=f"📥 {partner_name} 거래명세서 PDF 다운로드",
                data=pdf_buffer,
                file_name=filename,
                mime="application/pdf",
                use_container_width=True,
                key=f"pdf_download_{idx_p}",
            )
            st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)

        # --------------------- 거래처 미지정 내역 ---------------------
        if transactions_without_partner:
            st.markdown("---")
            st.markdown("### ❓ 거래처 미지정")
            st.warning(
                f"거래처가 지정되지 않은 내역: {len(transactions_without_partner)}건"
            )

            header_cols = st.columns([1.2, 1.5, 1, 1, 1, 1, 1, 1, 1.5])
            with header_cols[0]:
                st.write("**거래일자**")
            with header_cols[1]:
                st.write("**품목명**")
            with header_cols[2]:
                st.write("**규격/단위**")
            with header_cols[3]:
                st.write("**수량**")
            with header_cols[4]:
                st.write("**단가**")
            with header_cols[5]:
                st.write("**공급가액**")
            with header_cols[6]:
                st.write("**세액**")
            with header_cols[7]:
                st.write("**거래구분**")
            with header_cols[8]:
                st.write("**비고**")

            for trans in transactions_without_partner:
                trans_date = trans.get("transaction_date", "-")
                product_name = trans.get("product_name", "-")

                raw_unit = trans.get("unit", "")
                raw_qty = trans.get("qty", 0) or trans.get("actual_qty", 0) or 0
                _, conv_qty, conv_unit = convert_qty_unit(raw_qty, raw_qty, raw_unit)

                category = trans.get("category", "") or ""
                if category and conv_unit:
                    spec = f"{category} / {conv_unit}"
                elif category:
                    spec = category
                else:
                    spec = conv_unit or "-"

                qty = conv_qty
                price = trans.get("price", 0) or trans.get("actual_price", 0) or 0
                supply_amount = qty * price
                vat_amount = int(supply_amount * 0.1)
                trans_type = trans.get("transaction_type", "-")
                note = trans.get("special_note", "") or trans.get("note", "") or "-"

                total_supply_all += supply_amount
                total_vat_all += vat_amount

                row_cols = st.columns([1.2, 1.5, 1, 1, 1, 1, 1, 1, 1.5])
                with row_cols[0]:
                    st.write(trans_date)
                with row_cols[1]:
                    st.write(product_name)
                with row_cols[2]:
                    st.write(spec)
                with row_cols[3]:
                    st.write(f"{qty:,}")
                with row_cols[4]:
                    st.write(f"{price:,}")
                with row_cols[5]:
                    st.write(f"{supply_amount:,}")
                with row_cols[6]:
                    st.write(f"{vat_amount:,}")
                with row_cols[7]:
                    st.write(trans_type)
                with row_cols[8]:
                    st.write(note)

        # --------------------- 전체 합계 ---------------------
        st.markdown("---")
        st.markdown("#### 💰 전체 합계 정보")

        final_total = total_supply_all + total_vat_all

        summary_col1, summary_col2, summary_col3 = st.columns(3)
        with summary_col1:
            st.metric("총 공급가액 합계", f"{total_supply_all:,}원")
        with summary_col2:
            st.metric("총 세액 합계", f"{total_vat_all:,}원")
        with summary_col3:
            korean_total = number_to_korean(final_total)
            st.metric("최종 합계 금액 (청구 금액)", f"{final_total:,}원")
            st.caption(f"한글: {korean_total} 원정")

        st.markdown("---")
        st.markdown("#### 📝 공통 메모")
        common_memo = st.text_area(
            "문서 전체에 대한 공통 메모 (예: 입금 계좌: OO은행 123-...)",
            key="invoice_common_memo",
            height=100,
            placeholder="입금 계좌, 특이사항 등을 입력하세요.",
        )

        # --------------------- 전체 거래명세서 PDF (모든 거래처) ---------------------
        pdf_partner_groups = {}
        pdf_no_partner_items = []

        for trans in filtered_transactions:
            partner = ensure_partner_dict(trans.get("partner"))
            if partner:
                partner_code = get_partner_code(partner)
                if partner_code not in pdf_partner_groups:
                    pdf_partner_groups[partner_code] = {
                        "partner_info": partner,
                        "items": [],
                    }
                t_copy = dict(trans)
                t_copy["partner"] = partner
                pdf_partner_groups[partner_code]["items"].append(t_copy)
            else:
                pdf_no_partner_items.append(trans)

        def generate_all_partners_invoice_pdf(
            all_transactions, invoice_date, partner_groups, no_partner_items
        ):
            from io import BytesIO

            font_name = register_korean_font()
            styles = _build_styles(font_name)

            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                topMargin=15 * mm,
                bottomMargin=15 * mm,
                leftMargin=20 * mm,
                rightMargin=20 * mm,
            )
            elements = []

            if invoice_date == "전체":
                date_str = datetime.now().strftime("%Y년 %m월 %d일")
            else:
                try:
                    if " ~ " in invoice_date:
                        date_str = invoice_date
                    else:
                        date_obj = datetime.strptime(invoice_date, "%Y-%m-%d")
                        date_str = date_obj.strftime("%Y년 %m월 %d일")
                except:
                    date_str = invoice_date

            # 거래처별 페이지
            for partner_code, partner_data in partner_groups.items():
                partner_info = partner_data["partner_info"]
                partner_items = partner_data["items"]
                partner_name = partner_info.get("name", "거래처")

                if elements:
                    elements.append(PageBreak())

                date_para = Paragraph(
                    date_str,
                    ParagraphStyle(
                        "DateStyle",
                        parent=styles["Normal"],
                        fontName=font_name,
                        fontSize=11,
                        alignment=TA_LEFT,
                    ),
                )
                elements.append(date_para)

                title_text = f"거래명세서 - {partner_name}"
                title_para = Paragraph(
                    title_text,
                    ParagraphStyle(
                        "TitleStyle",
                        parent=styles["Title"],
                        fontName=font_name,
                        fontSize=20,
                        alignment=TA_CENTER,
                        spaceAfter=6,
                    ),
                )
                elements.append(title_para)
                elements.append(Spacer(1, 8 * mm))

                left_table, buyer_info = _build_partner_table(partner_info, font_name)
                partner_wrapper_data = [[left_table, buyer_info]]
                partner_wrapper = Table(
                    partner_wrapper_data, colWidths=[85 * mm, 85 * mm]
                )
                partner_wrapper.setStyle(
                    TableStyle(
                        [
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ]
                    )
                )
                elements.append(partner_wrapper)
                elements.append(Spacer(1, 5 * mm))

                items_data = [
                    [
                        Paragraph(
                            "품목명",
                            ParagraphStyle("Header", fontName=font_name, fontSize=10),
                        ),
                        Paragraph(
                            "규격",
                            ParagraphStyle("Header", fontName=font_name, fontSize=10),
                        ),
                        Paragraph(
                            "수량",
                            ParagraphStyle("Header", fontName=font_name, fontSize=10),
                        ),
                        Paragraph(
                            "단가",
                            ParagraphStyle("Header", fontName=font_name, fontSize=10),
                        ),
                        Paragraph(
                            "공급가액",
                            ParagraphStyle("Header", fontName=font_name, fontSize=10),
                        ),
                        Paragraph(
                            "세액",
                            ParagraphStyle("Header", fontName=font_name, fontSize=10),
                        ),
                        Paragraph(
                            "비고",
                            ParagraphStyle("Header", fontName=font_name, fontSize=10),
                        ),
                    ]
                ]
                total_amount = 0
                total_vat = 0

                for item in partner_items:
                    product_name = item.get("product_name", "-")

                    raw_unit = item.get("unit", "")
                    raw_qty = item.get("qty", 0) or item.get("actual_qty", 0) or 0
                    _, conv_qty, conv_unit = convert_qty_unit(
                        raw_qty, raw_qty, raw_unit
                    )

                    category = item.get("category", "") or ""
                    if category and conv_unit:
                        spec = f"{category} / {conv_unit}"
                    elif category:
                        spec = category
                    else:
                        spec = conv_unit or "-"

                    qty = conv_qty
                    price = item.get("price", 0) or item.get("actual_price", 0) or 0
                    supply_amount = qty * price
                    vat_amount = int(supply_amount * 0.1)
                    note = item.get("special_note", "") or item.get("note", "") or "-"

                    total_amount += supply_amount
                    total_vat += vat_amount

                    items_data.append(
                        [
                            Paragraph(
                                product_name,
                                ParagraphStyle(
                                    "Item", fontName=font_name, fontSize=9
                                ),
                            ),
                            Paragraph(
                                spec,
                                ParagraphStyle(
                                    "Item", fontName=font_name, fontSize=9
                                ),
                            ),
                            Paragraph(
                                f"{qty:,}",
                                ParagraphStyle(
                                    "Item",
                                    fontName=font_name,
                                    fontSize=9,
                                    alignment=TA_RIGHT,
                                ),
                            ),
                            Paragraph(
                                f"{price:,}",
                                ParagraphStyle(
                                    "Item",
                                    fontName=font_name,
                                    fontSize=9,
                                    alignment=TA_RIGHT,
                                ),
                            ),
                            Paragraph(
                                f"{supply_amount:,}",
                                ParagraphStyle(
                                    "Item",
                                    fontName=font_name,
                                    fontSize=9,
                                    alignment=TA_RIGHT,
                                ),
                            ),
                            Paragraph(
                                f"{vat_amount:,}",
                                ParagraphStyle(
                                    "Item",
                                    fontName=font_name,
                                    fontSize=9,
                                    alignment=TA_RIGHT,
                                ),
                            ),
                            Paragraph(
                                note,
                                ParagraphStyle(
                                    "Item", fontName=font_name, fontSize=9
                                ),
                            ),
                        ]
                    )

                items_table = _build_items_table(items_data, font_name)
                center_items_wrapper_data = [[items_table]]
                center_items_wrapper = Table(
                    center_items_wrapper_data, colWidths=[170 * mm]
                )
                center_items_wrapper.setStyle(
                    TableStyle(
                        [
                            ("ALIGN", (0, 0), (0, 0), "CENTER"),
                            ("VALIGN", (0, 0), (0, 0), "TOP"),
                        ]
                    )
                )
                elements.append(center_items_wrapper)
                elements.append(Spacer(1, 5 * mm))

                summary_table_data = [
                    [
                        Paragraph(
                            "합계",
                            ParagraphStyle(
                                "Summary", fontName=font_name, fontSize=10
                            ),
                        ),
                        Paragraph(
                            f"{total_amount:,}",
                            ParagraphStyle(
                                "Summary",
                                fontName=font_name,
                                fontSize=10,
                                alignment=TA_RIGHT,
                            ),
                        ),
                        Paragraph(
                            f"{total_vat:,} 부가가치세",
                            ParagraphStyle(
                                "Summary",
                                fontName=font_name,
                                fontSize=10,
                                alignment=TA_RIGHT,
                            ),
                        ),
                    ]
                ]
                summary_table = Table(
                    summary_table_data, colWidths=[30 * mm, 40 * mm, 100 * mm]
                )
                summary_table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#e6e6e6")),
                            ("ALIGN", (0, 0), (0, 0), "LEFT"),
                            ("ALIGN", (1, 0), (2, 0), "RIGHT"),
                            ("FONTNAME", (0, 0), (-1, -1), font_name),
                            ("FONTSIZE", (0, 0), (-1, -1), 10),
                            ("GRID", (0, 0), (-1, -1), 1, colors.black),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 5),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                            ("TOPPADDING", (0, 0), (-1, -1), 5),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ]
                    )
                )

                center_summary_wrapper_data = [[summary_table]]
                center_summary_wrapper = Table(
                    center_summary_wrapper_data, colWidths=[170 * mm]
                )
                center_summary_wrapper.setStyle(
                    TableStyle(
                        [
                            ("ALIGN", (0, 0), (0, 0), "CENTER"),
                            ("VALIGN", (0, 0), (0, 0), "TOP"),
                        ]
                    )
                )
                elements.append(center_summary_wrapper)
                elements.append(Spacer(1, 5 * mm))

                account_style = ParagraphStyle(
                    "AccountStyle",
                    parent=styles["Normal"],
                    fontSize=10,
                    alignment=TA_LEFT,
                    fontName=font_name,
                )
                elements.append(Paragraph("[결제계좌]-", account_style))

            # 거래처 미지정 페이지
            if no_partner_items:
                if elements:
                    elements.append(PageBreak())

                date_para = Paragraph(
                    date_str,
                    ParagraphStyle(
                        "DateStyle",
                        parent=styles["Normal"],
                        fontName=font_name,
                        fontSize=11,
                        alignment=TA_LEFT,
                    ),
                )
                elements.append(date_para)

                title_text = "거래명세서 - 거래처 미지정"
                title_para = Paragraph(
                    title_text,
                    ParagraphStyle(
                        "TitleStyle",
                        parent=styles["Title"],
                        fontName=font_name,
                        fontSize=20,
                        alignment=TA_CENTER,
                        spaceAfter=6,
                    ),
                )
                elements.append(title_para)
                elements.append(Spacer(1, 8 * mm))

                default_partner = {
                    "code": "",
                    "name": "거래처 미지정",
                    "business_number": "",
                    "representative": "",
                    "address": "",
                    "phone": "",
                }
                left_table, buyer_info = _build_partner_table(
                    default_partner, font_name
                )
                partner_wrapper_data = [[left_table, buyer_info]]
                partner_wrapper = Table(
                    partner_wrapper_data, colWidths=[85 * mm, 85 * mm]
                )
                partner_wrapper.setStyle(
                    TableStyle(
                        [
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ]
                    )
                )
                elements.append(partner_wrapper)
                elements.append(Spacer(1, 5 * mm))

                items_data = [
                    [
                        Paragraph(
                            "품목명",
                            ParagraphStyle("Header", fontName=font_name, fontSize=10),
                        ),
                        Paragraph(
                            "규격",
                            ParagraphStyle("Header", fontName=font_name, fontSize=10),
                        ),
                        Paragraph(
                            "수량",
                            ParagraphStyle("Header", fontName=font_name, fontSize=10),
                        ),
                        Paragraph(
                            "단가",
                            ParagraphStyle("Header", fontName=font_name, fontSize=10),
                        ),
                        Paragraph(
                            "공급가액",
                            ParagraphStyle("Header", fontName=font_name, fontSize=10),
                        ),
                        Paragraph(
                            "세액",
                            ParagraphStyle("Header", fontName=font_name, fontSize=10),
                        ),
                        Paragraph(
                            "비고",
                            ParagraphStyle("Header", fontName=font_name, fontSize=10),
                        ),
                    ]
                ]
                total_amount = 0
                total_vat = 0

                for item in no_partner_items:
                    product_name = item.get("product_name", "-")

                    raw_unit = item.get("unit", "")
                    raw_qty = item.get("qty", 0) or item.get("actual_qty", 0) or 0
                    _, conv_qty, conv_unit = convert_qty_unit(
                        raw_qty, raw_qty, raw_unit
                    )

                    category = item.get("category", "") or ""
                    if category and conv_unit:
                        spec = f"{category} / {conv_unit}"
                    elif category:
                        spec = category
                    else:
                        spec = conv_unit or "-"

                    qty = conv_qty
                    price = item.get("price", 0) or item.get("actual_price", 0) or 0
                    supply_amount = qty * price
                    vat_amount = int(supply_amount * 0.1)
                    note = item.get("special_note", "") or item.get("note", "") or "-"

                    total_amount += supply_amount
                    total_vat += vat_amount

                    items_data.append(
                        [
                            Paragraph(
                                product_name,
                                ParagraphStyle(
                                    "Item", fontName=font_name, fontSize=9
                                ),
                            ),
                            Paragraph(
                                spec,
                                ParagraphStyle(
                                    "Item", fontName=font_name, fontSize=9
                                ),
                            ),
                            Paragraph(
                                f"{qty:,}",
                                ParagraphStyle(
                                    "Item",
                                    fontName=font_name,
                                    fontSize=9,
                                    alignment=TA_RIGHT,
                                ),
                            ),
                            Paragraph(
                                f"{price:,}",
                                ParagraphStyle(
                                    "Item",
                                    fontName=font_name,
                                    fontSize=9,
                                    alignment=TA_RIGHT,
                                ),
                            ),
                            Paragraph(
                                f"{supply_amount:,}",
                                ParagraphStyle(
                                    "Item",
                                    fontName=font_name,
                                    fontSize=9,
                                    alignment=TA_RIGHT,
                                ),
                            ),
                            Paragraph(
                                f"{vat_amount:,}",
                                ParagraphStyle(
                                    "Item",
                                    fontName=font_name,
                                    fontSize=9,
                                    alignment=TA_RIGHT,
                                ),
                            ),
                            Paragraph(
                                note,
                                ParagraphStyle(
                                    "Item", fontName=font_name, fontSize=9
                                ),
                            ),
                        ]
                    )

                items_table = _build_items_table(items_data, font_name)
                center_items_wrapper_data = [[items_table]]
                center_items_wrapper = Table(
                    center_items_wrapper_data, colWidths=[170 * mm]
                )
                center_items_wrapper.setStyle(
                    TableStyle(
                        [
                            ("ALIGN", (0, 0), (0, 0), "CENTER"),
                            ("VALIGN", (0, 0), (0, 0), "TOP"),
                        ]
                    )
                )
                elements.append(center_items_wrapper)
                elements.append(Spacer(1, 5 * mm))

                summary_table_data = [
                    [
                        Paragraph(
                            "합계",
                            ParagraphStyle(
                                "Summary", fontName=font_name, fontSize=10
                            ),
                        ),
                        Paragraph(
                            f"{total_amount:,}",
                            ParagraphStyle(
                                "Summary",
                                fontName=font_name,
                                fontSize=10,
                                alignment=TA_RIGHT,
                            ),
                        ),
                        Paragraph(
                            f"{total_vat:,} 부가가치세",
                            ParagraphStyle(
                                "Summary",
                                fontName=font_name,
                                fontSize=10,
                                alignment=TA_RIGHT,
                            ),
                        ),
                    ]
                ]
                summary_table = Table(
                    summary_table_data, colWidths=[30 * mm, 40 * mm, 100 * mm]
                )
                summary_table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#e6e6e6")),
                            ("ALIGN", (0, 0), (0, 0), "LEFT"),
                            ("ALIGN", (1, 0), (2, 0), "RIGHT"),
                            ("FONTNAME", (0, 0), (-1, -1), font_name),
                            ("FONTSIZE", (0, 0), (-1, -1), 10),
                            ("GRID", (0, 0), (-1, -1), 1, colors.black),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 5),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                            ("TOPPADDING", (0, 0), (-1, -1), 5),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ]
                    )
                )

                center_summary_wrapper_data = [[summary_table]]
                center_summary_wrapper = Table(
                    center_summary_wrapper_data, colWidths=[170 * mm]
                )
                center_summary_wrapper.setStyle(
                    TableStyle(
                        [
                            ("ALIGN", (0, 0), (0, 0), "CENTER"),
                            ("VALIGN", (0, 0), (0, 0), "TOP"),
                        ]
                    )
                )
                elements.append(center_summary_wrapper)
                elements.append(Spacer(1, 5 * mm))

                account_style = ParagraphStyle(
                    "AccountStyle",
                    parent=styles["Normal"],
                    fontSize=10,
                    alignment=TA_LEFT,
                    fontName=font_name,
                )
                elements.append(Paragraph("[결제계좌]-", account_style))

            doc.build(elements)
            buffer.seek(0)
            return buffer

        pdf_buffer_all = generate_all_partners_invoice_pdf(
            filtered_transactions, selected_date, pdf_partner_groups, pdf_no_partner_items
        )

        if selected_date == "전체":
            filename_all = (
                f"거래명세서_전체_{datetime.now().strftime('%Y%m%d')}.pdf"
            )
        else:
            date_part = selected_date.replace(" ~ ", "_").replace("-", "")
            filename_all = f"거래명세서_전체_{date_part}.pdf"

        st.download_button(
            label="📥 전체 거래명세서 PDF 다운로드 (모든 거래처 포함)",
            data=pdf_buffer_all,
            file_name=filename_all,
            mime="application/pdf",
            use_container_width=True,
            key="pdf_download_all",
        )
