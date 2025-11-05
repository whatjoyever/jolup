from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AlertRow(BaseModel):
    id: int
    alert_type: str
    severity: str
    message: str
    created_at: datetime
    ingredient_id: str
    ingredient_name: str
    location_id: str
    location_name: str
