# ========================================================================
# PDF 생성 관련 주요 라이브러리
# ========================================================================
import os, sys
import streamlit as st
from datetime import datetime, date
from collections import Counter
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# ========================================================================
# PDF 레이아웃 유틸리티 함수들 (receive.py에서 복사)
# ========================================================================

# ------------------------------------------------------------------------
# 폰트 등록: 한글 출력용
# ------------------------------------------------------------------------
def register_korean_font(font_name='KoreanFont', font_path=None):
    """한글 폰트를 등록하고 폰트 이름을 반환"""
    try:
        import platform
        if platform.system() == 'Darwin':  # macOS
            font_paths = [
                '/System/Library/Fonts/AppleGothic.ttf',
                '/Library/Fonts/AppleGothic.ttf',
                '/System/Library/Fonts/Supplemental/AppleGothic.ttf'
            ]
            for path in font_paths:
                if os.path.exists(path):
                    pdfmetrics.registerFont(TTFont(font_name, path))
                    return font_name
        elif platform.system() == 'Windows':  # Windows
            win_path = r"C:\Windows\Fonts\malgun.ttf"
            if os.path.exists(win_path):
                pdfmetrics.registerFont(TTFont(font_name, win_path))
                return font_name
        
        # 폴백: UnicodeCIDFont 사용
        pdfmetrics.registerFont(UnicodeCIDFont('HYSMyeongJo-Medium'))
        return 'HYSMyeongJo-Medium'
    except Exception:
        try:
            pdfmetrics.registerFont(UnicodeCIDFont('HYSMyeongJo-Medium'))
            return 'HYSMyeongJo-Medium'
        except:
            return 'Helvetica'

# ------------------------------------------------------------------------
# 숫자 한글 변환 함수
# ------------------------------------------------------------------------
def number_to_korean(num):
    """숫자를 한글 숫자 표기로 변환"""
    korean_numbers = ['', '일', '이', '삼', '사', '오', '육', '칠', '팔', '구']
    units = ['', '십', '백', '천']
    units_10k = ['', '만', '억', '조']
    
    if num == 0:
        return '영'
    
    result = []
    num_str = str(num)
    length = len(num_str)
    
    for i in range(0, length, 4):
        segment = num_str[max(0, length-4-i):length-i]
        if not segment:
            continue
        segment_num = int(segment)
        if segment_num == 0:
            continue
        
        segment_str = ''
        segment_len = len(segment)
        for j, digit in enumerate(segment):
            if digit == '0':
                continue
            digit_num = int(digit)
            if digit_num > 1 or j == segment_len - 1:
                segment_str += korean_numbers[digit_num]
            if segment_len - j - 1 < len(units):
                segment_str += units[segment_len - j - 1]
        
        unit_index = (length - i - 1) // 4
        if unit_index > 0:
            segment_str += units_10k[unit_index]
        result.insert(0, segment_str)
    
    return ''.join(result)

# ------------------------------------------------------------------------
# 공통 스타일 팩토리
# ------------------------------------------------------------------------
def _build_styles(font_name):
    """공통 스타일을 생성하고 반환"""
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle('TitleK',
                              parent=styles['Title'],
                              fontName=font_name,
                              fontSize=20,
                              alignment=TA_LEFT,
                              spaceAfter=6))
    styles.add(ParagraphStyle('MetaLabel',
                              parent=styles['Normal'],
                              fontName=font_name,
                              fontSize=9,
                              textColor=colors.black,
                              leading=12))
    styles.add(ParagraphStyle('SectionHeader',
                              parent=styles['Heading4'],
                              fontName=font_name,
                              fontSize=12,
                              spaceBefore=6,
                              spaceAfter=4))
    styles.add(ParagraphStyle('Cell',
                              parent=styles['Normal'],
                              fontName=font_name,
                              fontSize=9,
                              leading=12))
    styles.add(ParagraphStyle('RightCell',
                              parent=styles['Normal'],
                              fontName=font_name,
                              fontSize=9,
                              alignment=TA_RIGHT,
                              leading=12))
    styles.add(ParagraphStyle('Small',
                              parent=styles['Normal'],
                              fontName=font_name,
                              fontSize=8,
                              leading=11))
    styles.add(ParagraphStyle('NoticeStyle',
                              parent=styles['Normal'],
                              fontName=font_name,
                              fontSize=10,
                              alignment=TA_LEFT,
                              spaceAfter=5))
    styles.add(ParagraphStyle('TotalStyle',
                              parent=styles['Normal'],
                              fontName=font_name,
                              fontSize=12,
                              alignment=TA_LEFT,
                              textColor=colors.black,
                              spaceAfter=10))
    return styles

# ------------------------------------------------------------------------
# 표 스타일 유틸
# ------------------------------------------------------------------------
def _table_style_base(first_col_header_gray=False, header_gray=False):
    """테이블 기본 스타일 생성"""
    ts = [
        ('FONT', (0,0), (-1,-1), 'Helvetica', 9),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]
    if header_gray:
        ts += [
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('ALIGN', (0,0), (-1,0), 'CENTER')
        ]
    if first_col_header_gray:
        ts += [
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#d0d0d0')),
            ('TEXTCOLOR', (0,0), (0,-1), colors.black),
            ('ALIGN', (0,0), (0,-1), 'CENTER')
        ]
    return TableStyle(ts)

# ------------------------------------------------------------------------
# 거래처 정보 테이블 구성 (이미지 형식: 왼쪽 라벨+데이터, 오른쪽 구매처)
# ------------------------------------------------------------------------
def _build_partner_table(partner_info, font_name):
    """거래처 정보 테이블 생성 (이미지 형식: 왼쪽 라벨 컬럼 회색 배경, 오른쪽 구매처)"""
    labels = ["등록번호", "상호(법인명)", "성명", "사업장주소", "업태", "종목", "전화번호"]
    values = [
        partner_info.get('business_number', '-'),
        partner_info.get('name', '-'),
        partner_info.get('representative', '-'),
        partner_info.get('address', '-'),
        '-',
        '-',
        partner_info.get('phone', '-')
    ]
    
    # 왼쪽 테이블: 라벨(회색) + 데이터(흰색) - 한글 폰트로 Paragraph 사용
    left_table_data = []
    for label, value in zip(labels, values):
        label_para = Paragraph(label, ParagraphStyle('Label', fontName=font_name, fontSize=10))
        value_para = Paragraph(str(value), ParagraphStyle('Value', fontName=font_name, fontSize=10))
        left_table_data.append([label_para, value_para])
    
    left_table = Table(left_table_data, colWidths=[35*mm, 65*mm])
    left_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e6e6e6')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    
    # buyer_info도 Paragraph로 변환하여 한글 폰트 적용
    buyer_info = Paragraph("구매처 1귀하", ParagraphStyle('BuyerInfo', fontName=font_name, fontSize=12, alignment=TA_CENTER))
    
    return left_table, buyer_info

