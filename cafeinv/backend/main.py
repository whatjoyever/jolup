import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from psycopg2 import errors
from dotenv import load_dotenv

# 로컬 환경 변수 로드
load_dotenv()

# 내부 모듈 import (패키지 문제 방지 위해 절대경로 스타일로 수정)
from models import SaleCreateIn, SaleCreateOut, InventoryRow, AlertRow
from service import create_sale, list_inventory, list_alerts, INSUFFICIENT_ERR

# ✅ FastAPI 앱 객체 생성 (이게 uvicorn이 찾는 app)
app = FastAPI(title="Cafe Inventory API", version="0.1.0")

# ✅ CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Health check
@app.get("/health")
def health():
    return {"ok": True}

# ✅ 재고 조회
@app.get("/inventory", response_model=list[InventoryRow])
def inventory(location_id: str | None = None):
    return list_inventory(location_id)

# ✅ 알림 조회
@app.get("/alerts", response_model=list[AlertRow])
def alerts():
    return list_alerts()

# ✅ 판매 생성
@app.post("/sales", response_model=SaleCreateOut)
def sales_create(payload: SaleCreateIn):
    try:
        return create_sale(payload)
    except Exception as e:
        if INSUFFICIENT_ERR in str(e):
            raise HTTPException(status_code=409, detail="INSUFFICIENT_STOCK")
        raise


# ✅ 여기서 경로를 문자열로 쓰지 말고, 직접 app 객체를 전달 (가장 안전함)
if __name__ == "__main__":
    uvicorn.run(
        app,  # <- 이렇게 수정
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", "8000")),
        reload=True
    )

# ====== STEP1 routes ======
from backend.models import (
    StockChangeIn, StockChangeOut, InventoryTxRow,
    POCreateIn, POCreateOut, POItemAddIn, POReceiveIn, POReceiveOut
)
from backend.service import (
    apply_stock_change_service, list_inventory_tx,
    create_purchase_order, add_po_item, receive_purchase_order
)

@app.post("/stock_change", response_model=StockChangeOut)
def stock_change(inp: StockChangeIn):
    return apply_stock_change_service(inp)

@app.get("/inventory_tx", response_model=list[InventoryTxRow])
def inventory_tx(ingredient_id: str | None = None,
                 location_id: str | None = None,
                 since: str | None = None,
                 limit: int = 50):
    return list_inventory_tx(ingredient_id, location_id, since, limit)

@app.post("/purchase_orders", response_model=POCreateOut)
def po_create(inp: POCreateIn):
    return create_purchase_order(inp)

@app.post("/po_items")
def po_add_item(inp: POItemAddIn):
    return add_po_item(inp)

@app.post("/purchase_orders/{po_id}/receive", response_model=POReceiveOut)
def po_receive(po_id: str, body: POReceiveIn):
    # path의 po_id를 보디와 일치시켜 안전성 확보
    body.purchase_order_id = po_id
    return receive_purchase_order(body)

# ====== STEP2 routes ======
from backend.service import (
    list_categories, list_units, list_locations, list_ingredients,
    create_menu_item, update_menu_item, list_menu_items, deactivate_menu_item,
    list_recipes, upsert_recipe, delete_recipe,
    create_supplier, update_supplier, list_suppliers, deactivate_supplier
)
from backend.models import (
    CategoryRow, UnitRow, LocationRow, IngredientRow,
    MenuItemCreate, MenuItemUpdate, MenuItemRow,
    RecipeRow, RecipeUpsert,
    SupplierCreate, SupplierUpdate, SupplierRow
)

@app.get("/categories", response_model=list[CategoryRow])
def categories(cat_type: str | None = None):
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

@app.get("/recipes", response_model=list[RecipeRow])
def recipes(menu_item_id: str):
    return list_recipes(menu_item_id)

@app.post("/recipes", response_model=RecipeRow)
def recipes_upsert(body: RecipeUpsert):
    return upsert_recipe(body)

@app.delete("/recipes/{menu_id}/{ingredient_id}")
def recipes_delete(menu_id: str, ingredient_id: str):
    return delete_recipe(menu_id, ingredient_id)

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

# ====== STEP3 routes ======
from backend.models import (
    TransferCreate, TransferRow, TransferItemAdd, TransferItemRow, TransferAction,
    AuditLogRow
)
from backend.service import (
    create_transfer, add_transfer_item, list_transfers, list_transfer_items,
    ship_transfer, receive_transfer, list_audit_logs
)

@app.post("/transfers", response_model=TransferRow)
def transfers_create(body: TransferCreate):
    return create_transfer(body)

@app.post("/transfer_items")
def transfers_add_item(body: TransferItemAdd):
    return add_transfer_item(body)

@app.get("/transfers", response_model=list[TransferRow])
def transfers_list(status: str | None = None, limit: int = 100):
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
def audit_logs(table_name: str | None = None, since: str | None = None, limit: int = 100):
    return list_audit_logs(table_name, since, limit)
