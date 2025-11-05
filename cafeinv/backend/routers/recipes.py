
# routers/recipes.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Any, Dict, List

from db import get_db
from schemas import RecipeUpsertIn

router = APIRouter(prefix="/recipes", tags=["recipes"])

@router.get("")
def list_recipes(menu_item_id: str | None = None, db: Session = Depends(get_db)):
    if menu_item_id:
        rows = db.execute(text("""
            select r.menu_item_id::text,
                   r.ingredient_id::text,
                   r.qty_required::float,
                   i.name as ingredient_name
            from recipes r
            left join ingredients i on i.id = r.ingredient_id
            where r.menu_item_id = :mid::uuid
            order by i.name nulls last, r.ingredient_id
        """), {"mid": menu_item_id}).mappings().all()
    else:
        rows = db.execute(text("""
            select r.menu_item_id::text,
                   r.ingredient_id::text,
                   r.qty_required::float,
                   i.name as ingredient_name
            from recipes r
            left join ingredients i on i.id = r.ingredient_id
            order by r.menu_item_id, i.name nulls last, r.ingredient_id
            limit 1000
        """)).mappings().all()
    return [dict(r) for r in rows]

@router.post("")
def upsert_recipe(body: RecipeUpsertIn, db: Session = Depends(get_db)):
    if not body.ingredients:
        raise HTTPException(400, "NO_INGREDIENTS")

    # 메뉴/재료 존재 확인
    m_ok = db.execute(text("select 1 from menu_items where id=:mid::uuid"), {"mid": str(body.menu_item_id)}).scalar()
    if not m_ok:
        raise HTTPException(404, "MENU_NOT_FOUND")

    for it in body.ingredients:
        ing_ok = db.execute(text("select 1 from ingredients where id=:iid::uuid"), {"iid": str(it.ingredient_id)}).scalar()
        if not ing_ok:
            raise HTTPException(404, f"ING_NOT_FOUND:{it.ingredient_id}")

    with db.begin():
        db.execute(text("delete from recipes where menu_item_id = :mid::uuid"),
                   {"mid": str(body.menu_item_id)})
        for it in body.ingredients:
            db.execute(text("""
                insert into recipes(menu_item_id, ingredient_id, qty_required)
                values(:mid::uuid, :ing::uuid, :qty::float)
            """), {"mid": str(body.menu_item_id),
                   "ing": str(it.ingredient_id),
                   "qty": float(it.qty_required)})
    return {"ok": True, "menu_item_id": str(body.menu_item_id), "count": len(body.ingredients)}
