from backend.db import get_connection
from backend.models import SaleCreateIn, SaleCreateOut, InventoryRow, AlertRow
import uuid

INSUFFICIENT_ERR = "INSUFFICIENT_STOCK"

# ✅ 재고 조회
# 맨 위에 필요한 import (없으면 추가)
import psycopg2.extras
from .db import get_connection  # 절대/상대 중 프로젝트에서 쓰는 방식 유지

def list_inventory(location_id: str | None = None) -> list[dict]:
    """
    재고 스냅샷 조회. location_id가 있으면 해당 위치만 필터.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if location_id:
                cur.execute(
                    """
                    SELECT
                        inv.ingredient_id::text,
                        inv.location_id::text,
                        ing.name         AS ingredient,
                        loc.name         AS location,
                        COALESCE(inv.qty_on_hand, 0) AS qty,
                        inv.reorder_point,
                        inv.safety_stock,
                        ing.unit_id::text AS unit_id,
                        u.name            AS unit
                    FROM inventory inv
                    JOIN ingredients ing ON ing.id = inv.ingredient_id
                    JOIN locations   loc ON loc.id = inv.location_id
                    LEFT JOIN units  u   ON u.id = ing.unit_id
                    WHERE inv.location_id = %s
                    ORDER BY ing.name;
                    """,
                    (location_id,),
                )
            else:
                cur.execute(
                    """
                    SELECT
                        inv.ingredient_id::text,
                        inv.location_id::text,
                        ing.name         AS ingredient,
                        loc.name         AS location,
                        COALESCE(inv.qty_on_hand, 0) AS qty,
                        inv.reorder_point,
                        inv.safety_stock,
                        ing.unit_id::text AS unit_id,
                        u.name            AS unit
                    FROM inventory inv
                    JOIN ingredients ing ON ing.id = inv.ingredient_id
                    JOIN locations   loc ON loc.id = inv.location_id
                    LEFT JOIN units  u   ON u.id = ing.unit_id
                    ORDER BY loc.name, ing.name;
                    """
                )
            rows = cur.fetchall()
            return [dict(r) for r in rows]



# ✅ 알림 조회
from psycopg2.extras import RealDictCursor

def list_alerts():
    # 1) alerts 테이블 컬럼 셋 파악
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema='public' AND table_name='alerts';
            """)
            cols = {r[0] for r in cur.fetchall()}

    # 2) 존재하는 컬럼에 맞춰 표현식 준비
    id_expr         = "a.id::text" if "id" in cols else "gen_random_uuid()::text"
    type_expr       = "a.alert_type" if "alert_type" in cols else ("a.type" if "type" in cols else "'generic'")
    severity_expr   = "a.severity" if "severity" in cols else ("a.level" if "level" in cols else "'info'")
    message_expr    = "a.message" if "message" in cols else ("a.msg" if "msg" in cols else "''")
    created_at_expr = "a.created_at" if "created_at" in cols else ("a.createdon" if "createdon" in cols else "now()")

    has_ing_id = "ingredient_id" in cols
    has_loc_id = "location_id"   in cols

    # 3) SELECT 컬럼 목록을 리스트로 만들고 join
    select_cols = [
        f"{id_expr} AS id",
        f"{type_expr} AS alert_type",
        f"{message_expr} AS message",
        f"{severity_expr} AS severity",
        f"{created_at_expr} AS created_at",
    ]
    if has_ing_id:
        select_cols += [
            "a.ingredient_id::text AS ingredient_id",
            "ing.name AS ingredient_name",
        ]
    else:
        select_cols += [
            "NULL::text AS ingredient_id",
            "NULL::text AS ingredient_name",
        ]
    if has_loc_id:
        select_cols += [
            "a.location_id::text AS location_id",
            "loc.name AS location_name",
        ]
    else:
        select_cols += [
            "NULL::text AS location_id",
            "NULL::text AS location_name",
        ]

    select_sql = ",\n                ".join(select_cols)

    # 4) JOIN도 조건부로
    join_ing = "LEFT JOIN ingredients ing ON ing.id::text = a.ingredient_id::text" if has_ing_id else ""
    join_loc = "LEFT JOIN locations   loc ON loc.id::text = a.location_id::text"   if has_loc_id else ""

    sql = f"""
        SELECT
                {select_sql}
        FROM alerts a
        {join_ing}
        {join_loc}
        ORDER BY {created_at_expr} DESC
        LIMIT 200;
    """

    # 5) 실행 및 모델 매핑
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall() or []
            return [AlertRow(**{
                "id": r.get("id"),
                "alert_type": r.get("alert_type"),
                "message": r.get("message"),
                "severity": r.get("severity"),
                "created_at": r.get("created_at"),
                "ingredient_id": r.get("ingredient_id"),
                "ingredient_name": r.get("ingredient_name"),
                "location_id": r.get("location_id"),
                "location_name": r.get("location_name"),
            }) for r in rows]




