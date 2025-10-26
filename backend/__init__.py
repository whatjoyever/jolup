from uuid import uuid4, UUID
from typing import Dict, Any, List, Optional
from backend.core.db import get_conn

# -------------------------------------------------------
#  Helper: dict row fetcher (psycopg2 → dict로 직렬화할 때 사용)
# -------------------------------------------------------
def rows_to_dicts(cur):
    cols = [desc[0] for desc in cur.description]
    for r in cur.fetchall():
        yield {c: v for c, v in zip(cols, r)}

# -------------------------------------------------------
# 1) 발주 생성
# -------------------------------------------------------
def create_purchase_order(payload: Dict[str, Any]) -> UUID:
    """
    payload = {
      "supplier_id": "uuid",
      "note": "str|null",
      "items": [{"ingredient_id":"uuid","qty":10,"unit_price":1200.0}, ...]
    }
    """
    supplier_id = payload.get("supplier_id")
    items = payload.get("items") or []
    note = payload.get("note")

    if not supplier_id:
        raise ValueError("supplier_id is required")
    if not items:
        raise ValueError("items is required")

    po_id = uuid4()

    with get_conn() as conn:
        with conn.cursor() as cur:
            # 발주 헤더
            cur.execute("""
                INSERT INTO purchase_orders (id, supplier_id, status, note)
                VALUES (%s, %s, 'open', %s)
            """, (str(po_id), str(supplier_id), note))

            # 발주 라인
            for it in items:
                ing_id = it["ingredient_id"]
                qty = float(it.get("qty") or 0)
                price = float(it.get("unit_price") or 0)
                if qty <= 0:
                    raise ValueError("qty must be > 0")
                cur.execute("""
                    INSERT INTO purchase_order_items
                      (id, purchase_order_id, ingredient_id, qty, unit_price)
                    VALUES (gen_random_uuid(), %s, %s, %s, %s)
                """, (str(po_id), str(ing_id), qty, price))
    return po_id

# -------------------------------------------------------
# 2) 발주 목록 (open/closed/all)
# -------------------------------------------------------
def list_purchase_orders(status: Optional[str] = "open") -> List[Dict[str, Any]]:
    params = []
    wh = ""
    if status and status != "all":
        wh = "WHERE po.status = %s"
        params.append(status)

    sql = f"""
      SELECT
        po.id,
        po.supplier_id,
        po.status,
        po.created_at,
        COALESCE(SUM(poi.qty),0) AS ordered_qty,
        COALESCE(SUM(ri_sum.received_qty),0) AS received_qty
      FROM purchase_orders po
      LEFT JOIN purchase_order_items poi ON poi.purchase_order_id = po.id
      LEFT JOIN (
        SELECT po_item_id, SUM(qty) AS received_qty
        FROM receipt_items
        GROUP BY po_item_id
      ) ri_sum ON ri_sum.po_item_id = poi.id
      {wh}
      GROUP BY po.id
      ORDER BY po.created_at DESC
      LIMIT 500
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            res = []
            for r in cur.fetchall():
                # r = (id, supplier_id, status, created_at, ordered, received)
                res.append({
                    "id": str(r[0]),
                    "supplier_id": str(r[1]) if r[1] else None,
                    "status": r[2],
                    "created_at": r[3].isoformat() if r[3] else None,
                    "ordered_qty": float(r[4] or 0),
                    "received_qty": float(r[5] or 0),
                })
            return res

# -------------------------------------------------------
# 3) 발주 상세 (잔량 포함)
# -------------------------------------------------------
def get_purchase_order_detail(po_id: UUID) -> Dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
              SELECT id, supplier_id, status, note, created_at
              FROM purchase_orders
              WHERE id = %s
            """, (str(po_id),))
            head = cur.fetchone()
            if not head:
                raise ValueError("PO not found")

            cur.execute("""
              SELECT
                poi.id AS po_item_id,
                poi.ingredient_id,
                poi.qty AS ordered_qty,
                poi.unit_price,
                COALESCE(ri_sum.received_qty,0) AS received_qty
              FROM purchase_order_items poi
              LEFT JOIN (
                 SELECT po_item_id, SUM(qty) AS received_qty
                 FROM receipt_items
                 GROUP BY po_item_id
              ) ri_sum ON ri_sum.po_item_id = poi.id
              WHERE poi.purchase_order_id = %s
              ORDER BY poi.created_at
            """, (str(po_id),))
            items = cur.fetchall()

    return {
        "id": str(head[0]),
        "supplier_id": str(head[1]) if head[1] else None,
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

# -------------------------------------------------------
# 4) (부분)입고 등록: receipts/receipt_items + 상태 업데이트
#    inventory_tx 반영은 receipt_items→inventory_tx 트리거가 처리
# -------------------------------------------------------
def create_receipt_from_po(po_id: UUID, body: Dict[str, Any]) -> UUID:
    loc_id = body.get("location_id")
    items = body.get("items") or []
    note = body.get("note")

    if not items:
        raise ValueError("items required")

    rid = uuid4()

    with get_conn() as conn:
        with conn.cursor() as cur:
            # 0) 발주/공급사 확인
            cur.execute("SELECT supplier_id FROM purchase_orders WHERE id=%s", (str(po_id),))
            row = cur.fetchone()
            if not row:
                raise ValueError("PO not found")
            supplier_id = row[0]

            # 1) receipts 헤더
            cur.execute("""
              INSERT INTO receipts (id, supplier_id, purchase_order_id, note)
              VALUES (%s, %s, %s, %s)
            """, (str(rid), str(supplier_id), str(po_id), note))

            # 2) 각 라인 처리 (수량 검증 포함)
            for it in items:
                po_item_id = it["po_item_id"]
                qty = float(it.get("qty") or 0)
                price = float(it.get("unit_price") or 0)
                expiry_date = it.get("expiry_date")
                note_item = it.get("note")

                if qty <= 0:
                    raise ValueError("qty must be > 0")

                # 주문 수량/기수령 확인
                cur.execute("SELECT ingredient_id, qty FROM purchase_order_items WHERE id=%s", (str(po_item_id),))
                r = cur.fetchone()
                if not r:
                    raise ValueError("po_item not found")
                ing_id, ordered_qty = r[0], float(r[1])

                cur.execute("SELECT COALESCE(SUM(qty),0) FROM receipt_items WHERE po_item_id=%s", (str(po_item_id),))
                received_so_far = float(cur.fetchone()[0] or 0)

                remaining = ordered_qty - received_so_far
                if qty > remaining + 1e-9:
                    raise ValueError(f"qty({qty}) > remaining({remaining})")

                # receipt_items 입력
                cur.execute("""
                  INSERT INTO receipt_items
                    (id, receipt_id, po_item_id, ingredient_id, qty, unit_price, location_id, expiry_date, note)
                  VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    str(rid), str(po_item_id), str(ing_id), qty, price,
                    str(loc_id) if loc_id else None, expiry_date, note_item
                ))

            # 3) 발주 상태 갱신 (모두 수령되면 closed)
            cur.execute("""
              SELECT SUM(poi.qty) AS ordered, COALESCE(SUM(ri.qty),0) AS received
              FROM purchase_order_items poi
              LEFT JOIN receipt_items ri ON ri.po_item_id = poi.id
              WHERE poi.purchase_order_id = %s
            """, (str(po_id),))
            ordered, received = cur.fetchone()
            if float(received or 0) + 1e-9 >= float(ordered or 0):
                cur.execute("UPDATE purchase_orders SET status='closed' WHERE id=%s", (str(po_id),))

    return rid
