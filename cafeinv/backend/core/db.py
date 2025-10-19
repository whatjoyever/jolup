import psycopg2
from contextlib import contextmanager

# ---- 임시: RDS 강제 하드코딩 (문제 해결용) ----
DB_CFG = dict(
    host="capstonecafe.cxeowumkgzt3.ap-northeast-2.rds.amazonaws.com",
    port=5432,
    dbname="cafeinven",
    user="hwjang",
    password="capstone1234",  # TODO: 실제 비번 입력
    sslmode="require",
)

# 기동 시 실제 적용 파라미터(비번 제외) 출력
print("[DB][HARD] Using:", {k: v for k, v in DB_CFG.items() if k != "password"})
print("[DB][HARD] db.py path:", __file__)

@contextmanager
def get_cursor():
    conn = psycopg2.connect(**DB_CFG)
    try:
        with conn:
            with conn.cursor() as cur:
                yield cur
    finally:
        conn.close()