# file: login.py
import streamlit as st

DEST_MAIN = "pages/main.py"   # 메인 페이지 경로

st.set_page_config(
    page_title="Stock Mate - 로그인",
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items=None,
)

# ------------------------------------------------
# 세션 기본값
# ------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user" not in st.session_state:
    st.session_state.user = None

# 샘플 데이터가 이미 한 번 세팅되었는지 여부
if "sample_initialized" not in st.session_state:
    st.session_state.sample_initialized = False


# ------------------------------------------------
# 샘플 데이터 세팅 함수
# ------------------------------------------------
def seed_sample_data():
    """처음 로그인할 때 샘플 데이터 주입 (개발 단계: 매번 새로 세팅)"""
    # 방법 1: 개발 중에는 sample_initialized 체크를 잠깐 끔
    # if st.session_state.sample_initialized:
    #     return

    # 1) 카테고리 (원재료 카테고리)
    if "categories" not in st.session_state:
        st.session_state.categories = []

    sample_categories = [
        {"code": "cat_001", "name": "원두"},
        {"code": "cat_002", "name": "시럽"},
        {"code": "cat_003", "name": "유제품"},
        {"code": "cat_004", "name": "토핑"},
        {"code": "cat_005", "name": "디저트"},
    ]
    st.session_state.categories = sample_categories

    # 2) 품목 (원재료)
    if "products" not in st.session_state:
        st.session_state.products = []

    sample_products = [
        {
            "code": "pr_001",
            "category": "원두",
            "name": "에스프레소 원두",
            "unit": "kg",
            "status": "사용",
            "safety": 10,
        },
        {
            "code": "pr_002",
            "category": "원두",
            "name": "디카페인 원두",
            "unit": "kg",
            "status": "사용",
            "safety": 3,
        },
        {
            "code": "pr_003",
            "category": "시럽",
            "name": "카라멜 시럽",
            "unit": "kg",
            "status": "사용",
            "safety": 1,
        },
        {
            "code": "pr_004",
            "category": "시럽",
            "name": "바닐라 시럽",
            "unit": "kg",
            "status": "사용",
            "safety": 1,
        },
        {
            "code": "pr_005",
            "category": "시럽",
            "name": "헤이즐넛 시럽",
            "unit": "kg",
            "status": "사용",
            "safety": 1,
        },
        {
            "code": "pr_006",
            "category": "유제품",
            "name": "우유",
            "unit": "L",
            "status": "사용",
            "safety": 20,
        },
        {
            "code": "pr_007",
            "category": "유제품",
            "name": "두유",
            "unit": "L",
            "status": "사용",
            "safety": 3,
        },
        {
            "code": "pr_008",
            "category": "토핑",
            "name": "휘핑크림",
            "unit": "g",
            "status": "사용",
            "safety": 600,
        },
        {
            "code": "pr_009",
            "category": "토핑",
            "name": "초코 파우더",
            "unit": "kg",
            "status": "사용",
            "safety": 1,
        },
        {
            "code": "pr_010",
            "category": "디저트",
            "name": "버터 크루아상",
            "unit": "개",
            "status": "사용",
            "safety": 5,
        },
        {
            "code": "pr_011",
            "category": "디저트",
            "name": "치즈케이크",
            "unit": "개",
            "status": "사용",
            "safety": 5,
        },
        {
            "code": "pr_012",
            "category": "디저트",
            "name": "브라우니",
            "unit": "개",
            "status": "단종",
            "safety": 0,
        },
    ]
    st.session_state.products = sample_products

    # 3) 거래처
    if "partners" not in st.session_state:
        st.session_state.partners = []

    sample_partners = [
        {
            "code": "pt_001",
            "name": "서울커피유통",
            "business_number": "123-45-67890",
            "representative": "김대표",
            "address": "서울시 강남구 카페로 1",
        },
        {
            "code": "pt_002",
            "name": "스위트시럽상회",
            "business_number": "222-33-44444",
            "representative": "박대표",
            "address": "서울시 마포구 단맛길 12",
        },
        {
            "code": "pt_003",
            "name": "해밀유제품",
            "business_number": "333-44-55555",
            "representative": "이대표",
            "address": "경기도 성남시 우유로 77",
        },
        {
            "code": "pt_004",
            "name": "브레드팩토리",
            "business_number": "444-55-66666",
            "representative": "최대표",
            "address": "서울시 종로구 디저트길 9",
        },
    ]
    st.session_state.partners = sample_partners

    # 4) 관리자
    if "admins" not in st.session_state:
        st.session_state.admins = []

    sample_admins = [
        {
            "emp_no": "2803",
            "name": "장희원",
            "gender": "여",
            "email": "heewon@example.com",
            "phone": "010-1234-5678",
            "position": "매니저",
            "management_type": "출/입고 관리",
            "status": "재직",
        },
        {
            "emp_no": "1001",
            "name": "김카페",
            "gender": "남",
            "email": "manager1@stockmate.com",
            "phone": "010-1111-2222",
            "position": "점장",
            "management_type": "전체 재고 관리",
            "status": "재직",
        },
        {
            "emp_no": "1002",
            "name": "이바리스타",
            "gender": "여",
            "email": "barista1@stockmate.com",
            "phone": "010-3333-4444",
            "position": "파트타이머",
            "management_type": "원두/음료 레시피",
            "status": "재직",
        },
    ]
    st.session_state.admins = sample_admins

    # 최근 등록 항목(Info 페이지에서 쓰는 값들)
    st.session_state.last_registered_category = sample_categories[0]
    st.session_state.last_registered_product = sample_products[0]
    st.session_state.last_registered_partner = sample_partners[0]
    st.session_state.last_registered_admin = sample_admins[0]

    # ------------------------------------------------
    # 5) 발주 / 입고 / 출고 샘플
    # ------------------------------------------------
    # 5-1) 발주 샘플 (order_list 화면용) - 단위 kg / L / 개
    if "orders" not in st.session_state:
        st.session_state.orders = []

    sample_orders = [
        {
            "order_no": "PO-20251120-001",
            "order_date": "2025-11-20",
            "partner_code": "pt_001",
            "partner_name": "서울커피유통",
            "product_code": "pr_001",
            "product_name": "에스프레소 원두",
            "order_qty": 12.0,   # 12 kg
            "order_unit": "kg",
            "expected_date": "2025-11-20",
            "status": "입고완료",
            "staff": "김카페",
            "note": "초기 원두 발주",
        },
        {
            "order_no": "PO-20251120-002",
            "order_date": "2025-11-20",
            "partner_code": "pt_001",
            "partner_name": "서울커피유통",
            "product_code": "pr_002",
            "product_name": "디카페인 원두",
            "order_qty": 3.0,    # 3 kg
            "order_unit": "kg",
            "expected_date": "2025-11-20",
            "status": "입고완료",
            "staff": "김카페",
            "note": "초기 디카페인 발주",
        },
        {
            "order_no": "PO-20251122-001",
            "order_date": "2025-11-22",
            "partner_code": "pt_002",
            "partner_name": "스위트시럽상회",
            "product_code": "pr_003",
            "product_name": "카라멜 시럽",
            "order_qty": 2.0,    # 2 kg
            "order_unit": "kg",
            "expected_date": "2025-11-22",
            "status": "입고완료",
            "staff": "장희원",
            "note": "초기 카라멜 시럽 발주",
        },
        {
            "order_no": "PO-20251122-002",
            "order_date": "2025-11-22",
            "partner_code": "pt_002",
            "partner_name": "스위트시럽상회",
            "product_code": "pr_004",
            "product_name": "바닐라 시럽",
            "order_qty": 2.0,    # 2 kg
            "order_unit": "kg",
            "expected_date": "2025-11-22",
            "status": "입고완료",
            "staff": "장희원",
            "note": "초기 바닐라 시럽 발주",
        },
        {
            "order_no": "PO-20251122-003",
            "order_date": "2025-11-22",
            "partner_code": "pt_002",
            "partner_name": "스위트시럽상회",
            "product_code": "pr_005",
            "product_name": "헤이즐넛 시럽",
            "order_qty": 2.0,    # 2 kg
            "order_unit": "kg",
            "expected_date": "2025-11-22",
            "status": "입고완료",
            "staff": "장희원",
            "note": "초기 헤이즐넛 시럽 발주",
        },
        {
            "order_no": "PO-20251121-001",
            "order_date": "2025-11-21",
            "partner_code": "pt_003",
            "partner_name": "해밀유제품",
            "product_code": "pr_006",
            "product_name": "우유",
            "order_qty": 30.0,   # 30 L
            "order_unit": "L",
            "expected_date": "2025-11-21",
            "status": "입고완료",
            "staff": "이바리스타",
            "note": "초기 우유 발주",
        },
        {
            "order_no": "PO-20251121-002",
            "order_date": "2025-11-21",
            "partner_code": "pt_003",
            "partner_name": "해밀유제품",
            "product_code": "pr_007",
            "product_name": "두유",
            "order_qty": 3.0,    # 3 L
            "order_unit": "L",
            "expected_date": "2025-11-21",
            "status": "입고완료",
            "staff": "이바리스타",
            "note": "초기 두유 발주",
        },
        {
            "order_no": "PO-20251122-004",
            "order_date": "2025-11-22",
            "partner_code": "pt_002",
            "partner_name": "스위트시럽상회",
            "product_code": "pr_008",
            "product_name": "휘핑크림",
            "order_qty": 1.2,    # 1.2 kg (1200 g)
            "order_unit": "kg",
            "expected_date": "2025-11-22",
            "status": "입고완료",
            "staff": "장희원",
            "note": "초기 휘핑크림 발주",
        },
        {
            "order_no": "PO-20251122-005",
            "order_date": "2025-11-22",
            "partner_code": "pt_002",
            "partner_name": "스위트시럽상회",
            "product_code": "pr_009",
            "product_name": "초코 파우더",
            "order_qty": 1.0,    # 1 kg
            "order_unit": "kg",
            "expected_date": "2025-11-22",
            "status": "입고완료",
            "staff": "장희원",
            "note": "초기 초코 파우더 발주",
        },
        {
            "order_no": "PO-20251122-006",
            "order_date": "2025-11-22",
            "partner_code": "pt_004",
            "partner_name": "브레드팩토리",
            "product_code": "pr_010",
            "product_name": "버터 크루아상",
            "order_qty": 10.0,   # 10개
            "order_unit": "개",
            "expected_date": "2025-11-22",
            "status": "입고완료",
            "staff": "장희원",
            "note": "초기 디저트 발주",
        },
    ]
    st.session_state.orders = sample_orders
    st.session_state.last_order = sample_orders[-1]

    # 5-2) 입고/출고 샘플 (네가 처음 준 버전 그대로 유지)
    if "received_items" not in st.session_state:
        st.session_state.received_items = []
    if "releases" not in st.session_state:
        st.session_state.releases = []

    # ✅ 재고 + 유통기한까지 맞춘 입고 샘플
    sample_received_list = [
        # 에스프레소 원두: (12,001g 입고 - 1g 출고) / 1000 ≒ 12 kg
        {
            "product_code": "pr_001",
            "product_name": "에스프레소 원두",
            "category": "원두",
            "unit": "g",
            "order_qty": 12000,
            "actual_qty": 12000,
            "accumulated_qty": 12000,
            "remaining_qty": 0,
            "order_price": 24000,
            "actual_price": 24000,
            "receive_date": "2025-11-20",
            "expiry": "2026-05-20",          # 유통기한
            "staff": "김카페",
            "special_note": "초기 원두 재고",
            "partner": "pt_001",
            "receive_type": "정기 발주",
            "receive_status": "완료",
        },

        # 디카페인 원두: 3000g → 3kg
        {
            "product_code": "pr_002",
            "product_name": "디카페인 원두",
            "category": "원두",
            "unit": "g",
            "order_qty": 3000,
            "actual_qty": 3000,
            "accumulated_qty": 3000,
            "remaining_qty": 0,
            "order_price": 32000,
            "actual_price": 32000,
            "receive_date": "2025-11-20",
            "expiry": "2026-05-20",
            "staff": "김카페",
            "special_note": "초기 디카페인 재고",
            "partner": "pt_001",
            "receive_type": "정기 발주",
            "receive_status": "완료",
        },

        # 카라멜 시럽: (2002mL 입고 - 2mL 출고) / 1000 = 2L
        {
            "product_code": "pr_003",
            "product_name": "카라멜 시럽",
            "category": "시럽",
            "unit": "mL",
            "order_qty": 2000,
            "actual_qty": 2000,
            "accumulated_qty": 2000,
            "remaining_qty": 0,
            "order_price": 12500,
            "actual_price": 12500,
            "receive_date": "2025-11-22",
            "expiry": "2026-11-22",
            "staff": "장희원",
            "special_note": "초기 카라멜 시럽 재고",
            "partner": "pt_002",
            "receive_type": "일반 입고",
            "receive_status": "완료",
        },

        # 바닐라 시럽: 2000mL → 2L
        {
            "product_code": "pr_004",
            "product_name": "바닐라 시럽",
            "category": "시럽",
            "unit": "mL",
            "order_qty": 2000,
            "actual_qty": 2000,
            "accumulated_qty": 2000,
            "remaining_qty": 0,
            "order_price": 12500,
            "actual_price": 12500,
            "receive_date": "2025-11-22",
            "expiry": "2026-11-22",
            "staff": "장희원",
            "special_note": "초기 바닐라 시럽 재고",
            "partner": "pt_002",
            "receive_type": "일반 입고",
            "receive_status": "완료",
        },

        # 헤이즐넛 시럽: 2000mL → 2L
        {
            "product_code": "pr_005",
            "product_name": "헤이즐넛 시럽",
            "category": "시럽",
            "unit": "mL",
            "order_qty": 2000,
            "actual_qty": 2000,
            "accumulated_qty": 2000,
            "remaining_qty": 0,
            "order_price": 12500,
            "actual_price": 12500,
            "receive_date": "2025-11-22",
            "expiry": "2026-11-22",
            "staff": "장희원",
            "special_note": "초기 헤이즐넛 시럽 재고",
            "partner": "pt_002",
            "receive_type": "일반 입고",
            "receive_status": "완료",
        },

        # 우유: 30000mL → 30L
        {
            "product_code": "pr_006",
            "product_name": "우유",
            "category": "유제품",
            "unit": "mL",
            "order_qty": 30000,
            "actual_qty": 30000,
            "accumulated_qty": 30000,
            "remaining_qty": 0,
            "order_price": 2000,
            "actual_price": 2000,
            "receive_date": "2025-11-21",
            "expiry": "2025-11-28",          # 우유라 짧게
            "staff": "이바리스타",
            "special_note": "초기 우유 재고",
            "partner": "pt_003",
            "receive_type": "긴급 입고",
            "receive_status": "완료",
        },

        # 두유: 3000mL → 3L
        {
            "product_code": "pr_007",
            "product_name": "두유",
            "category": "유제품",
            "unit": "mL",
            "order_qty": 3000,
            "actual_qty": 3000,
            "accumulated_qty": 3000,
            "remaining_qty": 0,
            "order_price": 3000,
            "actual_price": 3000,
            "receive_date": "2025-11-21",
            "expiry": "2025-12-05",
            "staff": "이바리스타",
            "special_note": "초기 두유 재고",
            "partner": "pt_003",
            "receive_type": "긴급 입고",
            "receive_status": "완료",
        },

        # 휘핑크림: 1200g
        {
            "product_code": "pr_008",
            "product_name": "휘핑크림",
            "category": "토핑",
            "unit": "g",
            "order_qty": 1200,
            "actual_qty": 1200,
            "accumulated_qty": 1200,
            "remaining_qty": 0,
            "order_price": 10000,
            "actual_price": 10000,
            "receive_date": "2025-11-22",
            "expiry": "2026-02-22",
            "staff": "장희원",
            "special_note": "초기 휘핑크림 재고",
            "partner": "pt_002",
            "receive_type": "일반 입고",
            "receive_status": "완료",
        },

        # 초코 파우더: 1000g → 1kg
        {
            "product_code": "pr_009",
            "product_name": "초코 파우더",
            "category": "토핑",
            "unit": "g",
            "order_qty": 1000,
            "actual_qty": 1000,
            "accumulated_qty": 1000,
            "remaining_qty": 0,
            "order_price": 18000,
            "actual_price": 18000,
            "receive_date": "2025-11-22",
            "expiry": "2027-11-22",
            "staff": "장희원",
            "special_note": "초기 초코 파우더 재고",
            "partner": "pt_002",
            "receive_type": "일반 입고",
            "receive_status": "완료",
        },

        # 버터 크루아상: 10개 입고 (5개 출고 샘플 → 현재 재고 5개)
        {
            "product_code": "pr_010",
            "product_name": "버터 크루아상",
            "category": "디저트",
            "unit": "개",
            "order_qty": 10,
            "actual_qty": 10,
            "accumulated_qty": 10,
            "remaining_qty": 0,
            "order_price": 600,
            "actual_price": 600,
            "receive_date": "2025-11-22",
            "expiry": "2025-11-25",          # 디저트라 짧게
            "staff": "장희원",
            "special_note": "초기 디저트 재고",
            "partner": "pt_004",
            "receive_type": "일반 입고",
            "receive_status": "완료",
        },
    ]

    st.session_state.received_items = sample_received_list

    sample_releases = [
        {
            "product_code": "pr_003",
            "product_name": "카라멜 시럽",
            "qty": 2,
            "reason": "샘플 음료 제조",
        },
        {
            "product_code": "pr_001",
            "product_name": "에스프레소 원두",
            "qty": 1,
            "reason": "바리스타 교육용 사용",
        },
        {
            "product_code": "pr_010",
            "product_name": "버터 크루아상",
            "qty": 5,
            "reason": "디저트 진열",
        },
    ]
    st.session_state.releases = sample_releases

    st.session_state.last_received_item = sample_received_list[-1]
    st.session_state.receive_completed = True

    # 6) 메뉴 카테고리 (레시피용)
    if "menu_categories" not in st.session_state:
        st.session_state.menu_categories = []

    sample_menu_categories = [
        {"code": "menu_cat_001", "name": "커피"},
        {"code": "menu_cat_002", "name": "라떼"},
        {"code": "menu_cat_003", "name": "에이드"},
        {"code": "menu_cat_004", "name": "스무디"},
        {"code": "menu_cat_005", "name": "디저트"},
    ]
    st.session_state.menu_categories = sample_menu_categories

    # 7) 레시피 샘플 (메뉴 10개)
    if "recipes" not in st.session_state:
        st.session_state.recipes = {}

    sample_recipes = {
        "아메리카노": {
            "category": "커피",
            "price": 4000,
            "ingredients": [
                {
                    "ingredient_code": "pr_001",
                    "ingredient_name": "에스프레소 원두",
                    "qty": 18.0,
                    "unit": "g",
                },
            ],
            "option_groups": [],
            "options": [],
        },
        "아이스 아메리카노": {
            "category": "커피",
            "price": 4300,
            "ingredients": [
                {
                    "ingredient_code": "pr_001",
                    "ingredient_name": "에스프레소 원두",
                    "qty": 18.0,
                    "unit": "g",
                },
            ],
            "option_groups": [],
            "options": [],
        },
        "카페라떼": {
            "category": "라떼",
            "price": 4500,
            "ingredients": [
                {
                    "ingredient_code": "pr_001",
                    "ingredient_name": "에스프레소 원두",
                    "qty": 18.0,
                    "unit": "g",
                },
                {
                    "ingredient_code": "pr_006",
                    "ingredient_name": "우유",
                    "qty": 180.0,
                    "unit": "ml",
                },
            ],
            "option_groups": [],
            "options": [],
        },
        "바닐라라떼": {
            "category": "라떼",
            "price": 4800,
            "ingredients": [
                {
                    "ingredient_code": "pr_001",
                    "ingredient_name": "에스프레소 원두",
                    "qty": 18.0,
                    "unit": "g",
                },
                {
                    "ingredient_code": "pr_006",
                    "ingredient_name": "우유",
                    "qty": 180.0,
                    "unit": "ml",
                },
                {
                    "ingredient_code": "pr_004",
                    "ingredient_name": "바닐라 시럽",
                    "qty": 20.0,
                    "unit": "ml",
                },
            ],
            "option_groups": [],
            "options": [],
        },
        "헤이즐넛라떼": {
            "category": "라떼",
            "price": 4800,
            "ingredients": [
                {
                    "ingredient_code": "pr_001",
                    "ingredient_name": "에스프레소 원두",
                    "qty": 18.0,
                    "unit": "g",
                },
                {
                    "ingredient_code": "pr_006",
                    "ingredient_name": "우유",
                    "qty": 180.0,
                    "unit": "ml",
                },
                {
                    "ingredient_code": "pr_005",
                    "ingredient_name": "헤이즐넛 시럽",
                    "qty": 20.0,
                    "unit": "ml",
                },
            ],
            "option_groups": [],
            "options": [],
        },
        "카라멜 마키아또": {
            "category": "라떼",
            "price": 5000,
            "ingredients": [
                {
                    "ingredient_code": "pr_001",
                    "ingredient_name": "에스프레소 원두",
                    "qty": 18.0,
                    "unit": "g",
                },
                {
                    "ingredient_code": "pr_006",
                    "ingredient_name": "우유",
                    "qty": 150.0,
                    "unit": "ml",
                },
                {
                    "ingredient_code": "pr_003",
                    "ingredient_name": "카라멜 시럽",
                    "qty": 25.0,
                    "unit": "ml",
                },
                {
                    "ingredient_code": "pr_008",
                    "ingredient_name": "휘핑크림",
                    "qty": 15.0,
                    "unit": "g",
                },
            ],
            "option_groups": [],
            "options": [],
        },
        "디카페인 아메리카노": {
            "category": "커피",
            "price": 4300,
            "ingredients": [
                {
                    "ingredient_code": "pr_002",
                    "ingredient_name": "디카페인 원두",
                    "qty": 18.0,
                    "unit": "g",
                },
            ],
            "option_groups": [],
            "options": [],
        },
        "카푸치노": {
            "category": "커피",
            "price": 4700,
            "ingredients": [
                {
                    "ingredient_code": "pr_001",
                    "ingredient_name": "에스프레소 원두",
                    "qty": 18.0,
                    "unit": "g",
                },
                {
                    "ingredient_code": "pr_006",
                    "ingredient_name": "우유",
                    "qty": 120.0,
                    "unit": "ml",
                },
                {
                    "ingredient_code": "pr_008",
                    "ingredient_name": "휘핑크림",
                    "qty": 10.0,
                    "unit": "g",
                },
            ],
            "option_groups": [],
            "options": [],
        },
        "카페모카": {
            "category": "라떼",
            "price": 5000,
            "ingredients": [
                {
                    "ingredient_code": "pr_001",
                    "ingredient_name": "에스프레소 원두",
                    "qty": 18.0,
                    "unit": "g",
                },
                {
                    "ingredient_code": "pr_006",
                    "ingredient_name": "우유",
                    "qty": 150.0,
                    "unit": "ml",
                },
                {
                    "ingredient_code": "pr_009",
                    "ingredient_name": "초코 파우더",
                    "qty": 10.0,
                    "unit": "g",
                },
                {
                    "ingredient_code": "pr_008",
                    "ingredient_name": "휘핑크림",
                    "qty": 10.0,
                    "unit": "g",
                },
            ],
            "option_groups": [],
            "options": [],
        },
        "치즈케이크 세트": {
            "category": "디저트",
            "price": 8000,
            "ingredients": [
                {
                    "ingredient_code": "pr_011",
                    "ingredient_name": "치즈케이크",
                    "qty": 1.0,
                    "unit": "개",
                },
                {
                    "ingredient_code": "pr_001",
                    "ingredient_name": "에스프레소 원두",
                    "qty": 18.0,
                    "unit": "g",
                },
            ],
            "option_groups": [],
            "options": [],
        },
    }

    # 예시 옵션 그룹 추가 (우유 변경)
    sample_recipes["카페라떼"]["option_groups"] = [
        {
            "group_name": "우유 선택",
            "required": False,
            "options": [
                {
                    "option_name": "일반 우유",
                    "additional_price": 0,
                    "ingredient_code": "pr_006",
                    "ingredient_name": "우유",
                    "qty": 0.0,
                    "unit": "ml",
                },
                {
                    "option_name": "두유 변경",
                    "additional_price": 500,
                    "ingredient_code": "pr_007",
                    "ingredient_name": "두유",
                    "qty": 180.0,
                    "unit": "ml",
                },
            ],
        }
    ]

    st.session_state.recipes = sample_recipes

    # 한 번만 실행되도록 플래그(지금은 체크 안 쓰지만 남겨둠)
    st.session_state.sample_initialized = True


