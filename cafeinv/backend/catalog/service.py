from backend.core.db import get_cursor

# ---------- Categories ----------
def list_categories(cat_type: str | None = None):
    with get_cursor() as cur:
        if cat_type:
            cur.execute("SELECT * FROM categories WHERE type=%s ORDER BY name;", (cat_type,))
        else:
            cur.execute("SELECT * FROM categories ORDER BY type, name;")
        return cur.fetchall()

def create_category(name: str, cat_type: str):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO categories(name, type) VALUES (%s, %s) RETURNING *;",
            (name, cat_type)
        )
        return cur.fetchone()

# ---------- Suppliers ----------
def list_suppliers(active_only: bool = False):
    with get_cursor() as cur:
        if active_only:
            cur.execute("SELECT * FROM suppliers WHERE is_active=TRUE ORDER BY name;")
        else:
            cur.execute("SELECT * FROM suppliers ORDER BY name;")
        return cur.fetchall()

def create_supplier(data: dict):
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO suppliers(name, contact, phone, email, address, is_active)
            VALUES (%s,%s,%s,%s,%s,COALESCE(%s, TRUE))
            RETURNING *;
            """,
            (data["name"], data.get("contact"), data.get("phone"),
             data.get("email"), data.get("address"), data.get("is_active"))
        )
        return cur.fetchone()

def deactivate_supplier(supplier_id: str):
    with get_cursor(commit=True) as cur:
        cur.execute("UPDATE suppliers SET is_active=FALSE WHERE id=%s RETURNING *;", (supplier_id,))
        return cur.fetchone()

# ---------- Units / Locations / Users (ref) ----------
def ref_units():
    with get_cursor() as cur:
        cur.execute("SELECT id, name, base, to_base FROM units ORDER BY name;")
        return cur.fetchall()

def ref_locations():
    with get_cursor() as cur:
        cur.execute("SELECT id, name FROM locations WHERE is_active=TRUE ORDER BY name;")
        return cur.fetchall()

def ref_users():
    with get_cursor() as cur:
        cur.execute("SELECT id, name FROM users WHERE is_active=TRUE ORDER BY name;")
        return cur.fetchall()

def ref_ingredients(active_only: bool = True):
    with get_cursor() as cur:
        if active_only:
            cur.execute("SELECT id, name FROM ingredients WHERE is_active=TRUE ORDER BY name;")
        else:
            cur.execute("SELECT id, name FROM ingredients ORDER BY name;")
        return cur.fetchall()

# ---------- Ingredients ----------
def create_ingredient(data: dict):
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO ingredients
              (name, unit_id, category_id, description,
               safety_stock_default, reorder_point_default,
               responsible_user_id, cost_per_unit)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING *;
            """,
            (data["name"], data["unit_id"], data.get("category_id"),
             data.get("description"), data.get("safety_stock_default", 0),
             data.get("reorder_point_default", 0), data.get("responsible_user_id"),
             data.get("cost_per_unit", 0))
        )
        return cur.fetchone()

# ---------- Menu & Recipes ----------
def list_menu_items(active_only: bool = False):
    with get_cursor() as cur:
        if active_only:
            cur.execute("SELECT * FROM menu_items WHERE is_active=TRUE ORDER BY name;")
        else:
            cur.execute("SELECT * FROM menu_items ORDER BY name;")
        return cur.fetchall()

def create_menu_item(data: dict):
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO menu_items(name, price, category_id, default_location_id, is_active)
            VALUES (%s,%s,%s,%s,%s) RETURNING *;
            """,
            (data["name"], data["price"], data.get("category_id"),
             data.get("default_location_id"), data.get("is_active", True))
        )
        return cur.fetchone()

def list_recipes(menu_item_id: str):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT r.menu_item_id, r.ingredient_id, r.qty_required,
                   i.name AS ingredient_name
            FROM recipes r
            JOIN ingredients i ON i.id = r.ingredient_id
            WHERE r.menu_item_id = %s
            ORDER BY ingredient_name;
            """,
            (menu_item_id,)
        )
        return cur.fetchall()

def upsert_recipe(menu_item_id: str, ingredient_id: str, qty_required: float):
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO recipes(menu_item_id, ingredient_id, qty_required)
            VALUES (%s,%s,%s)
            ON CONFLICT (menu_item_id, ingredient_id)
            DO UPDATE SET qty_required = EXCLUDED.qty_required
            RETURNING *;
            """,
            (menu_item_id, ingredient_id, qty_required)
        )
        return cur.fetchone()

def delete_recipe(menu_item_id: str, ingredient_id: str):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM recipes WHERE menu_item_id=%s AND ingredient_id=%s;",
            (menu_item_id, ingredient_id)
        )
        return {"ok": True}
