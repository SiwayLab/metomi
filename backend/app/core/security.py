# backend/app/core/security.py
"""
Metomi 安全与鉴权模块
- passlib[bcrypt] 密码哈希与验证
- python-jose JWT 令牌签发与解析
- FastAPI 依赖项 get_current_user
"""

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.models.all_models import User

# ── 密码哈希上下文 ──
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── OAuth2 Token 方案 (HttpOnly Cookie) ──
class OAuth2PasswordBearerWithCookie(OAuth2):
    """
    基于 HttpOnly Cookie 的认证提取器。
    
    【安全警告】
    使用 Cookie 传输凭证会带来 CSRF（跨站请求伪造）风险。
    当前系统主要通过配置 `COOKIE_SAMESITE="lax"`（或 "strict"）依赖浏览器机制进行基础防御。
    如果系统未来修改 `CORS_ORIGINS` 允许任意外部域名跨域，并将 `COOKIE_SAMESITE` 降级为 "none"，
    则必须在 FastAPI 中额外引入 CSRF Token 校验中间件（要求前端在 Header 中携带额外的 CSRF 令牌）。
    """
    def __init__(self, tokenUrl: str):
        flows = OAuthFlowsModel(password={"tokenUrl": tokenUrl})
        super().__init__(flows=flows)

    async def __call__(self, request: Request) -> str | None:
        token = request.cookies.get("access_token")
        if not token:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None
        return token

oauth2_scheme = OAuth2PasswordBearerWithCookie(
    tokenUrl=f"{settings.API_V1_PREFIX}/login"
)


# ═══════════════════════════════════════════════════════
#  密码工具
# ═══════════════════════════════════════════════════════

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与哈希值是否匹配"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """将明文密码哈希为 bcrypt 格式"""
    return pwd_context.hash(password)


# ═══════════════════════════════════════════════════════
#  JWT 令牌
# ═══════════════════════════════════════════════════════

def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    """
    签发 JWT 访问令牌。
    data 中应包含 {"sub": username, "tv": token_version}。
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


# ═══════════════════════════════════════════════════════
#  FastAPI 依赖项
# ═══════════════════════════════════════════════════════

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    解析 Bearer Token，从数据库获取当前用户。
    Token 无效或用户不存在时抛出 401 HTTPException。
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError as e:
        raise credentials_exception from e

    result = await db.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    # 校验 token_version：密码修改后旧 Token 自动失效
    token_tv = payload.get("tv", 0)
    if token_tv != user.token_version:
        raise credentials_exception

    return user
