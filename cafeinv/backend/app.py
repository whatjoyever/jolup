# backend/app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure local imports work when running from backend/ directory
from .db import get_db  # noqa: F401
from .routers import inventory, recipes, sales, diag
# 맨 위 import들 옆에 추가
from .routers import diag




app = FastAPI(title="Cafe Inventory Backend")

# CORS for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True}

# Routers
app.include_router(inventory.router, tags=["Inventory"])
app.include_router(recipes.router,  prefix="/recipes", tags=["Recipes"])
app.include_router(sales.router,    prefix="/sales",   tags=["Sales"])
# 라우터 등록 라인들 옆에 추가
app.include_router(diag.router,  tags=["Diag"])
