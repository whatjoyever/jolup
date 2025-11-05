
# routers/sales.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Dict, List, Tuple

from db import get_db
from schemas import SaleCreateIn

router = APIRouter(prefix="/sales", tags=["sales"])

@router.get("")
def recent_sales(limit: int = 10, db: Session = Depends(get_db)):
    rows = db.execute(text("""
        select s.id, s.created_at, s.total_amount, s.channel
        from sales s
        order by s.created_at desc
        limit :lim
    """), {"lim": limit}).mappings().all()
    return [dict(r) for r in rows]

@router.post("")
def create_sale(body: SaleCreateIn, db: Session = Depends(get_db)):
    if not body.items:
        raise HTTPException(400, "NO_ITEMS")

    # 0) 메뉴 존재/활성 여부(선택 검증)
    for it in body.items:
        ok = db.execute(
            text("select 1 from menu_items where id = :mid and (is_active is true or is_active is null)"),
            {"mid": str(it.menu_item_id)}
        ).scalar()
        if not ok:
            raise HTTPException(404, f"MENU_NOT_FOUND:{it.menu_item_id}")

    # 1) 레시피 로드 (uuid[] 바인딩)
    mids = [str(it.menu_item_id) for it in body.items]
    recipe_rows = db.execute(text("""
      select menu_item_id::text, ingredient_id::text, qty_required::float
      from recipes
      where menu_item_id = any(:mids::uuid[])
    """), {"mids": mids}).all()

    recipe_map: Dict[str, List[Tuple[str, float]]] = {}
    for mid, ing, qty_req in recipe_rows:
        recipe_map.setdefault(mid, []).append((ing, float(qty_req)))

    # 2) 필요한 총 소모량 집계
    needed: Dict[str, float] = {}
    for it in body.items:
        ritems = recipe_map.get(str(it.menu_item_id), [])
        for ing_id, qty_req in ritems:
            needed[ing_id] = needed.get(ing_id, 0.0) + qty_req * float(it.qty)

    if not needed:
        raise HTTPException(400, "RECIPE_NOT_FOUND")

    # 3) 재고 검증 및 차감 계획 생성
    #    - location_id가 주어지면 해당 위치에서만 차감 (부족하면 409)
    #    - 미주어지면: 여러 위치에서 '큰 재고부터' 그리디로 차감 계획 세움
    plans: Dict[str, List[Tuple[str, float]]] = {}  # ing_id -> [(loc_id, qty_to_deduct), ...]
    loc_given = str(body.location_id) if body.location_id else None

    for ing_id, req in needed.items():
        req_left = float(req)

        if loc_given:
            bal = db.execute(text("""
                select coalesce(qty_on_hand,0)::float
                from inv_stock
                where ingredient_id = :ing and location_id = :loc
            """), {"ing": ing_id, "loc": loc_given}).scalar()
            bal = float(bal or 0.0)
            if bal < req_left:
                raise HTTPException(status_code=409, detail=f"INSUFFICIENT_STOCK:{ing_id}:{bal}<{req_left}")
            plans[ing_id] = [(loc_given, req_left)]
            continue

        # 위치 미지정: 가장 잔고가 큰 순으로 차감 계획
        rows = db.execute(text("""
            select location_id::text, coalesce(qty_on_hand,0)::float as bal
            from inv_stock
            where ingredient_id = :ing and coalesce(qty_on_hand,0) > 0
            order by bal desc
        """), {"ing": ing_id}).all()

        if not rows:
            raise HTTPException(status_code=409, detail=f"INSUFFICIENT_STOCK:{ing_id}:0<{req_left}")

        plan_list: List[Tuple[str, float]] = []
        for loc_id, bal in rows:
            if req_left <= 0:
                break
            use = min(float(bal), req_left)
            plan_list.append((str(loc_id), use))
            req_left -= use

        if req_left > 1e-9:  # 거의 0이 아니면 부족
            total_bal = sum([float(b) for _, b in rows])
            raise HTTPException(status_code=409, detail=f"INSUFFICIENT_STOCK:{ing_id}:{total_bal}<{req}")

        plans[ing_id] = plan_list

    # 4) 트랜잭션: sales / sale_items / inventory_tx / inv_stock 업데이트
    with db.begin():
        sale_id = db.execute(text("""
          insert into sales(channel,total_amount) values(:ch,0) returning id
        """), {"ch": body.channel}).scalar()

        total_amount = 0.0
        for it in body.items:
            line_total = float(it.unit_price) * float(it.qty) - float(it.discount)
            total_amount += line_total
            db.execute(text("""
              insert into sale_items(sale_id,menu_item_id,qty,unit_price,discount)
              values(:sid,:mid,:q,:p,:d)
            """), {"sid": sale_id, "mid": str(it.menu_item_id),
                   "q": float(it.qty), "p": float(it.unit_price), "d": float(it.discount)})

        # 계획에 따라 차감
        for ing_id, chunks in plans.items():
            for loc_id, use_qty in chunks:
                db.execute(text("""
                  insert into inventory_tx(ingredient_id, location_id, tx_type, qty_delta, ref_table, ref_id)
                  values(:ing, :loc, 'sale', :delta, 'sales', :sid)
                """), {"ing": ing_id, "loc": loc_id, "delta": -abs(use_qty), "sid": sale_id})

                db.execute(text("""
                  insert into inv_stock(ingredient_id, location_id, qty_on_hand)
                  values(:ing,:loc,0)
                  on conflict(ingredient_id,location_id) do update
                  set qty_on_hand = inv_stock.qty_on_hand - :req
                """), {"ing": ing_id, "loc": loc_id, "req": abs(use_qty)})

        db.execute(text("update sales set total_amount=:amt where id=:sid"),
                   {"amt": total_amount, "sid": sale_id})

    return {"sale_id": sale_id, "total_amount": total_amount}
