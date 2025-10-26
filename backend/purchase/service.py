# backend/purchase/service.py
from uuid import uuid4, UUID
from typing import Optional, Dict, Any, List
from datetime import date

from backend.core.db import get_conn  # ★ 너네 DB 헬퍼에 맞춰 import
from backend.catalog.schema import PurchaseOrderCreateIn

# 유틸: 미입고 잔량 계산은 receipt_items 합계를 뺀 값으로 계산한다.
# receipt_items 테이블에 po_item_id(=purchase_order_items.id) FK가 있다고 가정.
# 만약 없다면 receipts 테이블에 purchase_order_id FK가 있는지 확인해서 join 경로만 바꿔.

def create_purchase_order(payload: PurchaseOrderCreateIn) -> UUID:
    po_id = uuid4()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO purchase_orders (id, supplier_id, status, note)
            VALUES (%s, %s, 'open', %s)
        """, (str(po_id), str(payload.supplier_id), payload.note))
        # 라인
        for it in payload.items:
            cur.execute("""
                INSERT INTO purchase_order_items (id, purchase_order_id, ingredient_id, qty, unit_price)
                VALUES (gen_random_uuid(), %s, %s, %s, %s)
            """, (str(po_id), str(it.ingredient_id), it.qty, it.unit_price))
    return po_id

def list_purchase_orders(status: Optional[str] = None) -> List[Dict[str, Any]]:
    q = """
      SELECT po.id, po.supplier_id, po.status, po.created_at,
             COALESCE(SUM(poi.qty),0) AS ordered_qty,
             COALESCE(SUM(ri_sum.received_qty),0) AS received_qty
      FROM purchase_orders po
      LEFT JOIN purchase_order_items poi ON poi.purchase_order_id = po.id
      LEFT JOIN (
         SELECT po_item_id, SUM(qty) AS received_qty
         FROM receipt_items
         GROUP BY po_item_id
      ) ri_sum ON ri_sum.po_item_id = poi.id
    """
    params = []
    if status and status != "all":
        q += " WHERE po.status = %s"
        params.append(status)
    q += " GROUP BY po.id"
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(q, params)
        rows = cur.fetchall()
    # 필요한 형태로 직렬화
    res = []
    for r in rows:
        res.append({
            "id": str(r[0]),
            "supplier_id": str(r[1]),
            "status": r[2],
            "created_at": r[3].isoformat() if r[3] else None,
            "ordered_qty": float(r[4] or 0),
            "received_qty": float(r[5] or 0),
        })
    return res

def get_purchase_order_detail(po_id: UUID) -> Dict[str, Any]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, supplier_id, status, note, created_at FROM purchase_orders WHERE id=%s", (str(po_id),))
        head = cur.fetchone()
        if not head:
            raise ValueError("PO not found")

        cur.execute("""
          SELECT poi.id,
                 poi.ingredient_id,
                 poi.qty,
                 poi.unit_price,
                 COALESCE(ri_sum.received_qty,0) AS received_qty
          FROM purchase_order_items poi
          LEFT JOIN (
             SELECT po_item_id, SUM(qty) AS received_qty
             FROM receipt_items
             GROUP BY po_item_id
          ) ri_sum ON ri_sum.po_item_id = poi.id
          WHERE poi.purchase_order_id = %s
        """, (str(po_id),))
        items = cur.fetchall()

    return {
        "id": str(head[0]),
        "supplier_id": str(head[1]),
        "status": head[2],
        "note": head[3],
        "created_at": head[4].isoformat() if head[4] else None,
        "items": [
            {
                "po_item_id": str(i[0]),
                "ingredient_id": str(i[1]),
                "ordered_qty": float(i[2]),
                "unit_price": float(i[3]),
                "received_qty": float(i[4]),
                "remaining_qty": float(i[2]) - float(i[4]),
            } for i in items
        ]
    }

def create_receipt_from_po(po_id: UUID, body: Dict[str, Any]) -> UUID:
    """
    body = {
      "location_id": "...",
      "note": "...",
      "items": [
        {"po_item_id": "...", "qty": 50, "unit_price": 1200, "expiry_date": "2025-12-31"}
      ]
    }
    """
    location_id = body.get("location_id")
    items = body.get("items", [])
    note = body.get("note")

    if not items:
        raise ValueError("items required")

    receipt_id = uuid4()

    with get_conn() as conn, conn.cursor() as cur:
        # 헤더(공급사 FK는 원발주에서 따옴)
        cur.execute("SELECT supplier_id FROM purchase_orders WHERE id=%s", (str(po_id),))
        row = cur.fetchone()
        if not row:
            raise ValueError("PO not found")
        supplier_id = row[0]

        cur.execute("""
            INSERT INTO receipts (id, supplier_id, purchase_order_id, note)
            VALUES (%s, %s, %s, %s)
        """, (str(receipt_id), str(supplier_id), str(po_id), note))

        # 각 아이템 검증 + 삽입 (부분입고/중복 방지 체크)
        for it in items:
            po_item_id = it["po_item_id"]
            qty = float(it["qty"])
            price = float(it.get("unit_price", 0))
            expiry_date: Optional[str] = it.get("expiry_date")

            # 1) 주문 수량 / 기수령 확인
            cur.execute("SELECT ingredient_id, qty FROM purchase_order_items WHERE id=%s", (str(po_item_id),))
            r = cur.fetchone()
            if not r:
                raise ValueError("po_item not found")
            ing_id, ordered_qty = r[0], float(r[1])

            cur.execute("SELECT COALESCE(SUM(qty),0) FROM receipt_items WHERE po_item_id=%s", (str(po_item_id),))
            current_received = float(cur.fetchone()[0] or 0)

            remaining = ordered_qty - current_received
            if qty <= 0:
                raise ValueError("qty must be > 0")
            if qty > remaining + 1e-9:
                raise ValueError(f"qty({qty}) > remaining({remaining})")

            # 2) receipt_items 삽입
            cur.execute("""
              INSERT INTO receipt_items
                (id, receipt_id, po_item_id, ingredient_id, qty, unit_price, location_id, expiry_date, note)
              VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                str(receipt_id), str(po_item_id), str(ing_id), qty, price,
                str(location_id), expiry_date, it.get("note"),
            ))

        # 3) 전체 수령 완료 여부에 따라 발주 상태 업데이트 (open→closed)
        cur.execute("""
          SELECT SUM(poi.qty) AS ordered, COALESCE(SUM(ri.qty),0) AS received
          FROM purchase_order_items poi
          LEFT JOIN receipt_items ri ON ri.po_item_id = poi.id
          WHERE poi.purchase_order_id = %s
        """, (str(po_id),))
        ordered, received = cur.fetchone()
        if float(received or 0) + 1e-9 >= float(ordered or 0):
            cur.execute("UPDATE purchase_orders SET status='closed' WHERE id=%s", (str(po_id),))

    # ★ receipt_items → inventory_tx 는 DB 트리거가 이미 처리 (네가 보여준 receipt_items_to_tx)
    return receipt_id
