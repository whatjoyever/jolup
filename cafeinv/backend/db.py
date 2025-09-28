import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "capstonecafe.cxeowumkgzt3.ap-northeast-2.rds.amazonaws.com"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "cafeinven"),
        user=os.getenv("DB_USER", "hwjang"),
        password=os.getenv("DB_PASSWORD")
    )
    return conn
