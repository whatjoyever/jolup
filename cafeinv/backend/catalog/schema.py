from pydantic import BaseModel
from typing import Optional

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
