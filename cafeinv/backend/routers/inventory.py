# backend/routers/inventory.py
from __future__ import annotations

from typing import Optional, Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.db import get_db

router = APIRouter(prefix="", tags=["Inventory"])

# ---------- helpers ----------
def has_table(db: Session, table: str) -> bool:
    return bool(
        db.execute(
            text(
                """
            SELECT 1
            FROM information_schema.tables
            WHERE table_name = :t
            LIMIT 1
            """
            ),
            {"t": table},
        ).scalar()
    )


def has_column(db: Session, table: str, column: str) -> bool:
    return bool(
        db.execute(
            text(
                """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = :t AND column_name = :c
            LIMIT 1
            """
            ),
            {"t": table, "c": column},
        ).scalar()
    )


def build_inv_tx_select(db: Session) -> str:
    parts: List[str] = []

    parts.append("id::text as id" if has_column(db, "inventory_tx", "id") else "NULL::text as id")
    parts.append(
        "ingredient_id::text as ingredient_id"
        if has_column(db, "inventory_tx", "ingredient_id")
        else "NULL::text as ingredient_id"
    )
    parts.append(
        "location_id::text as location_id"
        if has_column(db, "inventory_tx", "location_id")
        else "NULL::text as location_id"
    )

    if has_column(db, "inventory_tx", "tx_type"):
        parts.append("tx_type as tx_type")
    elif has_column(db, "inventory_tx", "type"):
        parts.append('"type" as tx_type')
    else:
        parts.append("''::text as tx_type")

    parts.append(
        "qty_delta::float as qty_delta"
        if has_column(db, "inventory_tx", "qty_delta")
        else "0.0::float as qty_delta"
    )
    parts.append(
        "ref_table as ref_table"
        if has_column(db, "inventory_tx", "ref_table")
        else "NULL::text as ref_table"
    )
    parts.append(
        "ref_id::text as ref_id"
        if has_column(db, "inventory_tx", "ref_id")
        else "NULL::text as ref_id"
    )
    parts.append("note as note" if has_column(db, "inventory_tx", "note") else "NULL::text as note")
    parts.append(
        "created_at as created_at"
        if has_column(db, "inventory_tx", "created_at")
        else "now() as created_at"
    )
    return ",\n       ".join(parts)


def build_where(
    db: Session,
    ingredient_id: Optional[str],
    location_id: Optional[str],
    since: Optional[str],
    params: Dict[str, Any],
) -> str:
    conds: List[str] = []
    if ingredient_id and has_column(db, "inventory_tx", "ingredient_id"):
        conds.append("ingredient_id = :ing")
        params["ing"] = ingredient_id
    if location_id and has_column(db, "inventory_tx", "location_id"):
        conds.append("location_id = :loc")
        params["loc"] = location_id
    if since and has_column(db, "inventory_tx", "created_at"):
        conds.append("created_at >= :since")
        params["since"] = since
    return f"WHERE {' AND '.join(conds)}" if conds else ""


def build_order_by(db: Session) -> str:
    if has_column(db, "inventory_tx", "created_at"):
        return "ORDER BY created_at DESC"
    elif has_column(db, "inventory_tx", "id"):
        return "ORDER BY id DESC"
    else:
        return ""


# ---------- APIs ----------

