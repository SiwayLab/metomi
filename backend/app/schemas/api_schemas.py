# backend/app/schemas/api_schemas.py
"""
Metomi API Pydantic v2 入参 / 出参模型
当前涵盖：鉴权、系统设置、通用响应
"""

from datetime import datetime

from typing import Optional

import re

from pydantic import BaseModel, Field, field_validator


# ═══════════════════════════════════════════════════════
#  密码强度校验（共享工具函数，供多处复用）
# ═══════════════════════════════════════════════════════

def validate_password_strength(password: str) -> str:
    """
    密码强度校验：至少包含一个大写字母、一个小写字母和一个数字。
    直接返回原值或抛出 ValueError（供 Pydantic field_validator 使用）。
    """
    if not re.search(r"[A-Z]", password):
        raise ValueError("密码必须包含至少一个大写字母")
    if not re.search(r"[a-z]", password):
        raise ValueError("密码必须包含至少一个小写字母")
    if not re.search(r"\d", password):
        raise ValueError("密码必须包含至少一个数字")
    return password


# ═══════════════════════════════════════════════════════
#  鉴权相关
# ═══════════════════════════════════════════════════════

class Token(BaseModel):
    """登录成功响应"""
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    """用户信息（安全输出，不含密码哈希）"""
    id: int
    username: str
    language: str = "zh-CN"
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """用户信息更新请求体"""
    language: Optional[str] = Field(None, max_length=16)


class UserPasswordUpdate(BaseModel):
    """用户修改密码请求体"""
    old_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=6, max_length=128)

    @field_validator("new_password")
    @classmethod
    def check_strength(cls, v: str) -> str:
        return validate_password_strength(v)


# ═══════════════════════════════════════════════════════
#  系统设置
# ═══════════════════════════════════════════════════════

class SystemSettingOut(BaseModel):
    """单条设置响应"""
    id: int
    setting_key: str
    setting_value: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SystemSettingUpdate(BaseModel):
    """单条设置更新"""
    setting_key: str = Field(..., min_length=1, max_length=128)
    setting_value: str


class SystemSettingBatchUpdate(BaseModel):
    """批量设置更新请求体"""
    settings: list[SystemSettingUpdate]


# ═══════════════════════════════════════════════════════
#  通用响应
# ═══════════════════════════════════════════════════════

class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str
