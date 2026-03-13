# backend/app/routers/auth.py
"""
鉴权路由
- POST /login ：用户登录，返回 JWT Token
- GET  /me    ：获取当前已认证用户信息
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.security import (
    create_access_token,
    get_current_user,
    verify_password,
    get_password_hash,
)
from app.models.all_models import User
from app.schemas.api_schemas import Token, UserOut, UserPasswordUpdate, MessageResponse

router = APIRouter(tags=["鉴权"])


@router.post("/login", response_model=MessageResponse, summary="用户登录")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    使用用户名和密码登录，校验通过后。
    注意：此接口实际并不会返回 JWT 到响应体中，而是会在响应头中设置 HttpOnly 的 'access_token' Cookie 并返回一段简单的成功信息。
    """
    result = await db.execute(
        select(User).where(User.username == form_data.username)
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(
        form_data.password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user.username, "tv": user.token_version}
    )
    
    response_data = MessageResponse(message="登录成功")
    response = JSONResponse(content=response_data.model_dump())
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return response

@router.post("/logout", summary="用户登出")
async def logout():
    """
    清除浏览器的 Access Token Cookie。
    """
    response = MessageResponse(message="登出成功")
    response_obj = JSONResponse(content=response.model_dump())
    response_obj.delete_cookie("access_token")
    return response_obj


@router.get("/me", response_model=UserOut, summary="获取当前用户")
async def read_current_user(
    current_user: User = Depends(get_current_user),
):
    """
    返回当前已认证用户的基本信息（不含密码哈希）。
    """
    return current_user


@router.put("/password", response_model=MessageResponse, summary="修改密码")
async def update_password(
    payload: UserPasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    验证旧密码并修改为新密码。
    """
    if not verify_password(payload.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码不正确",
        )
        
    current_user.password_hash = get_password_hash(payload.new_password)
    current_user.token_version += 1
    await db.flush()
    return MessageResponse(message="密码修改成功，请重新登录")
