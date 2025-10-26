from fastapi import APIRouter, HTTPException, Query
from uuid import UUID
from typing import Optional

from backend.purchase.service import (
    create_purchase_order,
    list_purchase_orders,
    get_purchase_order_detail,
    create_receipt_from_po,
)

router = APIRouter()

@router.post("/orders")
def create_po(payload: dict):
    """
    body:
    {
      "supplier_id": "uuid",
      "note": "string|null",
      "items": [
        {"ingredient_id": "uuid", "qty": 10, "unit_price": 1200.0},
        ...
      ]
    }
    """
    try:
        po_id = create_purchase_order(payload)
        return {"ok": True, "id": str(po_id)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"create_po failed: {e}")

@router.get("/orders")
def get_pos(status: Optional[str] = Query("open", description="open|closed|all")):
    try:
        return list_purchase_orders(status=status)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"list_po failed: {e}")

@router.get("/orders/{po_id}")
def get_po_detail(po_id: UUID):
    try:
        return get_purchase_order_detail(po_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"get_po failed: {e}")

@router.post("/receipts/from-po/{po_id}")
def receive_from_po(po_id: UUID, body: dict):
    """
    body:
    {
      "location_id": "uuid|null",
      "note": "부분 입고",
      "items": [
        {"po_item_id": "uuid", "qty": 50, "unit_price": 1200.0, "expiry_date": "2025-12-31", "note": null}
      ]
    }
    """
    try:
        rid = create_receipt_from_po(po_id, body)
        return {"ok": True, "receipt_id": str(rid)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"receive failed: {e}")
