# backend/app/routers/init.py
"""
系统初始化路由（免 Token 访问）
- GET  /init/status  ：检查系统是否已初始化
- POST /init/setup   ：首次设置管理员账号与基础配置
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_password_hash
from app.core.settings_cache import settings_cache
from app.models.all_models import SystemSetting, User
from app.schemas.api_schemas import SystemSettingUpdate, validate_password_strength
from app.core.limiter import limiter

router = APIRouter(prefix="/init", tags=["系统初始化"])


# ═══════════════════════════════════════════════════════
#  请求 / 响应模型
# ═══════════════════════════════════════════════════════

class InitStatusOut(BaseModel):
    """初始化状态响应"""
    is_initialized: bool


class InitSetupRequest(BaseModel):
    """首次初始化请求体"""
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    language: str = Field("zh-CN", max_length=16)
    settings: list[SystemSettingUpdate] = []

    @field_validator("password")
    @classmethod
    def check_password_strength(cls, v: str) -> str:
        return validate_password_strength(v)


# ═══════════════════════════════════════════════════════
#  路由
# ═══════════════════════════════════════════════════════

@router.get("/status", response_model=InitStatusOut, summary="检查初始化状态")
async def get_init_status(db: AsyncSession = Depends(get_db)):
    """
    返回系统是否已完成初始化。免 Token 访问。
    根据 users 表是否存在记录来判断。
    """
    count_result = await db.execute(select(func.count()).select_from(User))
    user_count = count_result.scalar() or 0
    return InitStatusOut(is_initialized=(user_count > 0))



@router.post("/setup", response_model=dict, summary="首次初始化设置")
@limiter.limit("3/minute")
async def init_setup(
    request: Request,
    body: InitSetupRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    首次系统初始化：创建管理员账号并写入基础配置。
    仅在 users 表为空时允许调用，否则 403 禁止。
    """
    # ── 检查 users 表是否已有用户 ──
    count_result = await db.execute(select(func.count()).select_from(User))
    user_count = count_result.scalar() or 0
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="系统已初始化，禁止重复安装",
        )

    # ── 双重检查: is_initialized 设置项 ──
    init_check = await db.execute(
        select(SystemSetting).where(
            SystemSetting.setting_key == "is_initialized"
        )
    )
    init_flag = init_check.scalar_one_or_none()
    if init_flag is not None and init_flag.setting_value == "true":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="系统已初始化，禁止重复安装 (is_initialized=true)",
        )

    # ── 1) 创建管理员（IntegrityError 兜底防竞态）──
    admin = User(
        username=body.username,
        password_hash=get_password_hash(body.password),
        language=body.language,
    )
    db.add(admin)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名已存在或系统已初始化（并发冲突）",
        )

    # ── 2) 批量写入传入的 system_settings ──
    for item in body.settings:
        existing = await db.execute(
            select(SystemSetting).where(
                SystemSetting.setting_key == item.setting_key
            )
        )
        row = existing.scalar_one_or_none()
        if row is not None:
            row.setting_value = item.setting_value
        else:
            db.add(
                SystemSetting(
                    setting_key=item.setting_key,
                    setting_value=item.setting_value,
                )
            )

    # ── 3) 将 is_initialized 设为 "true" ──
    init_row = await db.execute(
        select(SystemSetting).where(
            SystemSetting.setting_key == "is_initialized"
        )
    )
    init_setting = init_row.scalar_one_or_none()
    if init_setting is not None:
        init_setting.setting_value = "true"
    else:
        db.add(
            SystemSetting(
                setting_key="is_initialized",
                setting_value="true",
            )
        )

    await db.flush()

    # ── 4) 刷新内存缓存 ──
    all_settings = await db.execute(select(SystemSetting))
    records = all_settings.scalars().all()
    settings_cache.load_from_records(records)

    return {"message": "系统初始化成功", "username": body.username}