@router.get("/inventory")
def list_inventory(
    ingredient_id: Optional[str] = None,
    location_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    현재 재고(inv_stock)를 조회하면서,
    - ingredient_name (재료 이름)
    - location_name   (위치 이름)
    - unit_name       (단위, g/ml/ea 등)
    까지 함께 내려주는 엔드포인트.
    """
    if not has_table(db, "inv_stock"):
        return []

    # 기본 조건 + 파라미터
    params: Dict[str, Any] = {}
    conds: List[str] = []
    if ingredient_id:
        conds.append("s.ingredient_id = :ing")
        params["ing"] = ingredient_id
    if location_id:
        conds.append("s.location_id = :loc")
        params["loc"] = location_id

    where_clause = f"WHERE {' AND '.join(conds)}" if conds else ""

    sql = f"""
        SELECT
            s.ingredient_id::text AS ingredient_id,
            COALESCE(i.name, '')  AS ingredient_name,
            s.location_id::text   AS location_id,
            COALESCE(l.name, '')  AS location_name,
            COALESCE(s.qty_on_hand, 0)::float AS qty_on_hand,
            COALESCE(u.name, '')  AS unit_name
        FROM inv_stock AS s
        LEFT JOIN ingredients AS i ON i.id = s.ingredient_id
        LEFT JOIN locations  AS l ON l.id = s.location_id
        LEFT JOIN units      AS u ON u.id = i.unit_id
        {where_clause}
        ORDER BY ingredient_name, location_name
    """

    rows = db.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]


@router.get("/inventory_tx")
def list_inventory_tx(
    ingredient_id: Optional[str] = None,
    location_id: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    try:
        if not has_table(db, "inventory_tx"):
            return []

        select_cols = build_inv_tx_select(db)
        params: Dict[str, Any] = {"lim": int(limit)}
        where = build_where(db, ingredient_id, location_id, since, params)
        order_by = build_order_by(db)

        sql = f"""
            SELECT {select_cols}
            FROM inventory_tx
            {where}
            {order_by}
            LIMIT :lim
        """
        rows = db.execute(text(sql), params).mappings().all()
        return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"/inventory_tx failed: {e}")


@router.post("/stock_change")
def apply_stock_change(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
):
    if not has_table(db, "inv_stock"):
        raise HTTPException(500, "inv_stock table not found")
    if not has_table(db, "inventory_tx"):
        raise HTTPException(500, "inventory_tx table not found")

    ing = payload.get("ingredient_id")
    loc = payload.get("location_id")
    delta = float(payload.get("qty_delta", 0))
    tx_type_in = payload.get("tx_type") or payload.get("type") or "adjustment"
    note = payload.get("note")

    if not ing or not loc:
        raise HTTPException(400, "ingredient_id/location_id 필요")

    has_tx_type = has_column(db, "inventory_tx", "tx_type")
    has_type = has_column(db, "inventory_tx", "type")

    if has_tx_type:
        insert_sql = """
            INSERT INTO inventory_tx(id, ingredient_id, location_id, tx_type, qty_delta, ref_table, ref_id, note)
            VALUES (gen_random_uuid(), :ing, :loc, :tt, :d, 'manual', NULL, :note)
        """
    elif has_type:
        insert_sql = """
            INSERT INTO inventory_tx(id, ingredient_id, location_id, "type", qty_delta, ref_table, ref_id, note)
            VALUES (gen_random_uuid(), :ing, :loc, :tt, :d, 'manual', NULL, :note)
        """
    else:
        insert_sql = """
            INSERT INTO inventory_tx(id, ingredient_id, location_id, qty_delta, ref_table, ref_id, note)
            VALUES (gen_random_uuid(), :ing, :loc, :d, 'manual', NULL, :note)
        """

    # 🔧 여기부터 트랜잭션 처리 변경
    try:
        # 재고 이력 기록
        db.execute(
            text(insert_sql),
            {"ing": ing, "loc": loc, "tt": tx_type_in, "d": delta, "note": note},
        )
        # 현재 재고 반영
        db.execute(
            text(
                """
                INSERT INTO inv_stock(ingredient_id, location_id, qty_on_hand)
                VALUES (:ing, :loc, 0)
                ON CONFLICT (ingredient_id, location_id)
                DO UPDATE
                SET qty_on_hand = inv_stock.qty_on_hand + :d
                """
            ),
            {"ing": ing, "loc": loc, "d": delta},
        )

        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"/stock_change failed: {e}")

    # 변경 이후 잔액 조회
    bal = (
        db.execute(
            text(
                """
            SELECT COALESCE(qty_on_hand,0)::float
            FROM inv_stock
            WHERE ingredient_id = :ing AND location_id = :loc
            """
            ),
            {"ing": ing, "loc": loc},
        ).scalar()
        or 0.0
    )

    return {"ingredient_id": ing, "location_id": loc, "balance": float(bal)}

