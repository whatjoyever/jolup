# backend/routers/recipes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from backend.db import get_db
router = APIRouter()

@router.get("/health")
def health():
    return {"ok": True, "router": "recipes"}

@router.get("")
def list_recipes(menu_item_id: Optional[str] = None, db: Session = Depends(get_db)):
    params: Dict[str, Any] = {}
    where = ""
    if menu_item_id:
        where = "WHERE menu_item_id = :mid"
        params["mid"] = menu_item_id

    rows = db.execute(
        text(f"""
            SELECT menu_item_id::text, ingredient_id::text, qty_required::float
            FROM recipes
            {where}
            ORDER BY menu_item_id, ingredient_id
        """),
        params
    ).mappings().all()
    return [dict(r) for r in rows]

@router.post("")
def upsert_recipe(payload: Dict[str, Any], db: Session = Depends(get_db)):
    mid = payload.get("menu_item_id")
    items: List[Dict[str, Any]] = payload.get("ingredients") or []
    if not mid:
        raise HTTPException(400, "menu_item_id is required")
    with db.begin():
        db.execute(text("DELETE FROM recipes WHERE menu_item_id = :mid"), {"mid": mid})
        for it in items:
            ing = it.get("ingredient_id")
            qty = float(it.get("qty_required", 0))
            if not ing:
                continue
            db.execute(
                text("""
                    INSERT INTO recipes(menu_item_id, ingredient_id, qty_required)
                    VALUES (:mid, :ing, :qty)
                """),
                {"mid": mid, "ing": ing, "qty": qty}
            )
    return {"ok": True, "menu_item_id": mid, "count": len(items)}
