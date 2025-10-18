import os
import uvicorn
from fastapi import FastAPI
from backend.health.router import router as health_router
from backend.alerts.router import router as alerts_router
from backend.catalog.router import router as catalog_router
from backend.inventory.router import router as inventory_router
from backend.core.config import APP_HOST, APP_PORT

app = FastAPI(title="Cafe Inventory API")

# 라우터
app.include_router(health_router, tags=["Health"])
app.include_router(alerts_router, prefix="/alerts", tags=["Alerts"])
app.include_router(catalog_router, tags=["Catalog"])
app.include_router(inventory_router, prefix="/inventory", tags=["Inventory"])

# 선택: /inventory_tx 호환 경로 (Streamlit에서 고정 경로일 경우 활성화)
# from inventory.router import get_inventory_tx_compat
# app.add_api_route("/inventory_tx", get_inventory_tx_compat, methods=["GET"], tags=["Inventory"])

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.getenv("APP_HOST", APP_HOST),
        port=int(os.getenv("APP_PORT", APP_PORT)),
        reload=True,
    )
