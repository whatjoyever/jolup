from typing import Optional
from backend.core.db import get_cursor

def list_inventory(location_id: Optional[str] = None):
    with get_cursor() as cur:
        if location_id:
            cur.execute(
                "SELECT * FROM inventory WHERE location_id=%s ORDER BY ingredient_id;",
                (location_id,)
            )
        else:
            cur.execute("SELECT * FROM inventory ORDER BY ingredient_id, location_id;")
        return cur.fetchall()

def list_tx(ingredient_id: Optional[str], location_id: Optional[str], since: Optional[str], limit: int = 50):
    q = "SELECT * FROM inventory_tx WHERE 1=1"
    args = []
    if ingredient_id:
        q += " AND ingredient_id=%s"; args.append(ingredient_id)
    if location_id:
        q += " AND location_id=%s"; args.append(location_id)
    if since:
        q += " AND created_at >= %s"; args.append(since)
    q += " ORDER BY created_at DESC LIMIT %s"; args.append(limit)
    with get_cursor() as cur:
        cur.execute(q, tuple(args))
        return cur.fetchall()

def apply_stock_change(data: dict):
    # inventory_tx에 INSERT → 트리거가 inv_stock 갱신
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO inventory_tx(ingredient_id, location_id, tx_type, qty_delta, note)
            VALUES (%s,%s,%s,%s,%s)
            RETURNING *;
            """,
            (data["ingredient_id"], data["location_id"], data["tx_type"], data["qty_delta"], data.get("note"))
        )
        return cur.fetchone()

# ---- Purchase Orders / Receipts ----
def create_po(data: dict):
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO purchase_orders(supplier_id, status, order_date, expected_date, note)
            VALUES (%s,'draft',%s,%s,%s) RETURNING *;
            """,
            (data.get("supplier_id"), data.get("order_date"),
             data.get("expected_date"), data.get("note"))
        )
        return cur.fetchone()

def add_po_item(purchase_order_id: str, ingredient_id: str, qty_ordered: float, unit_cost: float):
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO purchase_order_items(purchase_order_id, ingredient_id, qty_ordered, unit_cost)
            VALUES (%s,%s,%s,%s) RETURNING *;
            """,
            (purchase_order_id, ingredient_id, qty_ordered, unit_cost)
        )
        return cur.fetchone()

def receive_po(po_id: str, location_id: str, items: list[dict]):
    # receipts + receipt_items 생성 → 트리거가 inventory_tx('purchase') 생성
    with get_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO receipts(purchase_order_id, location_id) VALUES (%s,%s) RETURNING id;",
            (po_id, location_id)
        )
        receipt_id = cur.fetchone()["id"]
        for it in items:
            cur.execute(
                """
                INSERT INTO receipt_items(receipt_id, ingredient_id, qty, unit_cost, expiry_date, lot_code)
                VALUES (%s,%s,%s,%s,%s,%s)
                RETURNING id;
                """,
                (receipt_id, it["ingredient_id"], it.get("qty_received") or it.get("qty") or 0,
                 it.get("unit_cost"), it.get("expiry_date"), it.get("lot_code"))
            )
        # 상태 변경(선택): 수령 완료
        cur.execute("UPDATE purchase_orders SET status='received' WHERE id=%s;", (po_id,))
        return {"receipt_id": receipt_id, "received_count": len(items), "status": "received"}
