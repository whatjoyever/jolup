from pydantic import BaseModel
from typing import Optional

# 판매 요청
class SaleCreateIn(BaseModel):
    menu_item_id: str
    qty: int
    unit_price: float

# 판매 응답
class SaleCreateOut(BaseModel):
    sale_id: str
    total_amount: float

# 재고 조회 응답
class InventoryRow(BaseModel):
    ingredient_id: str
    ingredient_name: str
    location_name: str
    qty_on_hand: float
    reorder_point: float
    safety_stock: float

# 알림 조회 응답
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AlertRow(BaseModel):
    id: str
    alert_type: str
    message: str
    severity: str
    created_at: datetime
    ingredient_id: Optional[str] = None
    ingredient_name: Optional[str] = None
    location_id: Optional[str] = None
    location_name: Optional[str] = None


    # ====== STEP1: stock change / tx history / purchase order ======
from typing import Optional, Literal
from datetime import date, datetime

TxType = Literal['purchase','recipe_consume','waste','adjustment','transfer_in','transfer_out','return']

class StockChangeIn(BaseModel):
    ingredient_id: str
    location_id: str
    qty_delta: float
    tx_type: TxType = 'adjustment'
    note: Optional[str] = None
    ref_table: Optional[str] = "manual"
    created_by: Optional[str] = None  # users.id (없으면 None)

class StockChangeOut(BaseModel):
    ok: bool
    balance: Optional[float] = None

class InventoryTxRow(BaseModel):
    created_at: datetime
    tx_type: TxType
    ingredient_name: str
    location_name: str
    qty_delta: float
    note: Optional[str] = None
    ref_table: Optional[str] = None

class POCreateIn(BaseModel):
    supplier_id: Optional[str] = None
    order_date: Optional[date] = None
    expected_date: Optional[date] = None
    note: Optional[str] = None
    created_by: Optional[str] = None

class POCreateOut(BaseModel):
    id: str
    status: str

class POItemAddIn(BaseModel):
    purchase_order_id: str
    ingredient_id: str
    qty_ordered: float
    unit_cost: float

class POReceiveItem(BaseModel):
    ingredient_id: str
    qty_received: float

class POReceiveIn(BaseModel):
    purchase_order_id: str
    location_id: str
    items: list[POReceiveItem]
    received_by: Optional[str] = None

class POReceiveOut(BaseModel):
    purchase_order_id: str
    received_count: int
    status: str

# ====== STEP2: menu/recipe & suppliers ======
from typing import Optional
from datetime import datetime

class CategoryRow(BaseModel):
    id: str
    name: str
    type: Optional[str] = None
    parent_id: Optional[str] = None

class UnitRow(BaseModel):
    id: str
    name: str
    base: str
    to_base: float

class LocationRow(BaseModel):
    id: str
    name: str

class IngredientRow(BaseModel):
    id: str
    name: str
    unit_id: str
    is_active: bool

class MenuItemCreate(BaseModel):
    name: str
    price: float
    category_id: Optional[str] = None
    default_location_id: Optional[str] = None
    is_active: Optional[bool] = True

class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    category_id: Optional[str] = None
    default_location_id: Optional[str] = None
    is_active: Optional[bool] = None

class MenuItemRow(BaseModel):
    id: str
    name: str
    price: float
    category_id: Optional[str] = None
    default_location_id: Optional[str] = None
    is_active: bool

class RecipeRow(BaseModel):
    menu_item_id: str
    ingredient_id: str
    ingredient_name: str
    qty_required: float

class RecipeUpsert(BaseModel):
    menu_item_id: str
    ingredient_id: str
    qty_required: float

class SupplierCreate(BaseModel):
    name: str
    contact: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = True

class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None

class SupplierRow(BaseModel):
    id: str
    name: str
    contact: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    is_active: bool

# ====== STEP3: transfers & audit logs ======
from typing import Optional
from datetime import datetime

class TransferCreate(BaseModel):
    from_location_id: Optional[str] = None
    to_location_id: Optional[str] = None
    created_by: Optional[str] = None
    status: Optional[str] = "draft"   # draft | shipped | received | canceled

class TransferRow(BaseModel):
    id: str
    from_location_id: Optional[str] = None
    to_location_id: Optional[str] = None
    status: Optional[str] = None
    created_at: datetime

class TransferItemAdd(BaseModel):
    transfer_id: str
    ingredient_id: str
    qty: float

class TransferItemRow(BaseModel):
    id: str
    transfer_id: str
    ingredient_id: str
    ingredient_name: str
    qty: float

class TransferAction(BaseModel):
    transfer_id: str
    acted_by: Optional[str] = None

class AuditLogRow(BaseModel):
    created_at: datetime
    table_name: Optional[str] = None
    record_id: Optional[str] = None
    action: Optional[str] = None
    user_id: Optional[str] = None
    before: Optional[dict] = None
    after: Optional[dict] = None
