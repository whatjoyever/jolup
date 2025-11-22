# backend/schema.py
from typing import List, Optional
from pydantic import BaseModel


# =======================
# 재고 (Inventory)
# =======================
class InventoryItem(BaseModel):
    ingredient_id: str
    location_id: str
    qty_on_hand: float


class InventoryTx(BaseModel):
    id: str
    ingredient_id: str
    location_id: str
    tx_type: Optional[str]
    qty_delta: float
    ref_table: Optional[str]
    ref_id: Optional[str]
    note: Optional[str]
    created_at: str


class StockChangeRequest(BaseModel):
    ingredient_id: str
    location_id: str
    qty_delta: float
    tx_type: Optional[str] = "adjustment"
    note: Optional[str] = None


class StockChangeResponse(BaseModel):
    ingredient_id: str
    location_id: str
    balance: float


# =======================
# 레시피 (Recipes)
# =======================
class RecipeIngredient(BaseModel):
    ingredient_id: str
    qty_required: float


class RecipeUpsertRequest(BaseModel):
    menu_item_id: str
    ingredients: List[RecipeIngredient]


class RecipeRow(BaseModel):
    menu_item_id: str
    ingredient_id: str
    qty_required: float


# =======================
# 판매 (Sales)
# =======================
class SaleItemRequest(BaseModel):
    menu_item_id: str
    qty: float
    unit_price: float


class CreateSaleRequest(BaseModel):
    location_id: str
    items: List[SaleItemRequest]


class CreateSaleResponse(BaseModel):
    ok: bool
    sale_id: str
    total_amount: float