# ✅ 판매 등록 → 트리거 작동 → 재고 차감
def create_sale(payload: SaleCreateIn) -> SaleCreateOut:
    conn = get_connection()
    cur = conn.cursor()

    sale_id = str(uuid.uuid4())
    total_amount = payload.qty * payload.unit_price

    # sales 테이블 삽입
    cur.execute("""
        INSERT INTO sales (id, total_amount, status)
        VALUES (%s, %s, 'paid')
    """, (sale_id, total_amount))

    # sale_items 삽입 (트리거가 여기서 작동)
    cur.execute("""
        INSERT INTO sale_items (sale_id, menu_item_id, qty, unit_price)
        VALUES (%s, %s, %s, %s)
    """, (sale_id, payload.menu_item_id, payload.qty, payload.unit_price))

    conn.commit()
    conn.close()

    return SaleCreateOut(sale_id=sale_id, total_amount=total_amount)

# ====== STEP1 services ======
from backend.db import get_connection
from backend.models import (
    StockChangeIn, StockChangeOut, InventoryTxRow,
    POCreateIn, POCreateOut, POItemAddIn, POReceiveIn, POReceiveOut
)
import uuid
from datetime import datetime, timedelta

def apply_stock_change_service(inp: StockChangeIn) -> StockChangeOut:
    conn = get_connection()
    cur = conn.cursor()
    ref_id = str(uuid.uuid4())
    # balance를 얻고 싶으면 UPDATE 후 SELECT로 현재고 조회
    cur.execute("""
        SELECT apply_stock_change(
            %s::uuid, %s::uuid, %s::numeric,
            %s::tx_type, %s, %s::uuid, %s, %s::uuid
        );
    """, (
        inp.ingredient_id, inp.location_id, inp.qty_delta,
        inp.tx_type, inp.ref_table or 'manual', ref_id,
        inp.note, inp.created_by
    ))
    # 현재 잔액 조회
    cur.execute("""
        SELECT qty_on_hand
        FROM inventory
        WHERE ingredient_id=%s AND location_id=%s
    """, (inp.ingredient_id, inp.location_id))
    row = cur.fetchone()
    conn.commit()
    conn.close()
    return StockChangeOut(ok=True, balance=float(row[0]) if row and row[0] is not None else None)


