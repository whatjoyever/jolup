from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class InventoryTxRow(BaseModel):
    id: str
    ingredient_id: str
    location_id: str
    tx_type: str
    qty_delta: float
    ref_table: Optional[str] = None
    ref_id: Optional[str] = None
    expiry_date: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime

class StockChangeIn(BaseModel):
    ingredient_id: str
    location_id: str
    qty_delta: float
    tx_type: str  # adjustment/purchase/waste/transfer_in/transfer_out/return/consume/sale
    note: Optional[str] = None
