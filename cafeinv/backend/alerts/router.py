from fastapi import APIRouter
from .service import list_alerts
from backend.core.exceptions import db_error

router = APIRouter()

@router.get("")
def get_alerts():
    return list_alerts()
