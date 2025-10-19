import os, sys
import streamlit as st  # ✅ 반드시 필요!

# --- sidebar import 경로 보정 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))  # ../frontend
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

from sidebar import render_sidebar
from client import api_get, api_post   # ✅ 공통 사이드바 불러오기


# -------------------------------
# 페이지 설정 & 커스텀 사이드바
# -------------------------------
st.set_page_config(page_title="기본정보", page_icon="⚙️", layout="wide")
render_sidebar("info")  # ✅ 왼쪽에 우리가 만든 네비만 표시

# 기본 여백/스타일 (원본 유지)
st.markdown("""
<style>
    .main .block-container {
        max-width: 100%;
        padding-top: 1rem; padding-right: 1rem; padding-left: 1rem; padding-bottom: 1rem;
    }
    div[data-testid="stHorizontalBlock"] { padding-left: 1rem; }
    button[data-testid="baseButton-secondary"]:hover {
        background-color: #d3d3d3 !important; border-color: #d3d3d3 !important;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------
# 헤더 & HOME 버튼
# -------------------------------
title_col, button_col = st.columns([4, 1])
with title_col:
    st.title("기본정보")
with button_col:
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
    if st.button("HOME 🏠", use_container_width=True, key="home_button"):
        st.switch_page("main.py")   # 필요시 "pages/Home.py" 등으로 변경

st.write("상품, 거래처 등 기본 정보를 관리하는 화면을 여기에 구성할 수 있습니다.")
st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# -------------------------------
# 탭
# -------------------------------
category_tab, product_tab, partner_tab, admin_tab = st.tabs(
    ["카테고리 등록", "품목 등록", "거래처 관리", "관리자 등록"]
)

# -------------------------------
# 세션 상태 초기화
# -------------------------------
if "categories" not in st.session_state:
    st.session_state.categories = []
if "category_selected" not in st.session_state:
    st.session_state.category_selected = set()
if "category_edit_mode" not in st.session_state:
    st.session_state.category_edit_mode = False

if "products" not in st.session_state:
    st.session_state.products = []
if "product_selected" not in st.session_state:
    st.session_state.product_selected = set()
if "product_edit_mode" not in st.session_state:
    st.session_state.product_edit_mode = False

if "partners" not in st.session_state:
    st.session_state.partners = []
if "partner_selected" not in st.session_state:
    st.session_state.partner_selected = set()
if "partner_edit_mode" not in st.session_state:
    st.session_state.partner_edit_mode = False

if "admins" not in st.session_state:
    st.session_state.admins = []
if "admin_selected" not in st.session_state:
    st.session_state.admin_selected = set()
if "admin_edit_mode" not in st.session_state:
    st.session_state.admin_edit_mode = False

# ===============================
# 카테고리 탭
# ===============================
with category_tab:
    st.subheader("카테고리 등록")

    with st.form("category_form", clear_on_submit=True):
        form_col1, form_col2, form_col3 = st.columns([2, 3, 1])
        with form_col1:
            st.caption("코드번호")
            cat_code = st.text_input("코드번호", key="cat_code_input", label_visibility="collapsed", placeholder="cat_001")
        with form_col2:
            st.caption("카테고리명")
            cat_name = st.text_input("카테고리명", key="cat_name_input", label_visibility="collapsed", placeholder="원두")
        with form_col3:
            st.markdown("<div style='height: 37px'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button("등록", use_container_width=True)

        if submitted:
            code = (cat_code or "").strip()
            name = (cat_name or "").strip()
            if not code or not name:
                st.warning("코드번호와 카테고리명을 모두 입력하세요.")
            elif any(c["code"] == code for c in st.session_state.categories):
                st.error("이미 존재하는 코드번호입니다.")
            else:
                # TODO: 서버 저장으로 바꿀 때 → resp, err = api_post("/catalog/categories", {"code": code, "name": name})
                st.session_state.categories.append({"code": code, "name": name})
                st.success("등록되었습니다.")
                st.rerun()

    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

    title_col, del_col1, del_col2 = st.columns([6, 1, 1])
    with title_col:
        st.subheader("카테고리 목록")
    with del_col1:
        if st.button("선택 삭제", key="btn_sel_del", use_container_width=True):
            if not st.session_state.category_selected:
                st.info("삭제할 항목을 선택하세요.")
            else:
                for i in sorted(st.session_state.category_selected, reverse=True):
                    if 0 <= i < len(st.session_state.categories):
                        st.session_state.categories.pop(i)
                st.session_state.category_selected = set()
                st.success("선택한 항목을 삭제했습니다.")
                st.rerun()
    with del_col2:
        if st.button("전체 삭제", key="btn_all_del", use_container_width=True):
            st.session_state.categories = []
            st.session_state.category_selected = set()
            st.success("전체 항목을 삭제했습니다.")
            st.rerun()

    with st.form("category_list_form"):
        if len(st.session_state.categories) == 0:
            st.warning("등록된 카테고리가 없습니다")
            st.form_submit_button("", use_container_width=True, help="")
        else:
            edit_col1, edit_col2, edit_col3 = st.columns([4, 1, 1])
            with edit_col1:
                st.write("")
            with edit_col2:
                if st.session_state.category_edit_mode:
                    if st.form_submit_button("저장", use_container_width=True):
                        for idx, row in enumerate(st.session_state.categories):
                            new_code = st.session_state.get(f"cat_code_{idx}", row["code"]).strip()
                            new_name = st.session_state.get(f"cat_name_{idx}", row["name"]).strip()
                            if any(c["code"] == new_code and i != idx for i, c in enumerate(st.session_state.categories)):
                                st.error(f"'{new_code}'는 이미 존재하는 코드번호입니다.")
                            else:
                                st.session_state.categories[idx] = {"code": new_code, "name": new_name}
                        st.session_state.category_edit_mode = False
                        st.success("저장되었습니다.")
                        st.rerun()
                else:
                    if st.form_submit_button("수정", use_container_width=True):
                        st.session_state.category_edit_mode = True
                        st.rerun()
            with edit_col3:
                st.write("")

            st.markdown("""
            <div style="max-height: 400px; overflow-y: auto;">
            """, unsafe_allow_html=True)

            for idx, row in enumerate(st.session_state.categories):
                cat_col1, cat_col2, cat_col3 = st.columns([2, 3, 1])
                with cat_col1:
                    st.caption("코드번호")
                    st.text_input("코드번호", value=row["code"], key=f"cat_code_{idx}",
                                  disabled=not st.session_state.category_edit_mode, label_visibility="collapsed")
                with cat_col2:
                    st.caption("카테고리명")
                    st.text_input("카테고리명", value=row["name"], key=f"cat_name_{idx}",
                                  disabled=not st.session_state.category_edit_mode, label_visibility="collapsed")
                with cat_col3:
                    st.caption("\u00A0")
                    st.markdown("<div style='height: 37px'></div>", unsafe_allow_html=True)
                    checked = st.checkbox("", key=f"cat_sel_{idx}")
                    if checked:
                        st.session_state.category_selected.add(idx)
                    else:
                        st.session_state.category_selected.discard(idx)

            st.markdown("</div>", unsafe_allow_html=True)

# ===============================
# 품목 탭
# ===============================
with product_tab:
    st.subheader("품목 등록")

    default_code = ""; default_cat = ""; default_name = ""
    default_unit = ""; default_status = True

    with st.form("product_form", clear_on_submit=True):
        r1c1, r1c2, r1c3 = st.columns([2, 3, 3])
        with r1c1:
            st.caption("코드번호")
            pr_code = st.text_input("코드번호", value=default_code, key="prod_code_input",
                                    label_visibility="collapsed", placeholder="pr_001")
        with r1c2:
            st.caption("카테고리명")
            category_names = [c["name"] for c in st.session_state.categories]
            if category_names:
                default_index = category_names.index(default_cat) if default_cat in category_names else 0
                pr_category = st.selectbox("카테고리명", options=category_names, index=default_index,
                                           key="prod_category_select", label_visibility="collapsed")
            else:
                pr_category = st.text_input("카테고리명", value=default_cat, key="prod_category_input_fallback",
                                            label_visibility="collapsed", placeholder="원두")
                st.info("카테고리를 먼저 등록하면 여기에서 선택할 수 있습니다.")
        with r1c3:
            st.caption("품목 명")
            pr_name = st.text_input("품목 명", value=default_name, key="prod_name_input",
                                    label_visibility="collapsed", placeholder="디카페인 원두")

        r2c1, r2c2, r2c3, r2c4 = st.columns([2, 2, 2, 1])
        with r2c1:
            st.caption("입고 단위")
            unit_options = ["병", "박스", "kg", "갯수", "기타"]
            default_unit_index = unit_options.index(default_unit) if default_unit in unit_options else 0
            pr_unit = st.selectbox("입고 단위", options=unit_options, index=default_unit_index,
                                   key="prod_unit_select", label_visibility="collapsed")
        with r2c2:
            st.caption("상태")
            default_status_label = "사용" if default_status else "단종"
            pr_status = st.selectbox("", options=["사용", "단종"],
                                     index=(0 if default_status_label == "사용" else 1),
                                     label_visibility="collapsed")
        with r2c3:
            st.caption("안전재고")
            pr_safety = st.number_input("안전재고", min_value=0, step=1, value=0,
                                        key="prod_safety_input", label_visibility="collapsed")
        with r2c4:
            st.caption("\u00A0"); st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            pr_submitted = st.form_submit_button("등록", use_container_width=True)

        if pr_submitted:
            code = (pr_code or "").strip()
            cat  = (pr_category or "").strip()
            name = (pr_name or "").strip()
            unit = (pr_unit or "").strip()
            if not code or not name:
                st.warning("코드번호와 품목명을 입력하세요.")
            else:
                if any(p["code"] == code for p in st.session_state.products):
                    st.error("이미 존재하는 코드번호입니다.")
                else:
                    # TODO: 서버 저장 전환 → api_post("/catalog/items", {...})
                    st.session_state.products.append({
                        "code": code, "category": cat, "name": name, "unit": unit,
                        "status": pr_status, "safety": int(pr_safety)
                    })
                    st.success("등록되었습니다.")
                    st.rerun()

    st.markdown("<div style='height:48px'></div>", unsafe_allow_html=True)

    # 검색
    search_col1, search_col2 = st.columns([1, 1])
    with search_col1:
        category_search = st.text_input("카테고리명으로 검색", key="category_search", placeholder="카테고리명 입력")
    with search_col2:
        product_search = st.text_input("품목명으로 검색", key="product_search", placeholder="품목명 입력")

    filtered_products = st.session_state.products
    if category_search:
        filtered_products = [p for p in filtered_products if category_search.lower() in p["category"].lower()]
    if product_search:
        filtered_products = [p for p in filtered_products if product_search.lower() in p["name"].lower()]

    with st.form("product_list_form"):
        if st.session_state.product_edit_mode:
            title_col, btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([5, 1, 1, 1, 1])
            with title_col:
                st.subheader("품목 목록")
            with btn_col1:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("선택 삭제", use_container_width=True):
                    if not st.session_state.product_selected:
                        st.info("삭제할 항목을 선택하세요.")
                    else:
                        for i in sorted(st.session_state.product_selected, reverse=True):
                            if 0 <= i < len(st.session_state.products):
                                st.session_state.products.pop(i)
                        st.session_state.product_selected = set()
                        st.success("선택한 항목을 삭제했습니다.")
                        st.rerun()
            with btn_col2:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("전체 삭제", use_container_width=True):
                    st.session_state.products = []
                    st.session_state.product_selected = set()
                    st.success("전체 항목을 삭제했습니다.")
                    st.rerun()
            with btn_col3:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("저장", use_container_width=True):
                    for idx, row in enumerate(st.session_state.products):
                        new_code = st.session_state.get(f"prod_code_{idx}", row["code"]).strip()
                        new_name = st.session_state.get(f"prod_name_{idx}", row["name"]).strip()
                        new_unit = st.session_state.get(f"prod_unit_{idx}", row["unit"]).strip()
                        new_status = st.session_state.get(f"prod_status_{idx}", row["status"]).strip()
                        new_safety = int(st.session_state.get(f"prod_safety_{idx}", row.get("safety", 0)))

                        if any(p["code"] == new_code and i != idx for i, p in enumerate(st.session_state.products)):
                            st.error(f"'{new_code}'는 이미 존재하는 코드번호입니다.")
                        else:
                            st.session_state.products[idx] = {
                                "code": new_code, "category": row["category"], "name": new_name,
                                "unit": new_unit, "status": new_status, "safety": new_safety
                            }
                    st.session_state.product_edit_mode = False
                    st.success("저장되었습니다."); st.rerun()
            with btn_col4:
                st.write("")
        else:
            title_col, btn_col = st.columns([5, 1])
            with title_col:
                st.subheader("품목 목록")
            with btn_col:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("수정", use_container_width=True):
                    st.session_state.product_edit_mode = True; st.rerun()

        if len(st.session_state.products) == 0:
            st.warning("등록된 품목이 없습니다"); st.form_submit_button("", use_container_width=True, help="")
        elif len(filtered_products) == 0:
            st.warning("검색 결과가 없습니다"); st.form_submit_button("", use_container_width=True, help="")
        else:
            if category_search or product_search:
                st.write(f"검색 결과: {len(filtered_products)}개")

            ph1, ph2, ph3, ph4, ph5, ph6, ph7 = st.columns([0.8, 2, 3, 1.2, 1.2, 1.2, 1.2])
            with ph1: st.write(" ")
            with ph2: st.write("**코드번호**")
            with ph3: st.write("**품목명**")
            with ph4: st.write("**단위**")
            with ph5: st.write("**상태**")
            with ph6: st.write("**안전재고**")
            with ph7: st.write("**작업**")

            for filtered_idx, pr in enumerate(filtered_products):
                original_idx = next(i for i, p in enumerate(st.session_state.products) if p == pr)
                c1, c2, c3, c4, c5, c6, c7 = st.columns([0.8, 2, 3, 1.2, 1.2, 1.2, 1.2])
                with c1:
                    checked = st.checkbox("", key=f"prod_sel_{original_idx}")
                    if checked: st.session_state.product_selected.add(original_idx)
                    else:       st.session_state.product_selected.discard(original_idx)
                with c2:
                    st.text_input("코드번호", value=pr["code"], key=f"prod_code_{original_idx}",
                                  disabled=not st.session_state.product_edit_mode, label_visibility="collapsed")
                with c3:
                    st.text_input("품목명", value=pr["name"], key=f"prod_name_{original_idx}",
                                  disabled=not st.session_state.product_edit_mode, label_visibility="collapsed")
                with c4:
                    if st.session_state.product_edit_mode:
                        unit_options = ["병", "박스", "kg", "갯수", "기타"]
                        current_unit_index = unit_options.index(pr["unit"]) if pr["unit"] in unit_options else 0
                        st.selectbox("단위", options=unit_options, index=current_unit_index,
                                     key=f"prod_unit_{original_idx}", label_visibility="collapsed")
                    else:
                        st.text_input("단위", value=pr["unit"], key=f"prod_unit_{original_idx}",
                                      disabled=True, label_visibility="collapsed")
                with c5:
                    if st.session_state.product_edit_mode:
                        st.selectbox("상태", options=["사용", "단종"],
                                     index=(0 if pr["status"] == "사용" else 1),
                                     key=f"prod_status_{original_idx}", label_visibility="collapsed")
                    else:
                        st.text_input("상태", value=pr["status"], key=f"prod_status_{original_idx}",
                                      disabled=True, label_visibility="collapsed")
                with c6:
                    if st.session_state.product_edit_mode:
                        st.number_input("안전재고", min_value=0, step=1, value=int(pr.get("safety", 0)),
                                        key=f"prod_safety_{original_idx}", label_visibility="collapsed")
                    else:
                        st.text_input("안전재고", value=str(pr.get("safety", 0)),
                                      key=f"prod_safety_{original_idx}", disabled=True, label_visibility="collapsed")
                with c7:
                    st.write("")

# ===============================
# 거래처 탭
# ===============================
with partner_tab:
    st.subheader("거래처 등록")

    with st.form("partner_form", clear_on_submit=True):
        form_col1, form_col2, form_col3, form_col4, form_col5, form_col6 = st.columns([1.5, 2, 2, 2, 3, 1])
        with form_col1:
            st.caption("거래처 코드")
            p_code = st.text_input("거래처 코드", key="p_code_input", label_visibility="collapsed", placeholder="P001")
        with form_col2:
            st.caption("거래처명")
            p_name = st.text_input("거래처명", key="p_name_input", label_visibility="collapsed", placeholder="○○커피")
        with form_col3:
            st.caption("사업자번호")
            p_bus = st.text_input("사업자번호", key="p_bus_input", label_visibility="collapsed", placeholder="123-45-67890")
        with form_col4:
            st.caption("대표자 이름")
            p_rep = st.text_input("대표자 이름", key="p_rep_input", label_visibility="collapsed", placeholder="홍길동")
        with form_col5:
            st.caption("주소")
            p_addr = st.text_input("주소", key="p_addr_input", label_visibility="collapsed", placeholder="서울시 강남구...")
        with form_col6:
            st.markdown("<div style='height: 37px'></div>", unsafe_allow_html=True)
            partner_submitted = st.form_submit_button("등록", use_container_width=True)

        if partner_submitted:
            import re
            if not p_code or not p_name:
                st.error("거래처 코드와 거래처명은 필수 입력 항목입니다.")
            elif any(p["code"] == p_code for p in st.session_state.partners):
                st.error("이미 존재하는 거래처 코드입니다.")
            elif p_bus and not re.match(r'^[0-9\-]+$', p_bus):
                st.error("사업자번호는 숫자와 하이픈(-)만 입력 가능합니다.")
            elif p_rep and not re.match(r'^[가-힣a-zA-Z\\s]+$', p_rep):
                st.error("대표자 이름은 한글과 영문만 입력 가능합니다.")
            else:
                # TODO: 서버 저장 전환 → api_post("/partners", {...})
                st.session_state.partners.append({
                    "code": p_code, "name": p_name, "business_number": p_bus,
                    "representative": p_rep, "address": p_addr
                })
                st.success("거래처가 등록되었습니다."); st.rerun()

    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

    with st.form("partner_list_form"):
        if st.session_state.partner_edit_mode:
            title_col, btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([5, 1, 1, 1, 1])
            with title_col: st.subheader("거래처 목록")
            with btn_col1:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("선택 삭제", use_container_width=True):
                    if not st.session_state.partner_selected:
                        st.info("삭제할 항목을 선택하세요.")
                    else:
                        for i in sorted(st.session_state.partner_selected, reverse=True):
                            if 0 <= i < len(st.session_state.partners):
                                st.session_state.partners.pop(i)
                        st.session_state.partner_selected = set()
                        st.success("선택한 항목을 삭제했습니다."); st.rerun()
            with btn_col2:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("전체 삭제", use_container_width=True):
                    st.session_state.partners = []; st.session_state.partner_selected = set()
                    st.success("전체 항목을 삭제했습니다."); st.rerun()
            with btn_col3:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("저장", use_container_width=True):
                    import re
                    for idx, row in enumerate(st.session_state.partners):
                        new_code = st.session_state.get(f"partner_code_{idx}", row["code"]).strip()
                        new_name = st.session_state.get(f"partner_name_{idx}", row["name"]).strip()
                        new_bus = st.session_state.get(f"partner_bus_{idx}", row["business_number"]).strip()
                        new_rep = st.session_state.get(f"partner_rep_{idx}", row["representative"]).strip()
                        new_addr = st.session_state.get(f"partner_addr_{idx}", row["address"]).strip()
                        if any(p["code"] == new_code and i != idx for i, p in enumerate(st.session_state.partners)):
                            st.error(f"'{new_code}'는 이미 존재하는 거래처 코드입니다.")
                        elif new_bus and not re.match(r'^[0-9\\-]+$', new_bus):
                            st.error(f"'{new_bus}'는 올바른 사업자번호 형식이 아닙니다. 숫자와 하이픈(-)만 입력 가능합니다.")
                        elif new_rep and not re.match(r'^[가-힣a-zA-Z\\s]+$', new_rep):
                            st.error(f"'{new_rep}'는 올바른 이름 형식이 아닙니다. 한글과 영문만 입력 가능합니다.")
                        else:
                            st.session_state.partners[idx] = {
                                "code": new_code, "name": new_name, "business_number": new_bus,
                                "representative": new_rep, "address": new_addr
                            }
                    st.session_state.partner_edit_mode = False
                    st.success("저장되었습니다."); st.rerun()
            with btn_col4: st.write("")
        else:
            title_col, btn_col = st.columns([5, 1])
            with title_col: st.subheader("거래처 목록")
            with btn_col:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("수정", use_container_width=True):
                    st.session_state.partner_edit_mode = True; st.rerun()

        if len(st.session_state.partners) == 0:
            st.warning("등록된 거래처가 없습니다"); st.form_submit_button("", use_container_width=True, help="")
        else:
            h1, h2, h3, h4, h5, h6 = st.columns([1.5, 2, 2, 2, 3, 0.5])
            with h1: st.write("**거래처 코드**")
            with h2: st.write("**거래처명**")
            with h3: st.write("**사업자번호**")
            with h4: st.write("**대표자**")
            with h5: st.write("**주소**")
            with h6: st.write("**선택**")

            for idx, partner in enumerate(st.session_state.partners):
                c1, c2, c3, c4, c5, c6 = st.columns([1.5, 2, 2, 2, 3, 0.5])
                with c1:
                    st.text_input("거래처 코드", value=partner["code"], key=f"partner_code_{idx}",
                                  disabled=not st.session_state.partner_edit_mode, label_visibility="collapsed")
                with c2:
                    st.text_input("거래처명", value=partner["name"], key=f"partner_name_{idx}",
                                  disabled=not st.session_state.partner_edit_mode, label_visibility="collapsed")
                with c3:
                    st.text_input("사업자번호", value=partner.get("business_number", ""), key=f"partner_bus_{idx}",
                                  disabled=not st.session_state.partner_edit_mode, label_visibility="collapsed")
                with c4:
                    st.text_input("대표자", value=partner.get("representative", ""), key=f"partner_rep_{idx}",
                                  disabled=not st.session_state.partner_edit_mode, label_visibility="collapsed")
                with c5:
                    st.text_input("주소", value=partner.get("address", ""), key=f"partner_addr_{idx}",
                                  disabled=not st.session_state.partner_edit_mode, label_visibility="collapsed")
                with c6:
                    checked = st.checkbox("", key=f"partner_sel_{idx}")
                    if checked: st.session_state.partner_selected.add(idx)
                    else:       st.session_state.partner_selected.discard(idx)

# ===============================
# 관리자 탭
# ===============================
with admin_tab:
    st.subheader("관리자 등록")

    with st.form("admin_form", clear_on_submit=True):
        form_col1, form_col2, form_col3, form_col4, form_col5, form_col6, form_col7, form_col8 = st.columns([1.2, 1, 1.2, 1.5, 1.5, 1.2, 1.5, 1.2])
        with form_col1:
            st.caption("사번번호")
            emp_no = st.text_input("사번번호", key="admin_emp_no", label_visibility="collapsed", placeholder="EMP001")
        with form_col2:
            st.caption("이름")
            name = st.text_input("이름", key="admin_name", label_visibility="collapsed", placeholder="홍길동")
        with form_col3:
            st.caption("성별")
            gender = st.selectbox("성별", ["남성", "여성"], key="admin_gender", label_visibility="collapsed")
        with form_col4:
            st.caption("이메일")
            email = st.text_input("이메일", key="admin_email", label_visibility="collapsed", placeholder="hong@example.com")
        with form_col5:
            st.caption("전화번호")
            phone = st.text_input("전화번호", key="admin_phone", label_visibility="collapsed", placeholder="010-1234-5678")
        with form_col6:
            st.caption("직급")
            position = st.selectbox("직급", ["직원", "매니저", "파트타이머"], key="admin_position", label_visibility="collapsed")
        with form_col7:
            st.caption("관리 종류")
            management_type = st.selectbox("관리 종류", ["출/입고 관리", "청소", "손님 응대", "음료 제조", "음식 제조", "기타"], key="admin_management", label_visibility="collapsed")
        with form_col8:
            st.caption("재직현황")
            status = st.selectbox("재직현황", ["재직", "퇴사", "휴직"], key="admin_status", label_visibility="collapsed")

        st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
        admin_submitted = st.form_submit_button("등록", use_container_width=True)

        if admin_submitted:
            if not emp_no or not name:
                st.error("사번번호와 이름은 필수 입력 항목입니다.")
            elif any(a["emp_no"] == emp_no for a in st.session_state.admins):
                st.error("이미 존재하는 사번번호입니다.")
            else:
                # TODO: 서버 저장 전환 → api_post("/admins", {...})
                st.session_state.admins.append({
                    "emp_no": emp_no, "name": name, "gender": gender, "email": email, "phone": phone,
                    "position": position, "management_type": management_type, "status": status
                })
                st.success("관리자가 등록되었습니다."); st.rerun()

    with st.form("admin_list_form"):
        if st.session_state.admin_edit_mode:
            title_col, btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([5, 1, 1, 1, 1])
            with title_col: st.subheader("관리자 목록")
            with btn_col1:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("선택 삭제", use_container_width=True):
                    if not st.session_state.admin_selected:
                        st.info("삭제할 항목을 선택하세요.")
                    else:
                        for i in sorted(st.session_state.admin_selected, reverse=True):
                            if 0 <= i < len(st.session_state.admins):
                                st.session_state.admins.pop(i)
                        st.session_state.admin_selected = set()
                        st.success("선택한 항목을 삭제했습니다."); st.rerun()
            with btn_col2:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("전체 삭제", use_container_width=True):
                    st.session_state.admins = []; st.session_state.admin_selected = set()
                    st.success("전체 항목을 삭제했습니다."); st.rerun()
            with btn_col3:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("저장", use_container_width=True):
                    for idx, row in enumerate(st.session_state.admins):
                        new_emp_no = st.session_state.get(f"admin_emp_no_{idx}", row["emp_no"]).strip()
                        new_name   = st.session_state.get(f"admin_name_{idx}", row["name"]).strip()
                        new_gender = st.session_state.get(f"admin_gender_{idx}", row["gender"])
                        new_email  = st.session_state.get(f"admin_email_{idx}", row["email"]).strip()
                        new_phone  = st.session_state.get(f"admin_phone_{idx}", row["phone"]).strip()
                        new_position = st.session_state.get(f"admin_position_{idx}", row["position"])
                        new_mgmt_type = st.session_state.get(f"admin_mgmt_type_{idx}", row["management_type"])
                        new_status = st.session_state.get(f"admin_status_{idx}", row["status"])

                        if any(a["emp_no"] == new_emp_no and i != idx for i, a in enumerate(st.session_state.admins)):
                            st.error(f"'{new_emp_no}'는 이미 존재하는 사번번호입니다.")
                        else:
                            st.session_state.admins[idx] = {
                                "emp_no": new_emp_no, "name": new_name, "gender": new_gender,
                                "email": new_email, "phone": new_phone, "position": new_position,
                                "management_type": new_mgmt_type, "status": new_status
                            }
                    st.session_state.admin_edit_mode = False
                    st.success("저장되었습니다."); st.rerun()
            with btn_col4: st.write("")
        else:
            title_col, btn_col = st.columns([5, 1])
            with title_col: st.subheader("관리자 목록")
            with btn_col:
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("수정", use_container_width=True):
                    st.session_state.admin_edit_mode = True; st.rerun()

        if len(st.session_state.admins) == 0:
            st.warning("등록된 관리자가 없습니다"); st.form_submit_button("", use_container_width=True, help="")
        else:
            h1, h2, h3, h4, h5, h6, h7, h8, h9 = st.columns([1, 1.5, 0.8, 1.5, 1.5, 1.2, 1.5, 1, 0.8])
            with h1: st.write("**선택**")
            with h2: st.write("**사번번호**")
            with h3: st.write("**이름**")
            with h4: st.write("**성별**")
            with h5: st.write("**연락처**")
            with h6: st.write("**직급**")
            with h7: st.write("**관리 종류**")
            with h8: st.write("**재직현황**")
            with h9: st.write("**수정**")

            for idx, admin in enumerate(st.session_state.admins):
                c1, c2, c3, c4, c5, c6, c7, c8, c9 = st.columns([1, 1.5, 0.8, 1.5, 1.5, 1.2, 1.5, 1, 0.8])
                with c1:
                    checked = st.checkbox("", key=f"admin_sel_{idx}")
                    if checked: st.session_state.admin_selected.add(idx)
                    else:       st.session_state.admin_selected.discard(idx)
                with c2:
                    st.text_input("사번번호", value=admin["emp_no"], key=f"admin_emp_no_{idx}",
                                  disabled=not st.session_state.admin_edit_mode, label_visibility="collapsed")
                with c3:
                    st.text_input("이름", value=admin["name"], key=f"admin_name_{idx}",
                                  disabled=not st.session_state.admin_edit_mode, label_visibility="collapsed")
                with c4:
                    if st.session_state.admin_edit_mode:
                        st.selectbox("성별", options=["남", "여"],
                                     index=(0 if admin["gender"] == "남" else 1),
                                     key=f"admin_gender_{idx}", label_visibility="collapsed")
                    else:
                        st.text_input("성별", value=admin["gender"], key=f"admin_gender_{idx}",
                                      disabled=True, label_visibility="collapsed")
                with c5:
                    if st.session_state.admin_edit_mode:
                        col_email, col_phone = st.columns(2)
                        with col_email:
                            st.text_input("이메일", value=admin["email"], key=f"admin_email_{idx}", label_visibility="collapsed")
                        with col_phone:
                            st.text_input("전화번호", value=admin["phone"], key=f"admin_phone_{idx}", label_visibility="collapsed")
                    else:
                        st.text_input("연락처", value=f"{admin['email']} / {admin['phone']}",
                                      key=f"admin_contact_{idx}", disabled=True, label_visibility="collapsed")
                with c6:
                    if st.session_state.admin_edit_mode:
                        position_options = ["직원", "매니저", "파트타이머"]
                        pos_index = position_options.index(admin["position"]) if admin["position"] in position_options else 0
                        st.selectbox("직급", options=position_options, index=pos_index,
                                     key=f"admin_position_{idx}", label_visibility="collapsed")
                    else:
                        st.text_input("직급", value=admin["position"], key=f"admin_position_{idx}",
                                      disabled=True, label_visibility="collapsed")
                with c7:
                    if st.session_state.admin_edit_mode:
                        mgmt_options = ["출/입고 관리", "청소", "손님 응대", "음료 제조", "음식 제조", "기타"]
                        mgmt_index = mgmt_options.index(admin["management_type"]) if admin["management_type"] in mgmt_options else 0
                        st.selectbox("관리 종류", options=mgmt_options, index=mgmt_index,
                                     key=f"admin_mgmt_type_{idx}", label_visibility="collapsed")
                    else:
                        st.text_input("관리 종류", value=admin["management_type"], key=f"admin_mgmt_type_{idx}",
                                      disabled=True, label_visibility="collapsed")
                with c8:
                    if st.session_state.admin_edit_mode:
                        status_options = ["재직", "퇴사", "휴직"]
                        status_index = status_options.index(admin["status"]) if admin["status"] in status_options else 0
                        st.selectbox("재직현황", options=status_options, index=status_index,
                                     key=f"admin_status_{idx}", label_visibility="collapsed")
                    else:
                        st.text_input("재직현황", value=admin["status"], key=f"admin_status_{idx}",
                                      disabled=True, label_visibility="collapsed")
                with c9:
                    st.write("")
