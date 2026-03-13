# backend/app/schemas/progress.py
"""
Metomi 阅读进度 Pydantic v2 模型
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ReadingProgressCreate(BaseModel):
    """提交 / 更新阅读进度"""
    book_id: int
    file_id: int
    location: str = Field(
        ...,
        description="当前位置：PDF 页码（如 '42'）或 EPUB CFI 定位符",
    )
    progress_percent: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="阅读进度百分比 0-100",
    )
    device_name: Optional[str] = Field(
        None,
        max_length=128,
        description="设备名称（用于多端同步显示）",
    )


class ReadingProgressOut(BaseModel):
    """阅读进度响应"""
    id: int
    user_id: int
    book_id: int
    file_id: int
    location: str
    progress_percent: Optional[float] = None
    device_name: Optional[str] = None
    last_read_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
