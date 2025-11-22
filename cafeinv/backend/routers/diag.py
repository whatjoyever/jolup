# backend/routers/diag.py
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from urllib.parse import urlparse, parse_qsl
import os

from backend.db import get_db, DATABASE_URL  # DATABASE_URL을 그대로 확인

router = APIRouter()

def _mask_url(u: str) -> str:
    try:
        p = urlparse(u)
        netloc = p.netloc
        if "@" in netloc:
            creds, host = netloc.split("@", 1)
            if ":" in creds:
                user, _pw = creds.split(":", 1)
                netloc = f"{user}:****@{host}"
            else:
                netloc = f"{creds}@{host}"
        return f"{p.scheme}://{netloc}{p.path}?{p.query}"
    except Exception:
        return u

@router.get("/diag/env")
def diag_env():
    # 현재 프로세스가 사용 중인 DB URL 요약
    parsed = urlparse(DATABASE_URL or "")
    q = dict(parse_qsl(parsed.query))
    return {
        "cwd": os.getcwd(),
        "DATABASE_URL_masked": _mask_url(DATABASE_URL or ""),
        "host": parsed.hostname,
        "port": parsed.port,
        "db": parsed.path.lstrip("/"),
        "sslmode": q.get("sslmode"),
        "driver": parsed.scheme,  # e.g., postgresql+psycopg2
        "note": "이 값에 localhost가 보이면 .env 미로드 상태!"
    }

@router.get("/diag/dbcheck")
def diag_dbcheck(db: Session = Depends(get_db)):
    try:
        v = db.execute(text("SELECT version()")).scalar()
        one = db.execute(text("SELECT 1")).scalar()
        return {"ok": True, "version": v, "select1": one}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@router.get("/diag/tables")
def diag_tables(db: Session = Depends(get_db)):
    rows = db.execute(text("""
        select table_name
        from information_schema.tables
        where table_schema = 'public'
        order by table_name
    """)).mappings().all()
    return {"tables": [r["table_name"] for r in rows]}
