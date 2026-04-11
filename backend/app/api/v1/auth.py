from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, decode_token
from app.models import User
from app.schemas import (
    UserCreate, UserResponse, UserUpdate, LoginRequest,
    LoginResponse, ChangePasswordRequest, MessageResponse
)
from app.core.config import settings

router = APIRouter()
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token无效或已过期"
        )

    user_id = int(payload.get("sub"))
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在"
        )

    return user


@router.post("/register", response_model=MessageResponse)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    # 检查邮箱是否已存在
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册"
        )

    # 创建用户
    user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        nickname=user_data.nickname
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return MessageResponse(
        code=201,
        message="注册成功",
        data={
            "id": user.id,
            "email": user.email,
            "nickname": user.nickname
        }
    )


@router.post("/login", response_model=MessageResponse)
async def login(login_data: LoginRequest, db: AsyncSession = Depends(get_db)):
    # 查找用户
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误"
        )

    # 生成Token
    token = create_access_token({"sub": str(user.id), "email": user.email})

    return MessageResponse(
        message="登录成功",
        data={
            "access_token": token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    )


@router.get("/me", response_model=MessageResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return MessageResponse(
        data={
            "id": current_user.id,
            "email": current_user.email,
            "nickname": current_user.nickname,
            "avatar": current_user.avatar,
            "created_at": current_user.created_at.isoformat()
        }
    )


@router.put("/me", response_model=MessageResponse)
async def update_me(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if user_data.nickname:
        current_user.nickname = user_data.nickname
    if user_data.avatar:
        current_user.avatar = user_data.avatar

    await db.commit()
    await db.refresh(current_user)

    return MessageResponse(
        message="更新成功",
        data={
            "id": current_user.id,
            "email": current_user.email,
            "nickname": current_user.nickname,
            "avatar": current_user.avatar
        }
    )


@router.put("/password", response_model=MessageResponse)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 验证旧密码
    if not verify_password(password_data.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码错误"
        )

    # 更新密码
    current_user.password_hash = get_password_hash(password_data.new_password)
    await db.commit()

    return MessageResponse(message="密码修改成功")