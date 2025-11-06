# backend/routers/sales.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from backend.db import get_db
router = APIRouter()

@router.get("/health")
def health():
    return {"ok": True, "router": "sales"}

@router.post("")
def create_sale(payload: Dict[str, Any], db: Session = Depends(get_db)):
    loc = payload.get("location_id")
    items: List[Dict[str, Any]] = payload.get("items") or []
    if not loc or not items:
        raise HTTPException(400, "location_id and items required")

    with db.begin():
        sale_id = db.execute(text("SELECT gen_random_uuid()")).scalar()
        total = 0.0
        for it in items:
            qty = float(it.get("qty", 0))
            unit_price = float(it.get("unit_price", 0))
            total += qty * unit_price

        db.execute(
            text("""
                INSERT INTO sales(id, location_id, total_amount)
                VALUES (:id, :loc, :total)
            """),
            {"id": sale_id, "loc": loc, "total": total}
        )

        for it in items:
            menu_item_id = it.get("menu_item_id")
            qty = float(it.get("qty", 0))
            unit_price = float(it.get("unit_price", 0))
            if not menu_item_id or qty <= 0:
                continue
            sale_item_id = db.execute(text("SELECT gen_random_uuid()")).scalar()
            db.execute(
                text("""
                    INSERT INTO sale_items(id, sale_id, menu_item_id, qty, unit_price)
                    VALUES (:id, :sid, :mid, :qty, :price)
                """),
                {"id": sale_item_id, "sid": sale_id, "mid": menu_item_id, "qty": qty, "price": unit_price}
            )

            recipe_rows = db.execute(
                text("""
                    SELECT ingredient_id::text, qty_required::float
                    FROM recipes
                    WHERE menu_item_id = :mid
                """),
                {"mid": menu_item_id}
            ).mappings().all()

            for r in recipe_rows:
                ing = r["ingredient_id"]
                per_one = float(r["qty_required"] or 0.0)
                delta = -(per_one * qty)
                if db.execute(text("""
                    SELECT 1 FROM information_schema.columns
                     WHERE table_name='inventory_tx' AND column_name='tx_type' LIMIT 1
                """)).scalar():
                    insert_tx = text("""
                        INSERT INTO inventory_tx(id, ingredient_id, location_id, tx_type, qty_delta, ref_table, ref_id, note)
                        VALUES (gen_random_uuid(), :ing, :loc, 'sale', :d, 'sale_items', :sid, 'sale deduction')
                    """)
                elif db.execute(text("""
                    SELECT 1 FROM information_schema.columns
                     WHERE table_name='inventory_tx' AND column_name='type' LIMIT 1
                """)).scalar():
                    insert_tx = text("""
                        INSERT INTO inventory_tx(id, ingredient_id, location_id, "type", qty_delta, ref_table, ref_id, note)
                        VALUES (gen_random_uuid(), :ing, :loc, 'sale', :d, 'sale_items', :sid, 'sale deduction')
                    """)
                else:
                    insert_tx = text("""
                        INSERT INTO inventory_tx(id, ingredient_id, location_id, qty_delta, ref_table, ref_id, note)
                        VALUES (gen_random_uuid(), :ing, :loc, :d, 'sale_items', :sid, 'sale deduction')
                    """)
                db.execute(insert_tx, {"ing": ing, "loc": loc, "d": delta, "sid": sale_item_id})

                db.execute(
                    text("""
                        INSERT INTO inv_stock(ingredient_id, location_id, qty_on_hand)
                        VALUES (:ing, :loc, 0)
                        ON CONFLICT (ingredient_id, location_id)
                        DO UPDATE SET qty_on_hand = inv_stock.qty_on_hand + :d
                    """),
                    {"ing": ing, "loc": loc, "d": delta}
                )

    return {"ok": True, "sale_id": str(sale_id), "total_amount": total}