def list_inventory_tx(ingredient_id: str|None, location_id: str|None,
                      since_iso: str|None, limit: int=50) -> list[InventoryTxRow]:
    conn = get_connection()
    cur = conn.cursor()
    conds, params = [], []
    if ingredient_id:
        conds.append("it.ingredient_id = %s::uuid")
        params.append(ingredient_id)
    if location_id:
        conds.append("it.location_id = %s::uuid")
        params.append(location_id)
    if since_iso:
        conds.append("it.created_at >= %s::timestamptz")
        params.append(since_iso)

    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    cur.execute(f"""
        SELECT it.created_at, it.tx_type::text, ing.name, l.name, it.qty_delta, it.note, it.ref_table
        FROM inventory_tx it
        JOIN ingredients ing ON ing.id = it.ingredient_id
        JOIN locations l  ON l.id  = it.location_id
        {where}
        ORDER BY it.created_at DESC
        LIMIT %s
    """, (*params, max(1, min(limit, 500))))
    rows = cur.fetchall()
    conn.close()
    return [
        InventoryTxRow(
            created_at=r[0], tx_type=r[1], ingredient_name=r[2],
            location_name=r[3], qty_delta=float(r[4]), note=r[5], ref_table=r[6]
        ) for r in rows
    ]


def create_purchase_order(inp: POCreateIn) -> POCreateOut:
    conn = get_connection()
    cur = conn.cursor()
    po_id = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO purchase_orders (id, supplier_id, order_date, expected_date, status, note, created_by)
        VALUES (%s, %s::uuid, %s, %s, 'ordered', %s, %s::uuid)
    """, (po_id, inp.supplier_id, inp.order_date, inp.expected_date, inp.note, inp.created_by))
    conn.commit()
    conn.close()
    return POCreateOut(id=po_id, status="ordered")


def add_po_item(inp: POItemAddIn) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    item_id = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO po_items (id, purchase_order_id, ingredient_id, qty_ordered, unit_cost, qty_received)
        VALUES (%s, %s::uuid, %s::uuid, %s, %s, COALESCE(qty_received,0))
    """, (item_id, inp.purchase_order_id, inp.ingredient_id, inp.qty_ordered, inp.unit_cost))
    conn.commit()
    conn.close()
    return {"id": item_id}


def receive_purchase_order(inp: POReceiveIn) -> POReceiveOut:
    conn = get_connection()
    cur = conn.cursor()
    received = 0
    # 각 품목 입고 → 재고 증가(apply_stock_change 'purchase') + po_items 수량 반영
    for it in inp.items:
        # po_item 존재 확인 및 누적 업데이트
        cur.execute("""
            UPDATE po_items
            SET qty_received = COALESCE(qty_received,0) + %s
            WHERE purchase_order_id=%s::uuid AND ingredient_id=%s::uuid
            RETURNING id
        """, (it.qty_received, inp.purchase_order_id, it.ingredient_id))
        row = cur.fetchone()
        if not row:
            # 라인이 없다면 라인 생성 후 반영(옵션)
            cur.execute("""
                INSERT INTO po_items (id, purchase_order_id, ingredient_id, qty_ordered, unit_cost, qty_received)
                VALUES (%s, %s::uuid, %s::uuid, %s, %s, %s)
            """, (str(uuid.uuid4()), inp.purchase_order_id, it.ingredient_id, it.qty_received, 0, it.qty_received))

        # 재고 증가 (purchase)
        cur.execute("""
            SELECT apply_stock_change(
                %s::uuid, %s::uuid, %s::numeric,
                'purchase'::tx_type, %s, %s::uuid, %s, %s::uuid
            )
        """, (
            it.ingredient_id, inp.location_id, it.qty_received,
            'po_items', str(uuid.uuid4()), f'PO={inp.purchase_order_id}', inp.received_by
        ))
        received += 1

    # 상태 갱신: 모든 라인 수령 완료면 received, 아니면 partially_received
    cur.execute("""
        SELECT SUM(CASE WHEN COALESCE(qty_received,0) >= COALESCE(qty_ordered,0) THEN 1 ELSE 0 END),
               COUNT(*)
        FROM po_items
        WHERE purchase_order_id=%s::uuid
    """, (inp.purchase_order_id,))
    done, total = cur.fetchone()
    new_status = 'received' if total and done == total else 'partially_received'
    cur.execute("UPDATE purchase_orders SET status=%s WHERE id=%s::uuid", (new_status, inp.purchase_order_id))

    conn.commit()
    conn.close()
    return POReceiveOut(purchase_order_id=inp.purchase_order_id, received_count=received, status=new_status)

