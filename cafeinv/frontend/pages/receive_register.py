import os, sys
import streamlit as st
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
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
# PDF 레이아웃 유틸리티 함수들
# ========================================================================

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

def _build_styles(font_name):
    """공통 스타일을 생성하고 반환"""
    styles = getSampleStyleSheet()
    return styles

def _build_partner_table(partner_info, font_name):
    """거래처 정보 테이블 생성"""
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
    
    # 한글 폰트로 Paragraph 사용
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

def _build_items_table(items_data, font_name):
    """상품 테이블 생성 (한글 폰트 적용)"""
    table = Table(items_data, colWidths=[24.3*mm, 24.3*mm, 17*mm, 24.3*mm, 24.3*mm, 24.3*mm, 31.5*mm])  # 총 170mm
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (2, 1), (6, -2), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),  # 모든 셀에 한글 폰트 적용
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    return table

def generate_invoice_pdf(invoice_items, invoice_date, partner_info):
    """거래명세서 PDF 생성"""
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
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (1, 0), (1, 0), 10),
        ('TOPPADDING', (1, 0), (1, 0), 5),
    ]))
    # 가운데 정렬을 위한 래퍼 테이블
    center_wrapper = Table([[partner_wrapper]], colWidths=[170*mm])
    center_wrapper.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('VALIGN', (0, 0), (0, 0), 'TOP'),
    ]))
    elements.append(center_wrapper)
    elements.append(Spacer(1, 5*mm))
    
    # 안내 문구 (한글 폰트 적용)
    notice_para = Paragraph("아래와 같이 견적합니다.", ParagraphStyle(
        'NoticeStyle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        alignment=TA_LEFT
    ))
    elements.append(notice_para)
    elements.append(Spacer(1, 3*mm))
    
    # 합계금액 계산
    total_supply = 0
    total_vat = 0
    for item in invoice_items:
        qty = item['actual_qty']
        price = item['actual_price']
        supply_amount = qty * price
        vat_amount = int(supply_amount * 0.1)
        total_supply += supply_amount
        total_vat += vat_amount
    
    total_amount = total_supply + total_vat
    korean_amount = number_to_korean(total_amount)
    
    # 합계금액 표시
    total_para = Paragraph(
        f"합계금액 {korean_amount} 원정 (₩ {total_amount:,})",
        ParagraphStyle(
            'TotalAmountStyle',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=12,
            alignment=TA_LEFT,
            spaceAfter=5
        )
    )
    elements.append(total_para)
    elements.append(Spacer(1, 3*mm))
    
    # 상품 테이블 데이터 (한글 폰트 적용)
    table_data = []
    # 헤더를 Paragraph로 변환
    header_row = [
        Paragraph("품명", ParagraphStyle('Header', fontName=font_name, fontSize=10)),
        Paragraph("규격", ParagraphStyle('Header', fontName=font_name, fontSize=10)),
        Paragraph("수량", ParagraphStyle('Header', fontName=font_name, fontSize=10)),
        Paragraph("단가", ParagraphStyle('Header', fontName=font_name, fontSize=10)),
        Paragraph("공급가액", ParagraphStyle('Header', fontName=font_name, fontSize=10)),
        Paragraph("부가세액", ParagraphStyle('Header', fontName=font_name, fontSize=10)),
        Paragraph("비고", ParagraphStyle('Header', fontName=font_name, fontSize=10))
    ]
    table_data.append(header_row)
    
    for item in invoice_items:
        qty = item['actual_qty']
        price = item['actual_price']
        supply_amount = qty * price
        vat_amount = int(supply_amount * 0.1)
        
        spec = item.get('category', '') or item.get('unit', '') or '-'
        
        # 데이터도 Paragraph로 변환하여 한글 폰트 적용
        table_data.append([
            Paragraph(str(item['product_name']), ParagraphStyle('Cell', fontName=font_name, fontSize=9)),
            Paragraph(str(spec), ParagraphStyle('Cell', fontName=font_name, fontSize=9)),
            Paragraph(str(qty), ParagraphStyle('Cell', fontName=font_name, fontSize=9, alignment=TA_RIGHT)),
            Paragraph(f"{price:,}", ParagraphStyle('Cell', fontName=font_name, fontSize=9, alignment=TA_RIGHT)),
            Paragraph(f"{supply_amount:,}", ParagraphStyle('Cell', fontName=font_name, fontSize=9, alignment=TA_RIGHT)),
            Paragraph(f"{vat_amount:,}", ParagraphStyle('Cell', fontName=font_name, fontSize=9, alignment=TA_RIGHT)),
            Paragraph("-", ParagraphStyle('Cell', fontName=font_name, fontSize=9))
        ])
    
    # 상품 테이블 (너비 통일: 170mm, 가운데 정렬)
    items_table = _build_items_table(table_data, font_name)
    center_items_wrapper = Table([[items_table]], colWidths=[170*mm])
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
    center_summary_wrapper = Table([[summary_table]], colWidths=[170*mm])
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