# ------------------------------------------------------------------------
# 상품 테이블 구성
# ------------------------------------------------------------------------
def _build_items_table(items_data, font_name):
    """상품 테이블 생성 (한글 폰트 적용 - Paragraph 객체 사용)"""
    table = Table(items_data, colWidths=[24.3*mm, 24.3*mm, 17*mm, 24.3*mm, 24.3*mm, 24.3*mm, 31.5*mm])  # 총 170mm
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (2, 1), (6, -2), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    return table

# --- sidebar import 경로 보정 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

from sidebar import render_sidebar
from client import api_get, api_post

# -------------------------------
# 페이지 설정 & 커스텀 사이드바
# -------------------------------
st.set_page_config(page_title="입고 내역", page_icon="📊", layout="wide")
render_sidebar("receive")

# 기본 여백/스타일
st.markdown("""
<style>
    .main .block-container {
        max-width: 100%;
        padding-top: 1rem;
        padding-right: 4rem;
        padding-left: 4rem;
        padding-bottom: 1rem;
    }
    div[data-testid="stHorizontalBlock"] { padding-left: 1rem; }
</style>
""", unsafe_allow_html=True)

# -------------------------------
# 세션 상태 초기화
# -------------------------------
if "received_items" not in st.session_state:
    st.session_state.received_items = []
if "partners" not in st.session_state:
    st.session_state.partners = []

# -------------------------------
# 헤더 & 뒤로가기 버튼
# -------------------------------
title_col, button_col = st.columns([4, 1])
with title_col:
    st.title("입고 내역")
with button_col:
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
    if st.button("← 뒤로가기", use_container_width=True, key="back_button"):
        st.switch_page("pages/receive.py")

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# -------------------------------
# 입고 내역 섹션
# -------------------------------
st.subheader("입고 내역")

if len(st.session_state.received_items) == 0:
    st.warning("입고 처리된 내역이 없습니다.")
else:
    # 입고 내역 검색 (Form 형태)
    st.markdown("### 🔍 검색")
    with st.form("receive_history_search_form", clear_on_submit=False):
        st.caption("품목명, 카테고리명, 입고일, 담당자 등으로 검색 가능")
        search_query = st.text_input("검색", key="receive_history_search",
                                     label_visibility="collapsed",
                                     placeholder="품목명, 카테고리명, 입고일(YYYY-MM-DD), 담당자명 등 입력")
        submitted_search = st.form_submit_button("검색", use_container_width=True, type="primary")
        
        # 검색어를 session_state에 저장
        if submitted_search:
            if search_query and search_query.strip():
                st.session_state.receive_history_search_term = search_query.strip()
            else:
                st.session_state.receive_history_search_term = ""
    
    # 검색어 초기화 (세션 상태에 없으면)
    if "receive_history_search_term" not in st.session_state:
        st.session_state.receive_history_search_term = ""
    
    # 검색 필터링 (품목명, 카테고리명, 입고일, 담당자 중 하나라도 매칭되면 표시)
    filtered_received = list(st.session_state.received_items)
    if st.session_state.receive_history_search_term:
        search_lower = st.session_state.receive_history_search_term.lower().strip()
        filtered_received = [
            r for r in filtered_received 
            if (search_lower in r.get("product_name", "").lower() or
                search_lower in r.get("category", "").lower() or
                st.session_state.receive_history_search_term in r.get("receive_date", "") or
                search_lower in r.get("staff", "").lower())
        ]
    
    if len(filtered_received) == 0:
        if st.session_state.receive_history_search_term:
            st.warning("검색 결과가 없습니다.")
        else:
            st.warning("입고 처리된 내역이 없습니다.")
    else:
        if st.session_state.receive_history_search_term:
            st.info(f"검색 결과: {len(filtered_received)}개")
        
        # 처음 10개만 표시
        display_limit = 10
        items_to_display = filtered_received[:display_limit]
        remaining_items = filtered_received[display_limit:] if len(filtered_received) > display_limit else []
        
        # 처음 10개 항목 표시
        for idx, item in enumerate(items_to_display):
            with st.expander(f"{item['product_name']} ({item['product_code']}) - 입고수량: {item.get('actual_qty', 0)}개 - {item.get('receive_date', '-')}", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**품목코드:** {item.get('product_code', '-')}")
                    st.write(f"**품목명:** {item.get('product_name', '-')}")
                    st.write(f"**발주 수량:** {item.get('order_qty', 0)}개")
                    st.write(f"**입고 수량:** {item.get('actual_qty', 0)}개")
                    st.write(f"**발주 단가:** {item.get('order_price', 0):,}원")
                    st.write(f"**입고 단가:** {item.get('actual_price', 0):,}원")
                with col2:
                    st.write(f"**입고일:** {item.get('receive_date', '-')}")
                    st.write(f"**유통기한:** {item.get('expiry', '-')}")
                    st.write(f"**담당자:** {item.get('staff', '-')}")
                    if item.get('special_note'):
                        st.write(f"**특이사항:** {item.get('special_note', '-')}")
                    partner_name = item.get("partner", {}).get("name", "-") if item.get("partner") else "-"
                    st.write(f"**거래처:** {partner_name}")
        
        # 10개 이상일 경우 "더보기" 버튼 표시
        if len(remaining_items) > 0:
            st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)
            more_button_col1, more_button_col2, more_button_col3 = st.columns([1, 1, 1])
            with more_button_col2:
                if "show_more_received_items" not in st.session_state:
                    st.session_state.show_more_received_items = False
                
                if st.button(f"더보기 ({len(remaining_items)}개)", key="show_more_received_btn", use_container_width=True, type="secondary"):
                    st.session_state.show_more_received_items = not st.session_state.show_more_received_items
                    st.rerun()
                
                # 더보기 팝업 (expander 사용)
                if st.session_state.show_more_received_items:
                    st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)
                    with st.expander(f"📋 나머지 입고 내역 ({len(remaining_items)}개)", expanded=True):
                        for idx, item in enumerate(remaining_items):
                            with st.expander(f"{item['product_name']} ({item['product_code']}) - 입고수량: {item.get('actual_qty', 0)}개 - {item.get('receive_date', '-')}", expanded=False):
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.write(f"**품목코드:** {item.get('product_code', '-')}")
                                    st.write(f"**품목명:** {item.get('product_name', '-')}")
                                    st.write(f"**발주 수량:** {item.get('order_qty', 0)}개")
                                    st.write(f"**입고 수량:** {item.get('actual_qty', 0)}개")
                                    st.write(f"**발주 단가:** {item.get('order_price', 0):,}원")
                                    st.write(f"**입고 단가:** {item.get('actual_price', 0):,}원")
                                with col2:
                                    st.write(f"**입고일:** {item.get('receive_date', '-')}")
                                    st.write(f"**유통기한:** {item.get('expiry', '-')}")
                                    st.write(f"**담당자:** {item.get('staff', '-')}")
                                    if item.get('special_note'):
                                        st.write(f"**특이사항:** {item.get('special_note', '-')}")
                                    partner_name = item.get("partner", {}).get("name", "-") if item.get("partner") else "-"
                                    st.write(f"**거래처:** {partner_name}")
                        # 닫기 버튼
                        st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)
                        close_col1, close_col2, close_col3 = st.columns([1, 1, 1])
                        with close_col2:
                            if st.button("닫기", key="close_more_received_btn", use_container_width=True):
                                st.session_state.show_more_received_items = False
                                st.rerun()