# ====== STEP2 services ======
from backend.models import (
    CategoryRow, UnitRow, LocationRow, IngredientRow,
    MenuItemCreate, MenuItemUpdate, MenuItemRow,
    RecipeRow, RecipeUpsert,
    SupplierCreate, SupplierUpdate, SupplierRow
)
import uuid

def list_categories(cat_type: str | None = None) -> list[CategoryRow]:
    conn = get_connection(); cur = conn.cursor()
    if cat_type:
        cur.execute("SELECT id, name, type, parent_id FROM categories WHERE type=%s ORDER BY name", (cat_type,))
    else:
        cur.execute("SELECT id, name, type, parent_id FROM categories ORDER BY name")
    rows = cur.fetchall(); conn.close()
    return [CategoryRow(id=r[0], name=r[1], type=r[2], parent_id=r[3]) for r in rows]

def list_units() -> list[UnitRow]:
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT id, name, base, to_base FROM units ORDER BY name")
    rows = cur.fetchall(); conn.close()
    return [UnitRow(id=r[0], name=r[1], base=r[2], to_base=float(r[3])) for r in rows]

def list_locations() -> list[LocationRow]:
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT id, name FROM locations ORDER BY name")
    rows = cur.fetchall(); conn.close()
    return [LocationRow(id=r[0], name=r[1]) for r in rows]

def list_ingredients(active_only: bool=True) -> list[IngredientRow]:
    conn = get_connection(); cur = conn.cursor()
    if active_only:
        cur.execute("SELECT id, name, unit_id, is_active FROM ingredients WHERE is_active=TRUE ORDER BY name")
    else:
        cur.execute("SELECT id, name, unit_id, is_active FROM ingredients ORDER BY name")
    rows = cur.fetchall(); conn.close()
    return [IngredientRow(id=r[0], name=r[1], unit_id=r[2], is_active=r[3]) for r in rows]

