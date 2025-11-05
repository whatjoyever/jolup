<<<<<<< Updated upstream
# import os
# import psycopg2
# from psycopg2.extras import RealDictCursor
# from dotenv import load_dotenv

# load_dotenv()

# def get_connection():
#     conn = psycopg2.connect(
#         host=os.getenv("DB_HOST", "capstonecafe.cxeowumkgzt3.ap-northeast-2.rds.amazonaws.com"),
#         port=os.getenv("DB_PORT", "5432"),
#         dbname=os.getenv("DB_NAME", "cafeinven"),
#         user=os.getenv("DB_USER", "hwjang"),
#         password=os.getenv("DB_PASSWORD")
#     )
#     return conn
=======
# backend/db.py
import os
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ✅ .env 자동 로드
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
except Exception:
    pass

def _ensure_sslmode(url: str) -> str:
    if not url:
        return url
    parsed = urlparse(url)
    q = dict(parse_qsl(parsed.query))
    if "sslmode" not in q:
        q["sslmode"] = "require"
    new_query = urlencode(q)
    return urlunparse(parsed._replace(query=new_query))

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://user:pass@localhost:5432/stockmate"
)
DATABASE_URL = _ensure_sslmode(DATABASE_URL)

# ✅ 실행 중 어떤 호스트로 붙는지 눈으로 확인(비번 마스킹)
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
        return urlunparse((p.scheme, netloc, p.path, p.params, p.query, p.fragment))
    except Exception:
        return u

print(f"[DB] Using DATABASE_URL = { _mask_url(DATABASE_URL) }")

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
>>>>>>> Stashed changes
