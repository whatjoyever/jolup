from fastapi import APIRouter
from backend.core.db import get_cursor

router = APIRouter()

@router.get("/health")
def health():
    ok = True
    db_ok = None
    try:
        with get_cursor() as cur:
            cur.execute("SELECT 1 AS ok;")
            db_ok = cur.fetchone()["ok"] == 1
    except Exception:
        ok = False
        db_ok = False
    return {"ok": ok, "db": db_ok}
