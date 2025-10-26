from fastapi import HTTPException, status

def db_error(e: Exception) -> HTTPException:
    # 필요 시 에러 타입 매핑 확장
    msg = str(e)
    code = status.HTTP_500_INTERNAL_SERVER_ERROR
    if "INSUFFICIENT_STOCK" in msg:
        code = status.HTTP_409_CONFLICT
    return HTTPException(status_code=code, detail=msg)
