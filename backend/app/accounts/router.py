from fastapi import APIRouter

from app.accounts.dependencies import AuthenticatedUser

router = APIRouter(prefix="/auth", tags=["accounts (A)"])


@router.get("/me")
def me(user: AuthenticatedUser):
    return {"id": user.id, "auth_mode": "local-development"}
