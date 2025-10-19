from backend.core.db import get_cursor

def list_alerts():
    with get_cursor() as cur:
        # ✅ message에 포함된 '%' 문자를 안전하게 처리
        cur.execute("""
            SELECT 
                id, 
                alert_type, 
                REPLACE(message, '%', '%%') AS message, 
                severity, 
                created_at
            FROM alerts
            ORDER BY severity DESC, created_at DESC;
        """)
        return cur.fetchall()
