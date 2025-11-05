
# schemas.py
from pydantic import BaseModel, UUID4, conint, confloat
from typing import List, Optional

class RecipeItemIn(BaseModel):
    ingredient_id: UUID4
    qty_required: confloat(ge=0)

class RecipeUpsertIn(BaseModel):
    menu_item_id: UUID4
    ingredients: List[RecipeItemIn]

class SaleLineIn(BaseModel):
    menu_item_id: UUID4
    qty: conint(ge=1)
    unit_price: conint(ge=0) = 0
    discount: conint(ge=0) = 0

class SaleCreateIn(BaseModel):
    items: List[SaleLineIn]
    channel: str = "POS"
    location_id: Optional[UUID4] = None
