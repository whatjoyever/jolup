import os
import psycopg2
import psycopg2.extras
from contextlib import contextmanager

@contextmanager
def get_cursor():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        dbname=os.getenv("DB_NAME", "cafeinven"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "capstone1234"),
        port=os.getenv("DB_PORT", 5432),
    )
    try:
        # ✅ DictCursor → RealDictCursor 로 변경
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        yield cur
        conn.commit()
    finally:
        cur.close()
        conn.close()
