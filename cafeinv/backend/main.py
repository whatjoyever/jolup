# backend/main.py
import os
import uvicorn
from typing import Optional, List

from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import psycopg2.extras

# --- 로컬 .env 로드 ---
load_dotenv()

# --- 내부 모델/서비스 임포트 ---
from backend.models import (
    # 기본
    SaleCreateIn, SaleCreateOut, InventoryRow, AlertRow,
    # STEP1
    StockChangeIn, StockChangeOut, InventoryTxRow,
    POCreateIn, POCreateOut, POItemAddIn, POReceiveIn, POReceiveOut,
    # STEP2
    CategoryRow, UnitRow, LocationRow, IngredientRow,
    MenuItemCreate, MenuItemUpdate, MenuItemRow,
    RecipeRow, RecipeUpsert,
    SupplierCreate, SupplierUpdate, SupplierRow,
    # STEP3
    TransferCreate, TransferRow, TransferItemAdd, TransferItemRow, TransferAction,
    AuditLogRow,
)

from backend.service import (
    create_sale,
    list_inventory as svc_list_inventory,   # <- 별칭으로 충돌 방지
    list_alerts,
    INSUFFICIENT_ERR,
    # STEP1
    apply_stock_change_service, list_inventory_tx,
    create_purchase_order, add_po_item, receive_purchase_order,
    # STEP2
    list_categories, list_units, list_locations, list_ingredients,
    create_menu_item, update_menu_item, list_menu_items, deactivate_menu_item,
    list_recipes, upsert_recipe, delete_recipe,
    create_supplier, update_supplier, list_suppliers, deactivate_supplier,
    # STEP3
    create_transfer, add_transfer_item, list_transfers, list_transfer_items,
    ship_transfer, receive_transfer, list_audit_logs,
)

# service_items 유틸 (참조용/간편 생성용) — 이름 충돌 방지를 위해 별칭 사용
from backend.service_items import (
    list_units as ref_list_units,
    list_locations as ref_list_locations,
    list_suppliers as ref_list_suppliers,
    list_users_simple,
    list_ingredients_simple,
    create_category as quick_create_category,
    list_categories as quick_list_categories,
    create_ingredient,
    create_receipt_with_items,
)

from backend.db import get_connection  # 리포트용 직접 조회에 사용