# -------------------------------
# 페이지 설정 & 커스텀 사이드바
# -------------------------------
st.set_page_config(page_title="입고 등록", page_icon="📦", layout="wide")
render_sidebar("receive")

# 기본 여백/스타일
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
# 세션 상태 초기화
# -------------------------------
if "receives" not in st.session_state:
    st.session_state.receives = []
if "received_items" not in st.session_state:
    st.session_state.received_items = []
if "staff_list" not in st.session_state:
    st.session_state.staff_list = ["김철수", "이영희", "박민수", "정수진"]
if "last_received_item" not in st.session_state:
    st.session_state.last_received_item = None
if "receive_completed" not in st.session_state:
    st.session_state.receive_completed = False

# -------------------------------
# 헤더 & 뒤로가기 버튼
# -------------------------------
title_col, button_col = st.columns([4, 1])
with title_col:
    st.title("입고 등록")
with button_col:
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
    if st.button("← 뒤로가기", use_container_width=True, key="back_button"):
        st.switch_page("pages/receive.py")

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# -------------------------------
# 입고 처리 섹션
# -------------------------------
st.subheader("입고 처리")

# 미입고 발주 목록 먼저 처리 (페이지 로드 보장)
# 미입고 발주 목록 (안전하게 처리)
try:
    receives_list = st.session_state.get('receives', [])
    if not isinstance(receives_list, list):
        receives_list = []
    
    unreceived_orders = [r for r in receives_list if isinstance(r, dict) and not r.get("is_received", False)]
except Exception as e:
    st.error(f"발주 목록을 불러오는 중 오류가 발생했습니다: {str(e)}")
    unreceived_orders = []

# 입고 완료 모달 팝오버 (화면 중앙 작은 창) - 페이지 하단에 표시
# 모달 표시 조건 확인 (안전하게 처리)
show_modal = False
try:
    show_modal = (st.session_state.get('receive_completed', False) and 
                  st.session_state.get('last_received_item') is not None)
except:
    show_modal = False

# 미입고 발주 목록 표시 (메인 콘텐츠)
if len(unreceived_orders) == 0:
    st.warning("입고 처리가 필요한 발주가 없습니다.")
