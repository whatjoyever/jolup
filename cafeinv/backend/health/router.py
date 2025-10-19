# backend/health/router.py
from fastapi import APIRouter
from backend.core.db import get_cursor

router = APIRouter()

@router.get("/health")
def health_check():
    """API 및 DB 연결 상태 확인"""
    try:
        with get_cursor() as cur:
            cur.execute("SELECT 1;")
            _ = cur.fetchone()
        return {"ok": True, "db": True}
    except Exception as e:
        print("[HealthCheck] DB 연결 실패:", e)
        return {"ok": False, "db": False}