def create_menu_item(inp: MenuItemCreate) -> MenuItemRow:
    conn = get_connection(); cur = conn.cursor()
    mid = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO menu_items (id, name, category_id, price, is_active, default_location_id)
        VALUES (%s, %s, %s::uuid, %s, %s, %s::uuid)
    """, (mid, inp.name, inp.category_id, inp.price, bool(inp.is_active), inp.default_location_id))
    conn.commit(); conn.close()
    return MenuItemRow(id=mid, name=inp.name, price=inp.price, category_id=inp.category_id,
                       default_location_id=inp.default_location_id, is_active=bool(inp.is_active))

def update_menu_item(menu_id: str, inp: MenuItemUpdate) -> MenuItemRow:
    conn = get_connection(); cur = conn.cursor()
    # 동적 업데이트
    sets, params = [], []
    if inp.name is not None: sets.append("name=%s"); params.append(inp.name)
    if inp.price is not None: sets.append("price=%s"); params.append(inp.price)
    if inp.category_id is not None: sets.append("category_id=%s::uuid"); params.append(inp.category_id)
    if inp.default_location_id is not None: sets.append("default_location_id=%s::uuid"); params.append(inp.default_location_id)
    if inp.is_active is not None: sets.append("is_active=%s"); params.append(bool(inp.is_active))
    if not sets:  # 변경 없음
        cur.execute("SELECT id, name, price, category_id, default_location_id, is_active FROM menu_items WHERE id=%s::uuid", (menu_id,))
    else:
        q = f"UPDATE menu_items SET {', '.join(sets)} WHERE id=%s::uuid RETURNING id, name, price, category_id, default_location_id, is_active"
        params.append(menu_id)
        cur.execute(q, params)
    row = cur.fetchone(); conn.commit(); conn.close()
    return MenuItemRow(id=row[0], name=row[1], price=float(row[2]), category_id=row[3], default_location_id=row[4], is_active=row[5])

def list_menu_items(active_only: bool=True) -> list[MenuItemRow]:
    conn = get_connection(); cur = conn.cursor()
    if active_only:
        cur.execute("SELECT id, name, price, category_id, default_location_id, is_active FROM menu_items WHERE is_active=TRUE ORDER BY name")
    else:
        cur.execute("SELECT id, name, price, category_id, default_location_id, is_active FROM menu_items ORDER BY name")
    rows = cur.fetchall(); conn.close()
    return [MenuItemRow(id=r[0], name=r[1], price=float(r[2]), category_id=r[3], default_location_id=r[4], is_active=r[5]) for r in rows]

def deactivate_menu_item(menu_id: str) -> dict:
    conn = get_connection(); cur = conn.cursor()
    cur.execute("UPDATE menu_items SET is_active=FALSE WHERE id=%s::uuid", (menu_id,))
    conn.commit(); conn.close()
    return {"ok": True}

def list_recipes(menu_id: str) -> list[RecipeRow]:
    conn = get_connection(); cur = conn.cursor()
    cur.execute("""
        SELECT r.menu_item_id, r.ingredient_id, ing.name, r.qty_required
        FROM recipes r
        JOIN ingredients ing ON ing.id = r.ingredient_id
        WHERE r.menu_item_id=%s::uuid
        ORDER BY ing.name
    """, (menu_id,))
    rows = cur.fetchall(); conn.close()
    return [RecipeRow(menu_item_id=r[0], ingredient_id=r[1], ingredient_name=r[2], qty_required=float(r[3])) for r in rows]

def upsert_recipe(inp: RecipeUpsert) -> RecipeRow:
    conn = get_connection(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO recipes (menu_item_id, ingredient_id, qty_required)
        VALUES (%s::uuid, %s::uuid, %s)
        ON CONFLICT (menu_item_id, ingredient_id)
        DO UPDATE SET qty_required=EXCLUDED.qty_required
        RETURNING menu_item_id, ingredient_id, %s
    """, (inp.menu_item_id, inp.ingredient_id, inp.qty_required, inp.qty_required))
    row = cur.fetchone(); conn.commit(); conn.close()
    # ingredient_name은 별도 조회
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT name FROM ingredients WHERE id=%s::uuid", (inp.ingredient_id,))
    ing_name = cur.fetchone()[0]; conn.close()
    return RecipeRow(menu_item_id=row[0], ingredient_id=row[1], ingredient_name=ing_name, qty_required=float(row[2]))

def delete_recipe(menu_id: str, ingredient_id: str) -> dict:
    conn = get_connection(); cur = conn.cursor()
    cur.execute("DELETE FROM recipes WHERE menu_item_id=%s::uuid AND ingredient_id=%s::uuid", (menu_id, ingredient_id))
    conn.commit(); conn.close(); return {"ok": True}

def create_supplier(inp: SupplierCreate) -> SupplierRow:
    conn = get_connection(); cur = conn.cursor()
    sid = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO suppliers (id, name, contact, phone, email, address, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (sid, inp.name, inp.contact, inp.phone, inp.email, inp.address, bool(inp.is_active)))
    conn.commit(); conn.close()
    return SupplierRow(id=sid, name=inp.name, contact=inp.contact, phone=inp.phone, email=inp.email, address=inp.address, is_active=bool(inp.is_active))

