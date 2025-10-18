from typing import Optional
from backend.db import get_connection
import uuid

# ---------- 공통 조회 ----------
def list_units() -> list[dict]:
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT id::text, name, base, to_base FROM units ORDER BY name;")
    rows = cur.fetchall(); conn.close()
    return [{"id": r[0], "name": r[1], "base": r[2], "to_base": float(r[3])} for r in rows]

def list_locations() -> list[dict]:
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT id::text, name FROM locations ORDER BY name;")
    rows = cur.fetchall(); conn.close()
    return [{"id": r[0], "name": r[1]} for r in rows]

def list_suppliers(active_only: bool = True) -> list[dict]:
    conn = get_connection(); cur = conn.cursor()
    if active_only:
        cur.execute("""
            SELECT id::text, name
            FROM suppliers
            WHERE is_active IS DISTINCT FROM FALSE
            ORDER BY name;
        """)
    else:
        cur.execute("""
            SELECT id::text, name
            FROM suppliers
            ORDER BY name;
        """)
    rows = cur.fetchall(); conn.close()
    return [{"id": r[0], "name": r[1]} for r in rows]

def list_users_simple() -> list[dict]:
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT id::text, COALESCE(full_name, username) AS name FROM users WHERE is_active IS DISTINCT FROM FALSE ORDER BY name;")
    rows = cur.fetchall(); conn.close()
    return [{"id": r[0], "name": r[1]} for r in rows]

def list_ingredients_simple() -> list[dict]:
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT id::text, name FROM ingredients WHERE is_active IS DISTINCT FROM FALSE ORDER BY name;")
    rows = cur.fetchall(); conn.close()
    return [{"id": r[0], "name": r[1]} for r in rows]

# ---------- 카테고리 ----------
def create_category(name: str, type_: str) -> dict:
    conn = get_connection(); cur = conn.cursor()
    cid = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO categories (id, name, type) VALUES (%s, %s, %s)
        ON CONFLICT (name, type) DO UPDATE SET name=EXCLUDED.name
        RETURNING id::text, name, type
    """, (cid, name, type_))
    row = cur.fetchone(); conn.commit(); conn.close()
    return {"id": row[0], "name": row[1], "type": row[2]}

def list_categories(type_: Optional[str] = None) -> list[dict]:
    conn = get_connection(); cur = conn.cursor()
    if type_:
        cur.execute("SELECT id::text, name, type FROM categories WHERE type=%s ORDER BY name;", (type_,))
    else:
        cur.execute("SELECT id::text, name, type FROM categories ORDER BY type, name;")
    rows = cur.fetchall(); conn.close()
    return [{"id": r[0], "name": r[1], "type": r[2]} for r in rows]

# ---------- 품목(원재료) ----------
def create_ingredient(payload: dict) -> dict:
    """
    payload keys:
      name, category_id, unit_id, description, safety_stock_default, reorder_point_default, responsible_user_id, cost_per_unit
    """
    conn = get_connection(); cur = conn.cursor()
    iid = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO ingredients
            (id, name, category_id, unit_id, description, safety_stock_default, reorder_point_default,
             responsible_user_id, cost_per_unit, is_active)
        VALUES
            (%s, %s, %s::uuid, %s::uuid, %s, COALESCE(%s,0), COALESCE(%s,0), %s::uuid, COALESCE(%s,0), TRUE)
        RETURNING id::text, name
    """, (
        iid,
        payload.get("name"),
        payload.get("category_id"),
        payload.get("unit_id"),
        payload.get("description"),
        payload.get("safety_stock_default"),
        payload.get("reorder_point_default"),
        payload.get("responsible_user_id"),
        payload.get("cost_per_unit"),
    ))
    row = cur.fetchone(); conn.commit(); conn.close()
    return {"id": row[0], "name": row[1]}

# ---------- 입고(헤더+아이템 일괄) ----------
def create_receipt_with_items(payload: dict) -> dict:
    """
    payload:
      supplier_id (uuid|None), location_id (uuid, required), received_at (iso|None), note (str|None), created_by (uuid|None),
      items: [ { ingredient_id, qty, unit_cost, expiry_date (YYYY-MM-DD|None), lot_code } ...]
    """
    items = payload.get("items") or []
    if not payload.get("location_id"):
        raise ValueError("location_id required")
    if not items:
        raise ValueError("items required")

    conn = get_connection(); cur = conn.cursor()
    rid = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO receipts (id, supplier_id, location_id, received_at, note, created_by)
        VALUES (%s, %s::uuid, %s::uuid, COALESCE(%s::timestamptz, now()), %s, %s::uuid)
        RETURNING id::text, received_at
    """, (rid, payload.get("supplier_id"), payload["location_id"], payload.get("received_at"), payload.get("note"), payload.get("created_by")))
    header = cur.fetchone()

    created = []
    for it in items:
        ri_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO receipt_items (id, receipt_id, ingredient_id, qty, unit_cost, expiry_date, lot_code)
            VALUES (%s, %s::uuid, %s::uuid, %s, %s, %s::date, %s)
            RETURNING id::text
        """, (ri_id, rid, it["ingredient_id"], it["qty"], it.get("unit_cost"), it.get("expiry_date"), it.get("lot_code")))
        created.append({"id": cur.fetchone()[0]})

    conn.commit(); conn.close()
    return {"receipt_id": rid, "received_at": header[1], "items": created}