else:
    try:
        st.caption("발주 선택")
        # 발주일 포함한 옵션 생성 (누적 입고 수량 포함)
        order_options = []
        for r in unreceived_orders:
            try:
                order_date = r.get('date', '')
                received_qty = r.get('received_qty', 0)
                order_qty = r.get('quantity', 0)
                remaining_qty = max(0, order_qty - received_qty)
                product_name = r.get('product_name', '품목명 없음')
                product_code = r.get('product_code', '코드 없음')
                
                if order_date:
                    try:
                        date_obj = datetime.strptime(str(order_date), "%Y-%m-%d")
                        date_str = date_obj.strftime("%Y-%m-%d")
                    except:
                        date_str = str(order_date)
                else:
                    date_str = "발주일 없음"
                
                # 누적 입고 수량이 있으면 표시
                if received_qty > 0:
                    order_options.append(f"{product_name} ({product_code}) - 발주일: {date_str} - 발주수량: {order_qty}개 (입고: {received_qty}개, 남음: {remaining_qty}개)")
                else:
                    order_options.append(f"{product_name} ({product_code}) - 발주일: {date_str} - 발주수량: {order_qty}개")
            except Exception as e:
                # 개별 발주 항목 처리 중 오류 발생 시 해당 항목만 건너뜀
                continue
        
        if len(order_options) == 0:
            st.warning("표시할 수 있는 발주가 없습니다.")
        else:
            selected_order_idx = st.selectbox("발주 건 선택",
                                              options=range(len(order_options)),
                                              format_func=lambda x: order_options[x],
                                              key="receive_register_order_select", label_visibility="collapsed")

            if selected_order_idx is not None and selected_order_idx < len(unreceived_orders):
                selected_order = unreceived_orders[selected_order_idx]
                order_date = selected_order.get('date', '')
                received_qty = selected_order.get('received_qty', 0)
                order_qty = selected_order.get('quantity', 0)
                remaining_qty = max(0, order_qty - received_qty)
                
                if order_date:
                    try:
                        date_obj = datetime.strptime(str(order_date), "%Y-%m-%d")
                        date_str = date_obj.strftime("%Y-%m-%d")
                        date_display = date_obj.strftime("%Y년 %m월 %d일")
                    except:
                        date_str = str(order_date)
                        date_display = str(order_date)
                else:
                    date_str = "발주일 없음"
                    date_display = "발주일 정보 없음"
                
                # 발주 정보 표시 (발주일은 오늘 날짜로 고정)
                product_name = selected_order.get('product_name', '품목명 없음')
                product_code = selected_order.get('product_code', '코드 없음')
                
                # 오늘 날짜를 한국어 형식으로 표시
                today = datetime.now()
                today_str = today.strftime("%Y년 %m월 %d일")
                
                if received_qty > 0:
                    # 부분 입고된 경우
                    st.warning(f"⚠️ **선택된 발주:** {product_name} ({product_code}) | **발주일:** {today_str} | **발주수량:** {order_qty}개 | **입고완료:** {received_qty}개 | **남은수량:** {remaining_qty}개")
                else:
                    # 처음 입고하는 경우
                    st.info(f"**선택된 발주:** {product_name} ({product_code}) | **발주일:** {today_str} | **발주수량:** {order_qty}개")

                with st.form("receive_register_form", clear_on_submit=True):
                    st.markdown("#### 발주 정보 (발주 등록 시 입력한 정보)")
                    info_col1, info_col2, info_col3, info_col4 = st.columns([1, 1, 1, 1])
                    with info_col1:
                        st.caption("발주일 (오늘 날짜)")
                        # 오늘 날짜를 한국어 형식으로 표시
                        today = datetime.now()
                        today_display = today.strftime("%Y년 %m월 %d일")
                        st.text_input("발주일", value=today_display, key="order_date_display", disabled=True, label_visibility="collapsed", help="입고 등록 시 오늘 날짜로 자동 설정됩니다.")
                    
                    with info_col2:
                        st.caption("발주 수량")
                        st.text_input("발주 수량", value=f"{order_qty}개", key="order_qty_display", disabled=True, label_visibility="collapsed")
                    
                    with info_col3:
                        st.caption("입고 완료 수량")
                        st.text_input("입고 완료 수량", value=f"{received_qty}개", key="received_qty_display", disabled=True, label_visibility="collapsed", help="이미 입고 완료된 수량입니다.")
                    
                    with info_col4:
                        st.caption("남은 수량")
                        st.text_input("남은 수량", value=f"{remaining_qty}개", key="remaining_qty_display", disabled=True, label_visibility="collapsed", help="입고가 필요한 남은 수량입니다.")
                    
                    # 발주 정보 하단에 발주 단가 표시
                    st.markdown("---")
                    info_price_col1, info_price_col2 = st.columns([1, 1])
                    with info_price_col1:
                        st.caption("발주 단가")
                        order_price = selected_order.get('price', 0)
                        st.text_input("발주 단가", value=f"{order_price:,}원", key="order_price_display", disabled=True, label_visibility="collapsed")
                    
                    st.markdown("---")
                    st.markdown("#### 입고 정보")
                    
                    # 입고 속성 선택 (입고 유형, 입고 상태, 거래처)
                    st.markdown("##### 입고 속성")
                    attr_col1, attr_col2, attr_col3 = st.columns([1, 1, 1])
                    with attr_col1:
                        st.caption("입고 유형")
                        receive_type = st.selectbox(
                            "입고 유형",
                            options=["일반 입고", "반품 입고", "교환 입고", "재입고", "기타"],
                            key="receive_register_type",
                            help="입고 유형을 선택하세요.",
                            label_visibility="collapsed"
                        )
                    
                    with attr_col2:
                        st.caption("입고 상태")
                        receive_status = st.selectbox(
                            "입고 상태",
                            options=["정상", "부분 입고", "지연 입고", "불량 입고", "기타"],
                            key="receive_register_status",
                            help="입고 상태를 선택하세요. '부분 입고'를 선택하면 나중에 나머지 품목을 추가 입고할 수 있습니다." if received_qty == 0 else f"입고 상태를 선택하세요. 이미 {received_qty}개가 입고 완료되었습니다.",
                            label_visibility="collapsed"
                        )
                    
                    with attr_col3:
                        st.caption("거래처")
                        # 거래처 정보 가져오기
                        partner_info = selected_order.get('partner')
                        if partner_info:
                            partner_name = partner_info.get('name', '거래처 정보 없음')
                            partner_code = partner_info.get('code', '')
                            if partner_code:
                                partner_display = f"{partner_name} ({partner_code})"
                            else:
                                partner_display = partner_name
                        else:
                            partner_display = "거래처 정보 없음"
                        
                        st.text_input("거래처", value=partner_display, key="partner_display", disabled=True, label_visibility="collapsed", help="발주 등록 시 선택한 거래처입니다.")
                    
                    # 부분 입고 안내
                    if received_qty > 0:
                        st.info(f"📌 현재까지 {received_qty}개 입고 완료. 남은 {remaining_qty}개 입고 시 '부분 입고'를 선택하세요.")
                    
                    st.markdown("---")
                    
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        st.caption("실제 입고 수량")
                        # 부분 입고 시 남은 수량을 기본값으로 설정, 아니면 발주 수량을 기본값으로 설정
                        default_qty = remaining_qty if remaining_qty > 0 else order_qty
                        actual_qty = st.number_input(
                            "실제 입고 수량", 
                            min_value=0, 
                            max_value=remaining_qty if remaining_qty > 0 else None,  # 부분 입고 시 남은 수량을 최대값으로 설정
                            step=1, 
                            value=default_qty,
                            key="receive_register_actual_qty", 
                            label_visibility="collapsed",
                            help=f"발주 수량: {order_qty}개, 이미 입고 완료: {received_qty}개, 남은 수량: {remaining_qty}개" if received_qty > 0 else f"발주 수량: {order_qty}개"
                        )
                        
                        # 부분 입고 안내 메시지
                        if received_qty > 0:
                            st.info(f"💡 이미 {received_qty}개가 입고 완료되었습니다. 남은 {remaining_qty}개를 입고 처리하세요.")

                        st.caption("실제 입고 단가")
                        actual_price = st.number_input("실제 입고 단가", min_value=0, step=100, value=order_price,
                                                       key="receive_register_actual_price", label_visibility="collapsed")
                        
                        st.caption("특이사항")
                        special_note = st.text_area("특이사항", key="receive_register_special_note",
                                                    label_visibility="collapsed",
                                                    placeholder="포장 박스 일부 파손, 유통기한 임박 상품 포함 등", height=100)
                    with col2:
                        st.caption("입고일")
                        receive_date = st.date_input("입고일", key="receive_register_date", label_visibility="collapsed")

                        st.caption("유통기한")
                        receive_expiry = st.date_input("유통기한", key="receive_register_expiry", label_visibility="collapsed")

                        st.caption("담당자")
                        staff_name = st.selectbox("담당자", options=st.session_state.staff_list,
                                                  key="receive_register_staff", label_visibility="collapsed")

                    submitted = st.form_submit_button("입고 완료", use_container_width=True)

                    if submitted:
                        if actual_qty == 0:
                            st.warning("실제 입고 수량을 입력하세요.")
                        else:
                            # 발주에서 현재 누적 입고 수량 가져오기
                            current_received_qty = selected_order.get("received_qty", 0)
                            order_qty = selected_order.get('quantity', 0)
                            
                            # 새로운 누적 입고 수량 계산
                            new_received_qty = current_received_qty + actual_qty
                            
                            # 입고 수량이 발주 수량을 초과하는지 확인
                            if new_received_qty > order_qty:
                                st.warning(f"⚠️ 입고 수량이 발주 수량을 초과합니다. 발주 수량: {order_qty}개, 이미 입고된 수량: {current_received_qty}개, 현재 입고 수량: {actual_qty}개")
                            else:
                                received_item = {
                                    "product_code": selected_order.get("product_code", ""),
                                    "product_name": selected_order.get("product_name", ""),
                                    "category": selected_order.get("category", ""),
                                    "unit": selected_order.get("unit", ""),
                                    "order_qty": order_qty,
                                    "actual_qty": actual_qty,
                                    "accumulated_qty": new_received_qty,  # 누적 입고 수량
                                    "remaining_qty": order_qty - new_received_qty,  # 남은 입고 수량
                                    "order_price": order_price,
                                    "actual_price": actual_price,
                                    "receive_date": str(receive_date),
                                    "expiry": str(receive_expiry),
                                    "staff": staff_name,
                                    "special_note": special_note,
                                    "partner": selected_order.get("partner"),
                                    "receive_type": receive_type,  # 입고 유형
                                    "receive_status": receive_status  # 입고 상태
                                }
                                
                                st.session_state.received_items.append(received_item)
                                st.session_state.last_received_item = received_item  # 최근 입고 아이템 저장
                                st.session_state.receive_completed = True  # 입고 완료 플래그 설정

                                # 발주 데이터 업데이트
                                for i, order in enumerate(st.session_state.receives):
                                    if order == selected_order:
                                        # 누적 입고 수량 업데이트
                                        st.session_state.receives[i]["received_qty"] = new_received_qty
                                        
                                        # 전체 입고 완료 여부 확인
                                        # 누적 입고 수량이 발주 수량과 같거나 크면 완료 처리
                                        # 입고 상태가 "부분 입고"이고 남은 수량이 있으면 미완료 상태 유지
                                        if new_received_qty >= order_qty:
                                            # 누적 입고 수량이 발주 수량과 같거나 크면 완료 처리
                                            st.session_state.receives[i]["is_received"] = True
                                        elif receive_status == "부분 입고" and new_received_qty < order_qty:
                                            # 부분 입고이고 남은 수량이 있으면 미완료 상태 유지 (나중에 추가 입고 가능)
                                            st.session_state.receives[i]["is_received"] = False
                                        else:
                                            # 입고 상태가 "정상"이고 누적 입고 수량이 발주 수량보다 작으면 미완료 상태 유지
                                            st.session_state.receives[i]["is_received"] = False
                                        
                                        break

                                st.rerun()
    except Exception as e:
        st.error(f"입고 등록 처리 중 오류가 발생했습니다: {str(e)}")
        import traceback
        st.error(traceback.format_exc())

# 입고 완료 모달 팝오버 (페이지 하단에 표시)
if show_modal:
    try:
        received_item = st.session_state.get('last_received_item')
        if received_item:
            # 모달 표시 코드는 여기에 추가 (현재는 간단히 성공 메시지만 표시)
            st.success("✅ 입고 처리가 완료되었습니다!")
            if st.button("닫기", key="close_receive_completed_modal"):
                st.session_state.receive_completed = False
                st.session_state.last_received_item = None
                st.rerun()
    except Exception as e:
        # 에러가 발생하면 모달을 표시하지 않음
        pass