# backend/app/routers/settings.py
"""
设置中心路由
- GET  /settings ：获取所有系统配置（敏感字段自动掩码）
- PUT  /settings ：批量更新配置并热刷新内存缓存
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user
from app.core.settings_cache import settings_cache
from app.models.all_models import SystemSetting, User
from app.schemas.api_schemas import (
    MessageResponse,
    SystemSettingBatchUpdate,
    SystemSettingOut,
)

router = APIRouter(tags=["设置中心"])

# ── 敏感字段列表：GET 返回时自动掩码，PUT 收到掩码时跳过 ──
SENSITIVE_KEYS = {"douban_cookie"}
MASK_VALUE = "******"


@router.get(
    "/settings",
    response_model=list[SystemSettingOut],
    summary="获取所有配置",
)
async def get_all_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    返回 system_settings 表中的所有配置项（需认证）。
    敏感字段（如 douban_cookie）的值会被掩码替换。
    """
    result = await db.execute(
        select(SystemSetting).order_by(SystemSetting.setting_key)
    )
    rows = result.scalars().all()

    # 对敏感字段做掩码处理（不修改 DB 对象，构造新的输出）
    out = []
    for row in rows:
        item = SystemSettingOut.model_validate(row)
        if row.setting_key in SENSITIVE_KEYS and row.setting_value:
            item.setting_value = MASK_VALUE
        out.append(item)
    return out


@router.put(
    "/settings",
    response_model=MessageResponse,
    summary="批量更新配置",
)
async def update_settings(
    payload: SystemSettingBatchUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    批量更新系统配置：
    - key 已存在 → 更新 value
    - key 不存在 → 新增记录
    - 敏感字段收到掩码值时自动跳过（防止覆盖真实值）
    - 完成后立即刷新 SettingsCache 内存缓存（热更新）
    """
    updated_count = 0
    for item in payload.settings:
        # 跳过掩码占位符，防止前端回传 "******" 覆盖真实 cookie
        if item.setting_key in SENSITIVE_KEYS and item.setting_value == MASK_VALUE:
            continue

        result = await db.execute(
            select(SystemSetting).where(
                SystemSetting.setting_key == item.setting_key
            )
        )
        existing = result.scalar_one_or_none()

        if existing is not None:
            existing.setting_value = item.setting_value
        else:
            db.add(
                SystemSetting(
                    setting_key=item.setting_key,
                    setting_value=item.setting_value,
                )
            )
        updated_count += 1

    # 先 flush 确保数据写入，再重新加载缓存
    await db.flush()

    # ── 热更新：重新从数据库加载全部设置到内存缓存 ──
    all_result = await db.execute(select(SystemSetting))
    all_records = all_result.scalars().all()
    settings_cache.load_from_records(all_records)

    return MessageResponse(
        message=f"已更新 {updated_count} 项配置，缓存已刷新"
    )