# -------------------------------
# 거래명세서 섹션 (입출고 통합)
# -------------------------------
st.markdown("---")
st.subheader("거래명세서 내역 (입출고 통합)")

# 출고 내역 초기화 (없으면 빈 리스트)
if "releases" not in st.session_state:
    st.session_state.releases = []

# 모든 거래 내역 결합 (입고 + 출고)
all_transactions = []
for item in st.session_state.received_items:
    all_transactions.append({
        **item,
        "transaction_type": "매입(입고)",
        "transaction_date": item.get('receive_date', ''),
        "qty": item.get('actual_qty', 0),
        "price": item.get('actual_price', 0)
    })
for item in st.session_state.releases:
    all_transactions.append({
        **item,
        "transaction_type": "매출(출고)",
        "transaction_date": item.get('date', ''),
        "qty": item.get('qty', 0),
        "price": item.get('price', 0),
        "actual_qty": item.get('qty', 0),
        "actual_price": item.get('price', 0),
        "category": item.get('category', ''),
        "unit": item.get('unit', ''),
        "partner": item.get('partner'),
        "special_note": item.get('note', '')
    })

if len(all_transactions) == 0:
    st.warning("거래 내역이 없습니다. 거래명세서를 생성할 수 없습니다.")
else:
    # 간편 설정 처리 (form 밖에서)
    if "invoice_quick_period" in st.session_state:
        quick_period = st.session_state.invoice_quick_period
        if quick_period != "직접 선택":
            if "invoice_quick_period_applied" not in st.session_state or st.session_state.invoice_quick_period_applied != quick_period:
                today = date.today()
                if quick_period == "이번 달":
                    st.session_state.invoice_start_date = today.replace(day=1)
                    st.session_state.invoice_end_date = today
                elif quick_period == "지난달":
                    if today.month == 1:
                        st.session_state.invoice_start_date = date(today.year - 1, 12, 1)
                        st.session_state.invoice_end_date = date(today.year - 1, 12, 31)
                    else:
                        st.session_state.invoice_start_date = date(today.year, today.month - 1, 1)
                        # 지난달 마지막 날
                        if today.month - 1 in [1, 3, 5, 7, 8, 10, 12]:
                            st.session_state.invoice_end_date = date(today.year, today.month - 1, 31)
                        elif today.month - 1 in [4, 6, 9, 11]:
                            st.session_state.invoice_end_date = date(today.year, today.month - 1, 30)
                        else:
                            # 2월 (윤년 체크)
                            if today.year % 4 == 0 and (today.year % 100 != 0 or today.year % 400 == 0):
                                st.session_state.invoice_end_date = date(today.year, 2, 29)
                            else:
                                st.session_state.invoice_end_date = date(today.year, 2, 28)
                elif quick_period == "올해":
                    st.session_state.invoice_start_date = date(today.year, 1, 1)
                    st.session_state.invoice_end_date = today
                elif quick_period == "이번 분기":
                    quarter = (today.month - 1) // 3
                    st.session_state.invoice_start_date = date(today.year, quarter * 3 + 1, 1)
                    st.session_state.invoice_end_date = today
                st.session_state.invoice_quick_period_applied = quick_period
                st.rerun()
    
    # 검색 조건 설정 (Form 형태)
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
                key="invoice_quick_period"
            )
        
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        
        # ② 거래처 선택
        st.markdown("**② 거래처 선택 (필수)**")
        # 거래처 목록 수집 (dict 사용 - set 대신)
        partner_dict = {}
        for trans in all_transactions:
            partner = trans.get("partner")
            if partner:
                partner_key = f"{partner.get('code', '')}_{partner.get('name', '')}"
                if partner_key not in partner_dict:
                    partner_dict[partner_key] = partner
        
        if "partners" in st.session_state and len(st.session_state.partners) > 0:
            # 세션의 partners 목록과 실제 거래 내역의 거래처를 결합
            for p in st.session_state.partners:
                key = f"{p.get('code', '')}_{p.get('name', '')}"
                if key not in partner_dict:
                    partner_dict[key] = p
            
            partner_list = list(partner_dict.values())
            partner_options = ["전체 거래처"] + [f"{p.get('name', '')} ({p.get('code', '')})" for p in partner_list]
            
            selected_partner_text = st.selectbox(
                "거래처 선택",
                options=partner_options,
                key="invoice_partner_select",
                help="여러 거래처를 선택하려면 '전체 거래처'를 선택하세요."
            )
            
            if selected_partner_text == "전체 거래처":
                selected_partner_codes = None  # None이면 전체
            else:
                # 선택된 거래처의 코드 추출
                selected_code = selected_partner_text.split('(')[1].split(')')[0] if '(' in selected_partner_text else None
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
            key="invoice_transaction_type"
        )
        
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        
        # ④ 품목별 필터링
        st.markdown("**④ 품목별 필터링**")
        # 모든 품목 목록 수집
        all_products = set()
        for trans in all_transactions:
            product_name = trans.get('product_name', '')
            if product_name:
                all_products.add(product_name)
        
        product_options = ["전체 품목"] + sorted(list(all_products))
        selected_product = st.selectbox(
            "품목 선택",
            options=product_options,
            key="invoice_product_select",
            help="특정 품목만 필터링하여 조회할 수 있습니다."
        )
        
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        
        # ⑤ 검색 버튼
        search_submitted = st.form_submit_button("🔍 조회하기", use_container_width=True, type="primary")
    
    # 검색 실행
    if search_submitted or "invoice_search_executed" not in st.session_state:
        st.session_state.invoice_search_executed = True
        
        # 필터링 적용
        filtered_transactions = list(all_transactions)
        
        # 날짜 필터링
        if start_date and end_date:
            temp_filtered = []
            for t in filtered_transactions:
                trans_date_str = t.get('transaction_date')
                if trans_date_str:
                    try:
                        trans_date = datetime.strptime(trans_date_str, "%Y-%m-%d").date()
                        if start_date <= trans_date <= end_date:
                            temp_filtered.append(t)
                    except:
                        pass
            filtered_transactions = temp_filtered
        
        # 거래처 필터링
        if selected_partner_codes is not None:
            filtered_transactions = [
                t for t in filtered_transactions
                if t.get('partner') and t.get('partner').get('code') in selected_partner_codes
            ]
        
        # 거래 구분 필터링
        if transaction_type == "매입(입고)":
            filtered_transactions = [t for t in filtered_transactions if t.get('transaction_type') == "매입(입고)"]
        elif transaction_type == "매출(출고)":
            filtered_transactions = [t for t in filtered_transactions if t.get('transaction_type') == "매출(출고)"]
        
        # 품목 필터링
        if selected_product != "전체 품목":
            filtered_transactions = [
                t for t in filtered_transactions
                if t.get('product_name') == selected_product
            ]
        
        st.session_state.filtered_invoice_transactions = filtered_transactions
    else:
        filtered_transactions = st.session_state.get('filtered_invoice_transactions', [])
    
    # 검색 결과 표시
    if len(filtered_transactions) == 0:
        st.warning("검색 조건에 맞는 거래 내역이 없습니다.")
    else:
        st.success(f"검색 결과: {len(filtered_transactions)}건")
        
        # 거래처별로 그룹화
        from collections import defaultdict
        transactions_by_partner = defaultdict(list)
        transactions_without_partner = []
        
        for trans in filtered_transactions:
            partner = trans.get('partner')
            if partner and partner.get('code'):
                partner_key = f"{partner.get('name', '')} ({partner.get('code', '')})"
                transactions_by_partner[partner_key].append(trans)
            else:
                transactions_without_partner.append(trans)
        
        # 거래 내역 테이블 (거래처별로 구분)
        st.markdown("---")
        st.markdown("#### 📊 거래 내역 목록")
        
        # 전체 합계를 위한 변수
        total_supply_all = 0
        total_vat_all = 0
        
        # 거래명세서 PDF 생성 함수 정의 (먼저 정의하여 위에서 사용 가능하도록)
        # PDF 생성 스타일 정의
        st.markdown("""
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
        """, unsafe_allow_html=True)
        
        # 거래명세서 PDF 생성 함수 정의 (먼저 정의)
        selected_date = f"{start_date} ~ {end_date}" if start_date and end_date else "전체"
        
        def generate_invoice_pdf_local(invoice_items, invoice_date, partner_info, show_partner_info=False):
            """
            invoice_items: 거래 내역 리스트
            invoice_date: 날짜 문자열
            partner_info: 거래처 정보 (전체 거래명세서일 경우 기본 거래처)
            show_partner_info: True이면 각 품목에 거래처 정보 표시 (전체 거래명세서용)
            """
            from io import BytesIO
            
            # 한글 폰트 등록
            font_name = register_korean_font()
            styles = _build_styles(font_name)
            
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=15*mm, bottomMargin=15*mm,
                                   leftMargin=20*mm, rightMargin=20*mm)
            elements = []
            
            # 날짜 형식 변환
            if invoice_date == "전체":
                date_str = datetime.now().strftime("%Y년 %m월 %d일")
            else:
                try:
                    # 날짜 범위 처리
                    if ' ~ ' in invoice_date:
                        date_str = invoice_date.replace(' ~ ', ' ~ ')
                    else:
                        date_obj = datetime.strptime(invoice_date, "%Y-%m-%d")
                        date_str = date_obj.strftime("%Y년 %m월 %d일")
                except:
                    date_str = invoice_date
            
            # 날짜를 왼쪽에 배치
            date_para = Paragraph(date_str, ParagraphStyle(
                'DateStyle',
                parent=styles['Normal'],
                fontName=font_name,
                fontSize=11,
                alignment=TA_LEFT
            ))
            elements.append(date_para)
            
            # 제목을 중앙에 큰 폰트로 배치
            title_para = Paragraph("거래명세서", ParagraphStyle(
                'TitleStyle',
                parent=styles['Title'],
                fontName=font_name,
                fontSize=20,
                alignment=TA_CENTER,
                spaceAfter=6
            ))
            elements.append(title_para)
            elements.append(Spacer(1, 8*mm))
            
            # 거래처 정보 테이블 (가운데 정렬 및 너비 통일: 170mm)
            left_table, buyer_info = _build_partner_table(partner_info, font_name)
            partner_wrapper_data = [[left_table, buyer_info]]
            partner_wrapper = Table(partner_wrapper_data, colWidths=[85*mm, 85*mm])
            partner_wrapper.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(partner_wrapper)
            elements.append(Spacer(1, 5*mm))
            
            # 상품 테이블 생성
            items_data = [["품목명", "규격", "수량", "단가", "공급가액", "세액", "비고"]]
            total_amount = 0
            total_vat = 0
            
            for item in invoice_items:
                product_name = item.get('product_name', '-')
                spec = item.get('category', '') or item.get('unit', '') or '-'
                qty = item.get('qty', 0) or item.get('actual_qty', 0)
                price = item.get('price', 0) or item.get('actual_price', 0)
                supply_amount = qty * price
                vat_amount = int(supply_amount * 0.1)
                note = item.get('special_note', '') or item.get('note', '') or '-'
                
                # 전체 거래명세서인 경우 거래처 정보 추가
                if show_partner_info:
                    item_partner = item.get('partner')
                    if item_partner and item_partner.get('name'):
                        partner_name = item_partner.get('name', '')
                        # 품목명에 거래처명 포함: "거래처명 - 품목명"
                        product_name = f"{partner_name} - {product_name}"
                
                total_amount += supply_amount
                total_vat += vat_amount
                
                items_data.append([
                    Paragraph(product_name, ParagraphStyle('Item', fontName=font_name, fontSize=9)),
                    Paragraph(spec, ParagraphStyle('Item', fontName=font_name, fontSize=9)),
                    Paragraph(f"{qty:,}", ParagraphStyle('Item', fontName=font_name, fontSize=9, alignment=TA_RIGHT)),
                    Paragraph(f"{price:,}", ParagraphStyle('Item', fontName=font_name, fontSize=9, alignment=TA_RIGHT)),
                    Paragraph(f"{supply_amount:,}", ParagraphStyle('Item', fontName=font_name, fontSize=9, alignment=TA_RIGHT)),
                    Paragraph(f"{vat_amount:,}", ParagraphStyle('Item', fontName=font_name, fontSize=9, alignment=TA_RIGHT)),
                    Paragraph(note, ParagraphStyle('Item', fontName=font_name, fontSize=9))
                ])
            
            items_table = _build_items_table(items_data, font_name)
            
            # 상품 테이블을 가운데 정렬하기 위해 wrapper 사용 (너비 통일: 170mm)
            center_items_wrapper_data = [[items_table]]
            center_items_wrapper = Table(center_items_wrapper_data, colWidths=[170*mm])
            center_items_wrapper.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('VALIGN', (0, 0), (0, 0), 'TOP'),
            ]))
            elements.append(center_items_wrapper)
            elements.append(Spacer(1, 5*mm))
            
            # 합계 행 (너비 통일: 170mm, 가운데 정렬, 한글 폰트 적용)
            summary_table_data = [
                [
                    Paragraph("합계", ParagraphStyle('Summary', fontName=font_name, fontSize=10)),
                    Paragraph(f"{total_amount:,}", ParagraphStyle('Summary', fontName=font_name, fontSize=10, alignment=TA_RIGHT)),
                    Paragraph(f"{total_vat:,} 부가가치세", ParagraphStyle('Summary', fontName=font_name, fontSize=10, alignment=TA_RIGHT))
                ]
            ]
            summary_table = Table(summary_table_data, colWidths=[30*mm, 40*mm, 100*mm])  # 총 170mm
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#e6e6e6')),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (1, 0), (2, 0), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, -1), font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            
            # 합계 테이블을 가운데 정렬하기 위해 wrapper 사용 (너비 통일: 170mm)
            center_summary_wrapper_data = [[summary_table]]
            center_summary_wrapper = Table(center_summary_wrapper_data, colWidths=[170*mm])
            center_summary_wrapper.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('VALIGN', (0, 0), (0, 0), 'TOP'),
            ]))
            elements.append(center_summary_wrapper)
            elements.append(Spacer(1, 5*mm))
            
            # 결제계좌 섹션
            account_style = ParagraphStyle(
                'AccountStyle',
                parent=styles['Normal'],
                fontSize=10,
                alignment=TA_LEFT,
                fontName=font_name
            )
            elements.append(Paragraph("[결제계좌]-", account_style))
            
            doc.build(elements)
            buffer.seek(0)
            return buffer
        
        # 거래처별로 표시
        for partner_name, partner_transactions in transactions_by_partner.items():
            # 거래처별 헤더
            st.markdown(f"---")
            st.markdown(f"### 🏢 {partner_name}")
            st.info(f"거래처: {partner_name} | 총 {len(partner_transactions)}건")
            
            # 테이블 헤더
            header_cols = st.columns([1.2, 1.5, 1, 1, 1, 1, 1, 1, 1.5])
            with header_cols[0]: st.write("**거래일자**")
            with header_cols[1]: st.write("**품목명**")
            with header_cols[2]: st.write("**규격/단위**")
            with header_cols[3]: st.write("**수량**")
            with header_cols[4]: st.write("**단가**")
            with header_cols[5]: st.write("**공급가액**")
            with header_cols[6]: st.write("**세액**")
            with header_cols[7]: st.write("**거래구분**")
            with header_cols[8]: st.write("**비고**")
            
            # 거래 내역 행
            partner_supply = 0
            partner_vat = 0
            for idx, trans in enumerate(partner_transactions):
                trans_date = trans.get('transaction_date', '-')
                product_name = trans.get('product_name', '-')
                spec = trans.get('category', '') or trans.get('unit', '') or '-'
                qty = trans.get('qty', 0)
                price = trans.get('price', 0)
                supply_amount = qty * price
                vat_amount = int(supply_amount * 0.1)
                trans_type = trans.get('transaction_type', '-')
                note = trans.get('special_note', '') or trans.get('note', '') or '-'
                
                partner_supply += supply_amount
                partner_vat += vat_amount
                total_supply_all += supply_amount
                total_vat_all += vat_amount
                
                row_cols = st.columns([1.2, 1.5, 1, 1, 1, 1, 1, 1, 1.5])
                with row_cols[0]: st.write(trans_date)
                with row_cols[1]: st.write(product_name)
                with row_cols[2]: st.write(spec)
                with row_cols[3]: st.write(f"{qty:,}")
                with row_cols[4]: st.write(f"{price:,}")
                with row_cols[5]: st.write(f"{supply_amount:,}")
                with row_cols[6]: st.write(f"{vat_amount:,}")
                with row_cols[7]: st.write(trans_type)
                with row_cols[8]: st.write(note)
            
            # 거래처별 합계
            partner_total = partner_supply + partner_vat
            st.markdown(f"**{partner_name} 합계:** 공급가액 {partner_supply:,}원 + 세액 {partner_vat:,}원 = **{partner_total:,}원**")
            
            # 거래처별 PDF 다운로드 버튼 (각 거래처 섹션 바로 아래)
            partner_info = partner_transactions[0].get('partner') if partner_transactions else None
            if partner_info:
                # PDF 생성 및 다운로드 버튼
                pdf_buffer = generate_invoice_pdf_local(partner_transactions, selected_date, partner_info)
                
                # 파일명 생성
                if selected_date == "전체":
                    filename = f"거래명세서_{partner_name}_{datetime.now().strftime('%Y%m%d')}.pdf"
                else:
                    date_part = selected_date.replace(' ~ ', '_').replace('-', '')
                    filename = f"거래명세서_{partner_name}_{date_part}.pdf"
                
                # 다운로드 버튼
                st.download_button(
                    label=f"📥 {partner_name} 거래명세서 PDF 다운로드",
                    data=pdf_buffer,
                    file_name=filename,
                    mime="application/pdf",
                    use_container_width=True,
                    key=f"pdf_download_{partner_info.get('code', '')}"
                )
            st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)
        
        # 거래처가 없는 내역 표시
        if transactions_without_partner:
            st.markdown("---")
            st.markdown(f"### ❓ 거래처 미지정")
            st.warning(f"거래처가 지정되지 않은 내역: {len(transactions_without_partner)}건")
            
            # 테이블 헤더
            header_cols = st.columns([1.2, 1.5, 1, 1, 1, 1, 1, 1, 1.5])
            with header_cols[0]: st.write("**거래일자**")
            with header_cols[1]: st.write("**품목명**")
            with header_cols[2]: st.write("**규격/단위**")
            with header_cols[3]: st.write("**수량**")
            with header_cols[4]: st.write("**단가**")
            with header_cols[5]: st.write("**공급가액**")
            with header_cols[6]: st.write("**세액**")
            with header_cols[7]: st.write("**거래구분**")
            with header_cols[8]: st.write("**비고**")
            
            for idx, trans in enumerate(transactions_without_partner):
                trans_date = trans.get('transaction_date', '-')
                product_name = trans.get('product_name', '-')
                spec = trans.get('category', '') or trans.get('unit', '') or '-'
                qty = trans.get('qty', 0)
                price = trans.get('price', 0)
                supply_amount = qty * price
                vat_amount = int(supply_amount * 0.1)
                trans_type = trans.get('transaction_type', '-')
                note = trans.get('special_note', '') or trans.get('note', '') or '-'
                
                total_supply_all += supply_amount
                total_vat_all += vat_amount
                
                row_cols = st.columns([1.2, 1.5, 1, 1, 1, 1, 1, 1, 1.5])
                with row_cols[0]: st.write(trans_date)
                with row_cols[1]: st.write(product_name)
                with row_cols[2]: st.write(spec)
                with row_cols[3]: st.write(f"{qty:,}")
                with row_cols[4]: st.write(f"{price:,}")
                with row_cols[5]: st.write(f"{supply_amount:,}")
                with row_cols[6]: st.write(f"{vat_amount:,}")
                with row_cols[7]: st.write(trans_type)
                with row_cols[8]: st.write(note)
        
        # 전체 합계 정보
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
        
        # 공통 메모
        st.markdown("---")
        st.markdown("#### 📝 공통 메모")
        common_memo = st.text_area(
            "문서 전체에 대한 공통 메모 (예: 입금 계좌: OO은행 123-...)",
            key="invoice_common_memo",
            height=100,
            placeholder="입금 계좌, 특이사항 등을 입력하세요."
        )
        
        # 거래처별로 그룹화 (전체 PDF 생성용)
        pdf_partner_groups = {}
        pdf_no_partner_items = []
        
        for trans in filtered_transactions:
            partner = trans.get('partner')
            if partner and partner.get('code'):
                partner_key = partner.get('code')
                if partner_key not in pdf_partner_groups:
                    pdf_partner_groups[partner_key] = {
                        'partner_info': partner,
                        'items': []
                    }
                pdf_partner_groups[partner_key]['items'].append(trans)
            else:
                pdf_no_partner_items.append(trans)
        
        # 전체 거래 내역 PDF 다운로드 버튼 (맨 밑에 배치)
        st.markdown("---")
        st.markdown("#### 📄 전체 거래명세서 PDF 생성")
        
        # 전체 거래 내역을 하나의 PDF로 생성 (기본 거래처 정보 사용)
        # 여러 거래처가 있을 경우 첫 번째 거래처 정보를 기본으로 사용
        if len(pdf_partner_groups) > 0:
            default_partner_for_all = list(pdf_partner_groups.values())[0]['partner_info']
        else:
            default_partner_for_all = {
                "code": "",
                "name": "전체 거래처",
                "business_number": "",
                "representative": "",
                "address": "",
                "phone": ""
            }
        
        # 전체 거래 내역 PDF 생성 (거래처별로 페이지 구분)
        # 거래처별로 그룹화하여 각 거래처마다 별도 페이지 생성
        def generate_all_partners_invoice_pdf(all_transactions, invoice_date, partner_groups, no_partner_items):
            """여러 거래처의 거래 내역을 거래처별로 페이지를 나눠서 생성"""
            from io import BytesIO
            
            # 한글 폰트 등록
            font_name = register_korean_font()
            styles = _build_styles(font_name)
            
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=15*mm, bottomMargin=15*mm,
                                   leftMargin=20*mm, rightMargin=20*mm)
            elements = []
            
            # 날짜 형식 변환
            if invoice_date == "전체":
                date_str = datetime.now().strftime("%Y년 %m월 %d일")
            else:
                try:
                    if ' ~ ' in invoice_date:
                        date_str = invoice_date.replace(' ~ ', ' ~ ')
                    else:
                        date_obj = datetime.strptime(invoice_date, "%Y-%m-%d")
                        date_str = date_obj.strftime("%Y년 %m월 %d일")
                except:
                    date_str = invoice_date
            
            # 거래처별로 페이지 생성
            for partner_code, partner_data in partner_groups.items():
                partner_info = partner_data['partner_info']
                partner_items = partner_data['items']
                partner_name = partner_info.get('name', '거래처')
                
                # 첫 번째 거래처가 아니면 페이지 나누기
                if elements:
                    elements.append(PageBreak())
                
                # 날짜 표시
                date_para = Paragraph(date_str, ParagraphStyle(
                    'DateStyle',
                    parent=styles['Normal'],
                    fontName=font_name,
                    fontSize=11,
                    alignment=TA_LEFT
                ))
                elements.append(date_para)
                
                # 제목 표시 (거래처명 포함)
                title_text = f"거래명세서 - {partner_name}"
                title_para = Paragraph(title_text, ParagraphStyle(
                    'TitleStyle',
                    parent=styles['Title'],
                    fontName=font_name,
                    fontSize=20,
                    alignment=TA_CENTER,
                    spaceAfter=6
                ))
                elements.append(title_para)
                elements.append(Spacer(1, 8*mm))
                
                # 거래처 정보 테이블
                left_table, buyer_info = _build_partner_table(partner_info, font_name)
                partner_wrapper_data = [[left_table, buyer_info]]
                partner_wrapper = Table(partner_wrapper_data, colWidths=[85*mm, 85*mm])
                partner_wrapper.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                elements.append(partner_wrapper)
                elements.append(Spacer(1, 5*mm))
                
                # 상품 테이블 생성
                items_data = [[
                    Paragraph("품목명", ParagraphStyle('Header', fontName=font_name, fontSize=10)),
                    Paragraph("규격", ParagraphStyle('Header', fontName=font_name, fontSize=10)),
                    Paragraph("수량", ParagraphStyle('Header', fontName=font_name, fontSize=10)),
                    Paragraph("단가", ParagraphStyle('Header', fontName=font_name, fontSize=10)),
                    Paragraph("공급가액", ParagraphStyle('Header', fontName=font_name, fontSize=10)),
                    Paragraph("세액", ParagraphStyle('Header', fontName=font_name, fontSize=10)),
                    Paragraph("비고", ParagraphStyle('Header', fontName=font_name, fontSize=10))
                ]]
                total_amount = 0
                total_vat = 0
                
                for item in partner_items:
                    product_name = item.get('product_name', '-')
                    spec = item.get('category', '') or item.get('unit', '') or '-'
                    qty = item.get('qty', 0) or item.get('actual_qty', 0)
                    price = item.get('price', 0) or item.get('actual_price', 0)
                    supply_amount = qty * price
                    vat_amount = int(supply_amount * 0.1)
                    note = item.get('special_note', '') or item.get('note', '') or '-'
                    
                    total_amount += supply_amount
                    total_vat += vat_amount
                    
                    items_data.append([
                        Paragraph(product_name, ParagraphStyle('Item', fontName=font_name, fontSize=9)),
                        Paragraph(spec, ParagraphStyle('Item', fontName=font_name, fontSize=9)),
                        Paragraph(f"{qty:,}", ParagraphStyle('Item', fontName=font_name, fontSize=9, alignment=TA_RIGHT)),
                        Paragraph(f"{price:,}", ParagraphStyle('Item', fontName=font_name, fontSize=9, alignment=TA_RIGHT)),
                        Paragraph(f"{supply_amount:,}", ParagraphStyle('Item', fontName=font_name, fontSize=9, alignment=TA_RIGHT)),
                        Paragraph(f"{vat_amount:,}", ParagraphStyle('Item', fontName=font_name, fontSize=9, alignment=TA_RIGHT)),
                        Paragraph(note, ParagraphStyle('Item', fontName=font_name, fontSize=9))
                    ])
                
                items_table = _build_items_table(items_data, font_name)
                
                # 상품 테이블을 가운데 정렬하기 위해 wrapper 사용
                center_items_wrapper_data = [[items_table]]
                center_items_wrapper = Table(center_items_wrapper_data, colWidths=[170*mm])
                center_items_wrapper.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                    ('VALIGN', (0, 0), (0, 0), 'TOP'),
                ]))
                elements.append(center_items_wrapper)
                elements.append(Spacer(1, 5*mm))
                
                # 합계 행
                summary_table_data = [
                    [
                        Paragraph("합계", ParagraphStyle('Summary', fontName=font_name, fontSize=10)),
                        Paragraph(f"{total_amount:,}", ParagraphStyle('Summary', fontName=font_name, fontSize=10, alignment=TA_RIGHT)),
                        Paragraph(f"{total_vat:,} 부가가치세", ParagraphStyle('Summary', fontName=font_name, fontSize=10, alignment=TA_RIGHT))
                    ]
                ]
                summary_table = Table(summary_table_data, colWidths=[30*mm, 40*mm, 100*mm])
                summary_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#e6e6e6')),
                    ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                    ('ALIGN', (1, 0), (2, 0), 'RIGHT'),
                    ('FONTNAME', (0, 0), (-1, -1), font_name),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 5),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ]))
                
                center_summary_wrapper_data = [[summary_table]]
                center_summary_wrapper = Table(center_summary_wrapper_data, colWidths=[170*mm])
                center_summary_wrapper.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                    ('VALIGN', (0, 0), (0, 0), 'TOP'),
                ]))
                elements.append(center_summary_wrapper)
                elements.append(Spacer(1, 5*mm))
                
                # 결제계좌 섹션
                account_style = ParagraphStyle(
                    'AccountStyle',
                    parent=styles['Normal'],
                    fontSize=10,
                    alignment=TA_LEFT,
                    fontName=font_name
                )
                elements.append(Paragraph("[결제계좌]-", account_style))
            
            # 거래처 미지정 내역이 있으면 별도 페이지 추가
            if no_partner_items:
                if elements:
                    elements.append(PageBreak())
                
                # 날짜 표시
                date_para = Paragraph(date_str, ParagraphStyle(
                    'DateStyle',
                    parent=styles['Normal'],
                    fontName=font_name,
                    fontSize=11,
                    alignment=TA_LEFT
                ))
                elements.append(date_para)
                
                # 제목 표시
                title_text = "거래명세서 - 거래처 미지정"
                title_para = Paragraph(title_text, ParagraphStyle(
                    'TitleStyle',
                    parent=styles['Title'],
                    fontName=font_name,
                    fontSize=20,
                    alignment=TA_CENTER,
                    spaceAfter=6
                ))
                elements.append(title_para)
                elements.append(Spacer(1, 8*mm))
                
                # 기본 거래처 정보
                default_partner = {
                    "code": "",
                    "name": "거래처 미지정",
                    "business_number": "",
                    "representative": "",
                    "address": "",
                    "phone": ""
                }
                left_table, buyer_info = _build_partner_table(default_partner, font_name)
                partner_wrapper_data = [[left_table, buyer_info]]
                partner_wrapper = Table(partner_wrapper_data, colWidths=[85*mm, 85*mm])
                partner_wrapper.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                elements.append(partner_wrapper)
                elements.append(Spacer(1, 5*mm))
                
                # 상품 테이블 생성
                items_data = [[
                    Paragraph("품목명", ParagraphStyle('Header', fontName=font_name, fontSize=10)),
                    Paragraph("규격", ParagraphStyle('Header', fontName=font_name, fontSize=10)),
                    Paragraph("수량", ParagraphStyle('Header', fontName=font_name, fontSize=10)),
                    Paragraph("단가", ParagraphStyle('Header', fontName=font_name, fontSize=10)),
                    Paragraph("공급가액", ParagraphStyle('Header', fontName=font_name, fontSize=10)),
                    Paragraph("세액", ParagraphStyle('Header', fontName=font_name, fontSize=10)),
                    Paragraph("비고", ParagraphStyle('Header', fontName=font_name, fontSize=10))
                ]]
                total_amount = 0
                total_vat = 0
                
                for item in no_partner_items:
                    product_name = item.get('product_name', '-')
                    spec = item.get('category', '') or item.get('unit', '') or '-'
                    qty = item.get('qty', 0) or item.get('actual_qty', 0)
                    price = item.get('price', 0) or item.get('actual_price', 0)
                    supply_amount = qty * price
                    vat_amount = int(supply_amount * 0.1)
                    note = item.get('special_note', '') or item.get('note', '') or '-'
                    
                    total_amount += supply_amount
                    total_vat += vat_amount
                    
                    items_data.append([
                        Paragraph(product_name, ParagraphStyle('Item', fontName=font_name, fontSize=9)),
                        Paragraph(spec, ParagraphStyle('Item', fontName=font_name, fontSize=9)),
                        Paragraph(f"{qty:,}", ParagraphStyle('Item', fontName=font_name, fontSize=9, alignment=TA_RIGHT)),
                        Paragraph(f"{price:,}", ParagraphStyle('Item', fontName=font_name, fontSize=9, alignment=TA_RIGHT)),
                        Paragraph(f"{supply_amount:,}", ParagraphStyle('Item', fontName=font_name, fontSize=9, alignment=TA_RIGHT)),
                        Paragraph(f"{vat_amount:,}", ParagraphStyle('Item', fontName=font_name, fontSize=9, alignment=TA_RIGHT)),
                        Paragraph(note, ParagraphStyle('Item', fontName=font_name, fontSize=9))
                    ])
                
                items_table = _build_items_table(items_data, font_name)
                center_items_wrapper_data = [[items_table]]
                center_items_wrapper = Table(center_items_wrapper_data, colWidths=[170*mm])
                center_items_wrapper.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                    ('VALIGN', (0, 0), (0, 0), 'TOP'),
                ]))
                elements.append(center_items_wrapper)
                elements.append(Spacer(1, 5*mm))
                
                # 합계 행
                summary_table_data = [
                    [
                        Paragraph("합계", ParagraphStyle('Summary', fontName=font_name, fontSize=10)),
                        Paragraph(f"{total_amount:,}", ParagraphStyle('Summary', fontName=font_name, fontSize=10, alignment=TA_RIGHT)),
                        Paragraph(f"{total_vat:,} 부가가치세", ParagraphStyle('Summary', fontName=font_name, fontSize=10, alignment=TA_RIGHT))
                    ]
                ]
                summary_table = Table(summary_table_data, colWidths=[30*mm, 40*mm, 100*mm])
                summary_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#e6e6e6')),
                    ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                    ('ALIGN', (1, 0), (2, 0), 'RIGHT'),
                    ('FONTNAME', (0, 0), (-1, -1), font_name),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 5),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ]))
                
                center_summary_wrapper_data = [[summary_table]]
                center_summary_wrapper = Table(center_summary_wrapper_data, colWidths=[170*mm])
                center_summary_wrapper.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                    ('VALIGN', (0, 0), (0, 0), 'TOP'),
                ]))
                elements.append(center_summary_wrapper)
                elements.append(Spacer(1, 5*mm))
                
                # 결제계좌 섹션
                account_style = ParagraphStyle(
                    'AccountStyle',
                    parent=styles['Normal'],
                    fontSize=10,
                    alignment=TA_LEFT,
                    fontName=font_name
                )
                elements.append(Paragraph("[결제계좌]-", account_style))
            
            doc.build(elements)
            buffer.seek(0)
            return buffer
        
        # 전체 거래 내역 PDF 생성 (거래처별로 페이지 구분)
        pdf_buffer_all = generate_all_partners_invoice_pdf(filtered_transactions, selected_date, pdf_partner_groups, pdf_no_partner_items)
        
        if selected_date == "전체":
            filename_all = f"거래명세서_전체_{datetime.now().strftime('%Y%m%d')}.pdf"
        else:
            date_part = selected_date.replace(' ~ ', '_').replace('-', '')
            filename_all = f"거래명세서_전체_{date_part}.pdf"
        
        st.download_button(
            label="📥 전체 거래명세서 PDF 다운로드 (모든 거래처 포함)",
            data=pdf_buffer_all,
            file_name=filename_all,
            mime="application/pdf",
            use_container_width=True,
            key="pdf_download_all"
        )
        

