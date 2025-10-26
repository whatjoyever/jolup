from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID

# =========================
# 기존 모델 (그대로 유지)
# =========================

# Categories
class CategoryIn(BaseModel):
    name: str
    type: str  # 'ingredient' | 'menu'

class CategoryOut(BaseModel):
    id: str
    name: str
    type: str
    is_active: bool

# Suppliers
class SupplierIn(BaseModel):
    name: str
    contact: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = True

# Ingredients
class IngredientIn(BaseModel):
    name: str
    unit_id: str
    category_id: Optional[str] = None
    description: Optional[str] = None
    safety_stock_default: float = 0
    reorder_point_default: float = 0
    responsible_user_id: Optional[str] = None
    cost_per_unit: float = 0

# Menu
class MenuItemIn(BaseModel):
    name: str
    price: float
    category_id: Optional[str] = None
    default_location_id: Optional[str] = None
    is_active: bool = True

# Recipes
class RecipeUpsert(BaseModel):
    menu_item_id: str
    ingredient_id: str
    qty_required: float

# =========================
# 여기부터 “추가” (발주용)
# =========================

class PurchaseOrderItemIn(BaseModel):
    ingredient_id: UUID
    qty: float
    unit_price: float

class PurchaseOrderCreateIn(BaseModel):
    supplier_id: UUID
    items: List[PurchaseOrderItemIn]
    note: Optional[str] = None

class PurchaseOrderOut(BaseModel):
    id: UUID
    supplier_id: UUID
    created_at: str
    status: str
