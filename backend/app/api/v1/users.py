from fastapi import APIRouter, Depends, HTTPException
from app.api.v1.auth import get_current_user
from app.schemas import MessageResponse

router = APIRouter()


@router.get("/profile", response_model=MessageResponse)
async def get_user_profile(current_user = Depends(get_current_user)):
    return MessageResponse(
        data={
            "id": current_user.id,
            "email": current_user.email,
            "nickname": current_user.nickname,
            "avatar": current_user.avatar
        }
    )