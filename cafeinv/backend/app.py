# backend/app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 로컬 모듈
from db import get_db  # noqa: F401  # 의존성 주입 경로 확인용 (직접 사용하진 않지만 import 유지)
from routers import recipes, sales, inventory

app = FastAPI(title="Cafe Inventory Backend")

# CORS (Streamlit 브라우저 접근 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # 필요 시 도메인 화이트리스트로 제한 가능
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True}

# ---- 라우터 연결 ----
# /recipes, /sales 는 prefix를 명시적으로 유지
app.include_router(recipes.router, prefix="/recipes", tags=["Recipes"])
app.include_router(sales.router,   prefix="/sales",   tags=["Sales"])

# inventory 라우터는 내부에서 경로를 절대 경로로 정의함 (/inventory, /inventory_tx, /stock_change)
app.include_router(inventory.router, tags=["Inventory"])