# ------------------------------------------------
# 이미 로그인된 상태면 바로 메인으로 보내기
# ------------------------------------------------
if st.session_state.logged_in:
    seed_sample_data()
    st.switch_page(DEST_MAIN)
    st.stop()

# ------------------------------------------------
# 로그인 화면 UI
# ------------------------------------------------
st.markdown(
    """
    <style>
    .login-box {
        max-width: 480px;
        margin: 80px auto;
        padding: 40px 48px;
        border-radius: 16px;
        background-color: #111827;
        border: 1px solid #1f2937;
        box-shadow: 0 24px 60px rgba(0,0,0,0.45);
        color: #e5e7eb;
    }
    .login-title {
        font-size: 32px;
        font-weight: 700;
        text-align: center;
        margin-bottom: 4px;
    }
    .login-subtitle {
        font-size: 14px;
        text-align: center;
        color: #9ca3af;
        margin-bottom: 32px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.container():
    st.markdown(
        """
        <div class="login-box">
            <div style="text-align:center; margin-bottom: 24px;">
                <span style="font-size: 20px; padding: 8px 16px; border-radius: 999px;
                             background-color:#1f2937; color:#f97316; font-weight:600;">
                    🔒 Stock Mate 로그인
                </span>
            </div>
            <div class="login-title">Stock Mate 로그인</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Streamlit 컴포넌트는 HTML 블록 바깥에서 그려야 함
with st.form("login_form", clear_on_submit=False):
    st.write("")  # 살짝 여백
    uid = st.text_input("사번번호", placeholder="사번입력")
    pw = st.text_input("비밀번호", type="password", placeholder="비밀번호")
    login_clicked = st.form_submit_button("로그인", use_container_width=True)

if login_clicked:
    if not uid or not pw:
        st.warning("아이디와 비밀번호를 모두 입력하세요.")
    else:
        # 단순 시연용 로그인 처리
        st.session_state.user = uid
        st.session_state.logged_in = True

        # 로그인 성공 시 샘플 데이터 세팅
        seed_sample_data()

        st.success("로그인 성공! 메인 화면으로 이동합니다.")
        st.switch_page(DEST_MAIN)
        st.stop()
