from fastapi import APIRouter, Query
from backend.core.exceptions import db_error
from .schema import StockChangeIn
from .service import (
    list_inventory, list_tx, apply_stock_change,
    create_po, add_po_item, receive_po
)

router = APIRouter()

# ----- inventory -----
@router.get("")
def get_inventory(location_id: str | None = Query(default=None)):
    try:
        return list_inventory(location_id)
    except Exception as e:
        raise db_error(e)

# ----- tx history -----
@router.get("/inventory_tx")
def get_inventory_tx(
    ingredient_id: str | None = None,
    location_id: str | None = None,
    since: str | None = None,
    limit: int = 50
):
    try:
        return list_tx(ingredient_id, location_id, since, limit)
    except Exception as e:
        raise db_error(e)

# ----- stock change (manual) -----
@router.post("/stock_change")
def post_stock_change(body: StockChangeIn):
    try:
        return apply_stock_change(body.model_dump())
    except Exception as e:
        raise db_error(e)

# ----- purchase orders / receipts -----
@router.post("/purchase_orders")
def post_purchase_order(body: dict):
    try:
        return create_po(body)
    except Exception as e:
        raise db_error(e)

@router.post("/po_items")
def post_po_item(body: dict):
    try:
        return add_po_item(
            purchase_order_id=body["purchase_order_id"],
            ingredient_id=body["ingredient_id"],
            qty_ordered=body["qty_ordered"],
            unit_cost=body.get("unit_cost", 0)
        )
    except Exception as e:
        raise db_error(e)

@router.post("/purchase_orders/{po_id}/receive")
def post_po_receive(po_id: str, body: dict):
    try:
        return receive_po(po_id, body["location_id"], body["items"])
    except Exception as e:
        raise db_error(e)