def update_supplier(supplier_id: str, inp: SupplierUpdate) -> SupplierRow:
    conn = get_connection(); cur = conn.cursor()
    sets, params = [], []
    if inp.name is not None: sets.append("name=%s"); params.append(inp.name)
    if inp.contact is not None: sets.append("contact=%s"); params.append(inp.contact)
    if inp.phone is not None: sets.append("phone=%s"); params.append(inp.phone)
    if inp.email is not None: sets.append("email=%s"); params.append(inp.email)
    if inp.address is not None: sets.append("address=%s"); params.append(inp.address)
    if inp.is_active is not None: sets.append("is_active=%s"); params.append(bool(inp.is_active))
    if sets:
        q = f"UPDATE suppliers SET {', '.join(sets)} WHERE id=%s::uuid RETURNING id, name, contact, phone, email, address, is_active"
        params.append(supplier_id); cur.execute(q, params)
    else:
        cur.execute("SELECT id, name, contact, phone, email, address, is_active FROM suppliers WHERE id=%s::uuid", (supplier_id,))
    row = cur.fetchone(); conn.commit(); conn.close()
    return SupplierRow(id=row[0], name=row[1], contact=row[2], phone=row[3], email=row[4], address=row[5], is_active=row[6])

def list_suppliers(active_only: bool=True) -> list[SupplierRow]:
    conn = get_connection(); cur = conn.cursor()
    if active_only:
        cur.execute("SELECT id, name, contact, phone, email, address, is_active FROM suppliers WHERE is_active=TRUE ORDER BY name")
    else:
        cur.execute("SELECT id, name, contact, phone, email, address, is_active FROM suppliers ORDER BY name")
    rows = cur.fetchall(); conn.close()
    return [SupplierRow(id=r[0], name=r[1], contact=r[2], phone=r[3], email=r[4], address=r[5], is_active=r[6]) for r in rows]

def deactivate_supplier(supplier_id: str) -> dict:
    conn = get_connection(); cur = conn.cursor()
    cur.execute("UPDATE suppliers SET is_active=FALSE WHERE id=%s::uuid", (supplier_id,))
    conn.commit(); conn.close(); return {"ok": True}

# ====== STEP3 services ======
from backend.models import (
    TransferCreate, TransferRow, TransferItemAdd, TransferItemRow, TransferAction,
    AuditLogRow
)
import uuid

def create_transfer(inp: TransferCreate) -> TransferRow:
    conn = get_connection(); cur = conn.cursor()
    tid = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO transfers (id, from_location_id, to_location_id, status, created_by)
        VALUES (%s, %s::uuid, %s::uuid, %s, %s::uuid)
        RETURNING id, from_location_id, to_location_id, status, created_at
    """, (tid, inp.from_location_id, inp.to_location_id, inp.status or 'draft', inp.created_by))
    row = cur.fetchone(); conn.commit(); conn.close()
    return TransferRow(id=row[0], from_location_id=row[1], to_location_id=row[2], status=row[3], created_at=row[4])

def add_transfer_item(inp: TransferItemAdd) -> dict:
    conn = get_connection(); cur = conn.cursor()
    iid = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO transfer_items (id, transfer_id, ingredient_id, qty)
        VALUES (%s, %s::uuid, %s::uuid, %s)
    """, (iid, inp.transfer_id, inp.ingredient_id, inp.qty))
    conn.commit(); conn.close()
    return {"id": iid}

def list_transfers(status: str | None = None, limit: int = 100) -> list[TransferRow]:
    conn = get_connection(); cur = conn.cursor()
    if status:
        cur.execute("""
            SELECT id, from_location_id, to_location_id, status, created_at
            FROM transfers WHERE status=%s
            ORDER BY created_at DESC LIMIT %s
        """, (status, max(1, min(limit, 500))))
    else:
        cur.execute("""
            SELECT id, from_location_id, to_location_id, status, created_at
            FROM transfers
            ORDER BY created_at DESC LIMIT %s
        """, (max(1, min(limit, 500)),))
    rows = cur.fetchall(); conn.close()
    return [TransferRow(id=r[0], from_location_id=r[1], to_location_id=r[2], status=r[3], created_at=r[4]) for r in rows]