# =========================================================
# FastAPI 앱
# =========================================================
app = FastAPI(title="Cafe Inventory API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# ---------------- Health ----------------
@app.get("/health")
def health():
    return {"ok": True}


# =========================================================
# 기본 엔드포인트 (인벤토리/알림/판매)
# =========================================================
@app.get("/inventory", response_model=list[InventoryRow])
def inventory(location_id: Optional[str] = None):
    # 서비스 함수 별칭 사용으로 이름 충돌 제거
    return svc_list_inventory(location_id)

@app.get("/alerts", response_model=list[AlertRow])
def alerts():
    return list_alerts()

@app.post("/sales", response_model=SaleCreateOut)
def sales_create(payload: SaleCreateIn):
    try:
        return create_sale(payload)
    except Exception as e:
        if INSUFFICIENT_ERR in str(e):
            raise HTTPException(status_code=409, detail="INSUFFICIENT_STOCK")
        raise


# =========================================================
# STEP 1: 수동 재고변경 / 발주 수령 / 재고 트랜잭션 조회
# =========================================================
@app.post("/stock_change", response_model=StockChangeOut)
def stock_change(inp: StockChangeIn):
    return apply_stock_change_service(inp)

@app.get("/inventory_tx", response_model=list[InventoryTxRow])
def inventory_tx(
    ingredient_id: Optional[str] = None,
    location_id: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = 50,
):
    return list_inventory_tx(ingredient_id, location_id, since, limit)

@app.post("/purchase_orders", response_model=POCreateOut)
def po_create(inp: POCreateIn):
    return create_purchase_order(inp)

@app.post("/po_items")
def po_add_item(inp: POItemAddIn):
    return add_po_item(inp)

@app.post("/purchase_orders/{po_id}/receive", response_model=POReceiveOut)
def po_receive(po_id: str, body: POReceiveIn):
    body.purchase_order_id = po_id
    return receive_purchase_order(body)


# =========================================================
# STEP 2: 기준정보 (카테고리/단위/위치/원재료/메뉴/레시피/공급사)
# =========================================================
@app.get("/categories", response_model=list[CategoryRow])
def categories(cat_type: Optional[str] = None):
    return list_categories(cat_type)

@app.get("/units", response_model=list[UnitRow])
def units():
    return list_units()

@app.get("/locations", response_model=list[LocationRow])
def locations():
    return list_locations()

@app.get("/ingredients", response_model=list[IngredientRow])
def ingredients(active_only: bool = True):
    return list_ingredients(active_only)

# 메뉴
@app.get("/menu_items", response_model=list[MenuItemRow])
def menu_items(active_only: bool = True):
    return list_menu_items(active_only)

@app.post("/menu_items", response_model=MenuItemRow)
def menu_items_create(body: MenuItemCreate):
    return create_menu_item(body)

@app.put("/menu_items/{menu_id}", response_model=MenuItemRow)
def menu_items_update(menu_id: str, body: MenuItemUpdate):
    return update_menu_item(menu_id, body)

@app.post("/menu_items/{menu_id}/deactivate")
def menu_items_deactivate(menu_id: str):
    return deactivate_menu_item(menu_id)

# 레시피
@app.get("/recipes", response_model=list[RecipeRow])
def recipes(menu_item_id: str):
    return list_recipes(menu_item_id)

@app.post("/recipes", response_model=RecipeRow)
def recipes_upsert(body: RecipeUpsert):
    return upsert_recipe(body)

@app.delete("/recipes/{menu_id}/{ingredient_id}")
def recipes_delete(menu_id: str, ingredient_id: str):
    return delete_recipe(menu_id, ingredient_id)

# 공급사
@app.get("/suppliers", response_model=list[SupplierRow])
def suppliers(active_only: bool = True):
    return list_suppliers(active_only)

@app.post("/suppliers", response_model=SupplierRow)
def suppliers_create(body: SupplierCreate):
    return create_supplier(body)

@app.put("/suppliers/{supplier_id}", response_model=SupplierRow)
def suppliers_update(supplier_id: str, body: SupplierUpdate):
    return update_supplier(supplier_id, body)

@app.post("/suppliers/{supplier_id}/deactivate")
def suppliers_deactivate(supplier_id: str):
    return deactivate_supplier(supplier_id)


# =========================================================
# STEP 3: 로케이션 간 이동/감사로그
# =========================================================
@app.post("/transfers", response_model=TransferRow)
def transfers_create(body: TransferCreate):
    return create_transfer(body)

@app.post("/transfer_items")
def transfers_add_item(body: TransferItemAdd):
    return add_transfer_item(body)

@app.get("/transfers", response_model=list[TransferRow])
def transfers_list(status: Optional[str] = None, limit: int = 100):
    return list_transfers(status, limit)

@app.get("/transfer_items", response_model=list[TransferItemRow])
def transfers_items_list(transfer_id: str):
    return list_transfer_items(transfer_id)

@app.post("/transfers/{transfer_id}/ship")
def transfers_ship(transfer_id: str, body: TransferAction):
    body.transfer_id = transfer_id
    return ship_transfer(body)

@app.post("/transfers/{transfer_id}/receive")
def transfers_receive(transfer_id: str, body: TransferAction):
    body.transfer_id = transfer_id
    return receive_transfer(body)

@app.get("/audit_logs", response_model=list[AuditLogRow])
def audit_logs(table_name: Optional[str] = None, since: Optional[str] = None, limit: int = 100):
    return list_audit_logs(table_name, since, limit)


# =========================================================
# 참조용/간편 등록 API (service_items 기반)
#   - 프론트에서 셀렉트박스 채우기/간단 등록용
# =========================================================
# --- 공통 참조 ---
@app.get("/ref/units")
def ref_units():
    return ref_list_units()

@app.get("/ref/locations")
def ref_locations():
    return ref_list_locations()

@app.get("/ref/suppliers")
def ref_suppliers():
    return ref_list_suppliers()

@app.get("/ref/users")
def ref_users():
    return list_users_simple()

@app.get("/ref/ingredients")
def ref_ingredients():
    return list_ingredients_simple()

# --- 원재료 생성(간편) ---
from pydantic import BaseModel, Field

class IngredientIn(BaseModel):
    name: str
    category_id: Optional[str] = None
    unit_id: str
    description: Optional[str] = None
    safety_stock_default: Optional[float] = 0
    reorder_point_default: Optional[float] = 0
    responsible_user_id: Optional[str] = None
    cost_per_unit: Optional[float] = 0

@app.post("/ingredients")
def ingredients_create(body: IngredientIn):
    return create_ingredient(body.model_dump())

# --- 카테고리 간편 생성 ---
class CategoryIn(BaseModel):
    name: str
    type: str = Field(pattern="^(ingredient|menu)$")

@app.post("/categories/quick")
def categories_quick_create(body: CategoryIn):
    # 정식 /categories는 GET만 노출. 빠른 생성은 /categories/quick 로 구분
    return quick_create_category(body.name.strip(), body.type)


# =========================================================
# 리포트/스냅샷 전용 라우터 (경로 충돌 방지 위해 prefix 사용)
# =========================================================
report_router = APIRouter(prefix="/report", tags=["report"])

@report_router.get("/items")
def report_items():
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT i.id::text, i.name,
                       c.name AS category,
                       u.name AS unit,
                       i.description,
                       i.safety_stock AS safe_stock
                FROM ingredients i
                LEFT JOIN categories c ON i.category_id = c.id
                LEFT JOIN units u ON u.id = i.unit_id
                ORDER BY i.name;
            """)
            return cur.fetchall()

@report_router.get("/inventory")
def report_inventory_snapshot():
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    inv.ingredient_id::text,
                    inv.location_id::text,
                    ing.name   AS ingredient,
                    loc.name   AS location,
                    COALESCE(inv.qty_on_hand,0) AS qty,
                    inv.reorder_point,
                    inv.safety_stock
                FROM inventory inv
                JOIN ingredients ing ON ing.id = inv.ingredient_id
                JOIN locations   loc ON loc.id = inv.location_id
                ORDER BY loc.name, ing.name;
            """)
            return cur.fetchall()

@report_router.get("/purchase_orders")
def report_purchase_orders():
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT po.id::text, po.created_at, u.full_name AS staff,
                       pi.qty_ordered AS qty, pi.unit_cost,
                       ing.name AS item_name
                FROM purchase_orders po
                JOIN po_items pi     ON po.id = pi.purchase_order_id
                JOIN ingredients ing ON pi.ingredient_id = ing.id
                LEFT JOIN users u    ON po.created_by = u.id
                ORDER BY po.created_at DESC;
            """)
            return cur.fetchall()

app.include_router(report_router)


# =========================================================
# 앱 실행 (uvicorn main:app 대신 안전하게 app 객체 직접 전달)
# =========================================================
if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", "8000")),
        reload=True,
    )
