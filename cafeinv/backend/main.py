# backend/main.py
import os
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.health.router import router as health_router
from backend.alerts.router import router as alerts_router
from backend.catalog.router import router as catalog_router
from backend.inventory.router import router as inventory_router
from backend.core.config import APP_HOST, APP_PORT

app = FastAPI(title="Cafe Inventory API")

# CORS (Streamlit 등 프론트 호출 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 라우터
app.include_router(health_router, tags=["Health"])
app.include_router(alerts_router, prefix="/alerts", tags=["Alerts"])
app.include_router(catalog_router, tags=["Catalog"])
app.include_router(inventory_router, prefix="/inventory", tags=["Inventory"])

# /inventory_tx 호환 엔드포인트 (Streamlit이 고정 경로로 부르는 경우)
@app.get("/inventory_tx", tags=["Inventory"])
def get_inventory_tx_compat(
    limit: int = Query(50, ge=1, le=1000, description="Max rows")
):
    try:
        from backend.inventory.service import list_inventory_tx  # 있으면 사용
    except Exception:
        # 없으면 임시로 빈 배열(또는 501로 변경 가능)
        return []
    try:
        return list_inventory_tx(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"inventory_tx failed: {e}")

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.getenv("APP_HOST", APP_HOST),
        port=int(os.getenv("APP_PORT", APP_PORT)),
        reload=True,
    )
