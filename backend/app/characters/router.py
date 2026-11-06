from fastapi import APIRouter, HTTPException

from app.accounts.dependencies import AuthenticatedUser

router = APIRouter(prefix="/characters", tags=["characters (A)"])


@router.get("/me")
def character(user: AuthenticatedUser):
    raise HTTPException(
        501, detail={"code": "NOT_IMPLEMENTED", "message": "A 담당: 캐릭터 조회를 구현해 주세요."}
    )