def list_transfer_items(transfer_id: str) -> list[TransferItemRow]:
    conn = get_connection(); cur = conn.cursor()
    cur.execute("""
        SELECT ti.id, ti.transfer_id, ti.ingredient_id, ing.name, ti.qty
        FROM transfer_items ti
        JOIN ingredients ing ON ing.id = ti.ingredient_id
        WHERE ti.transfer_id=%s::uuid
        ORDER BY ing.name
    """, (transfer_id,))
    rows = cur.fetchall(); conn.close()
    return [TransferItemRow(id=r[0], transfer_id=r[1], ingredient_id=r[2], ingredient_name=r[3], qty=float(r[4])) for r in rows]

def ship_transfer(inp: TransferAction) -> dict:
    """
    ship 시점: from_location에서 qty만큼 'transfer_out'으로 차감.
    """
    conn = get_connection(); cur = conn.cursor()
    # transfer 본문/아이템/위치 조회
    cur.execute("SELECT from_location_id, to_location_id, status FROM transfers WHERE id=%s::uuid", (inp.transfer_id,))
    tr = cur.fetchone()
    if not tr: raise ValueError("transfer not found")
    from_loc, to_loc, st = tr
    if st not in ('draft', 'canceled'):
        # draft에서만 ship하도록 제한(필요시 완화 가능)
        pass
    # 라인들 차감
    cur.execute("SELECT ingredient_id, qty FROM transfer_items WHERE transfer_id=%s::uuid", (inp.transfer_id,))
    items = cur.fetchall()
    for ing_id, qty in items:
        # from에서 음수 (transfer_out)
        cur.execute("""
            SELECT apply_stock_change(
                %s::uuid, %s::uuid, %s::numeric * -1,
                'transfer_out'::tx_type, %s, %s::uuid, %s, %s::uuid
            )
        """, (ing_id, from_loc, qty, 'transfer_items', str(uuid.uuid4()),
              f'TR_SHIP={inp.transfer_id}', None))
    # 상태 변경
    cur.execute("UPDATE transfers SET status='shipped' WHERE id=%s::uuid", (inp.transfer_id,))
    conn.commit(); conn.close()
    return {"ok": True, "status": "shipped"}

def receive_transfer(inp: TransferAction) -> dict:
    """
    receive 시점: to_location에 qty만큼 'transfer_in'으로 입고.
    """
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT from_location_id, to_location_id, status FROM transfers WHERE id=%s::uuid", (inp.transfer_id,))
    tr = cur.fetchone()
    if not tr: raise ValueError("transfer not found")
    from_loc, to_loc, st = tr
    # 라인들 입고
    cur.execute("SELECT ingredient_id, qty FROM transfer_items WHERE transfer_id=%s::uuid", (inp.transfer_id,))
    items = cur.fetchall()
    for ing_id, qty in items:
        cur.execute("""
            SELECT apply_stock_change(
                %s::uuid, %s::uuid, %s::numeric,
                'transfer_in'::tx_type, %s, %s::uuid, %s, %s::uuid
            )
        """, (ing_id, to_loc, qty, 'transfer_items', str(uuid.uuid4()),
              f'TR_RECV={inp.transfer_id}', None))
    cur.execute("UPDATE transfers SET status='received' WHERE id=%s::uuid", (inp.transfer_id,))
    conn.commit(); conn.close()
    return {"ok": True, "status": "received"}

def list_audit_logs(table_name: str | None, since: str | None, limit: int = 100) -> list[AuditLogRow]:
    conn = get_connection(); cur = conn.cursor()
    conds, params = [], []
    if table_name:
        conds.append("table_name=%s"); params.append(table_name)
    if since:
        conds.append("created_at >= %s::timestamptz"); params.append(since)
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    cur.execute(f"""
        SELECT created_at, table_name, record_id::text, action, user_id::text, before, after
        FROM audit_logs
        {where}
        ORDER BY created_at DESC
        LIMIT %s
    """, (*params, max(1, min(limit, 500))))
    rows = cur.fetchall(); conn.close()
    return [
        AuditLogRow(
            created_at=r[0], table_name=r[1], record_id=r[2], action=r[3], user_id=r[4],
            before=r[5], after=r[6]
        ) for r in rows
    ]
