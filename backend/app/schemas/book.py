# backend/app/schemas/book.py
"""
Metomi 图书相关 Pydantic v2 入参 / 出参模型
BookOut 嵌套包含 authors, tags, publisher, files 关联信息
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator
import re

# 合法的阅读状态枚举
ReadStatusType = Literal[
    "unread", "want_to_read", "reading", "read", "shelved", "skimmed"
]


# ═══════════════════════════════════════════════════════
#  嵌套输出模型（用于 BookOut 内部）
# ═══════════════════════════════════════════════════════

class AuthorOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class PublisherOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}



class FileOut(BaseModel):
    id: int
    original_hash: str
    file_path: str
    format: str
    size_bytes: int
    original_filename: Optional[str] = None

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════
#  图书输出模型
# ═══════════════════════════════════════════════════════

class BookOut(BaseModel):
    """完整图书信息（含所有关联实体）"""
    id: int
    title: str
    isbn: Optional[str] = None
    douban_id: Optional[str] = None
    custom_code: Optional[str] = None
    description: Optional[str] = None
    pub_date: Optional[str] = None
    language: Optional[str] = None
    cover_path: Optional[str] = None
    book_type: str = "ebook"
    physical_location: Optional[str] = None
    rating: Optional[float] = None
    read_status: str = "unread"
    created_at: datetime
    updated_at: datetime

    # 嵌套关联
    publisher: Optional[PublisherOut] = None
    authors: list[AuthorOut] = []
    files: list[FileOut] = []

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════
#  图书创建 / 更新模型
# ═══════════════════════════════════════════════════════

class BookCreate(BaseModel):
    """创建图书请求体"""
    title: str = Field(..., min_length=1, max_length=512)
    isbn: Optional[str] = None
    douban_id: Optional[str] = None
    custom_code: Optional[str] = None
    description: Optional[str] = None
    pub_date: Optional[str] = None
    language: Optional[str] = None
    cover_path: Optional[str] = None
    book_type: str = "ebook"
    physical_location: Optional[str] = None
    rating: Optional[float] = Field(None, ge=0, le=10, description="评分 0-10")
    read_status: ReadStatusType = "unread"

    # 关联数据（名称列表，后端自动 UPSERT）
    author_names: list[str] = []
    publisher_name: Optional[str] = None

    # 关联文件
    file_id: Optional[int] = None

    @field_validator("cover_path")
    @classmethod
    def validate_cover_path(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return v
        # 只允许 http(s) 绝对路径或 /covers/ 相对路径，防御 javascript: 等 XSS 攻击
        if not re.match(r"^(https?://|/covers/)", v, re.IGNORECASE):
            raise ValueError("cover_path 必须是以 http://, https:// 或 /covers/ 开头的安全路径")
        return v


class BookUpdate(BaseModel):
    """更新图书请求体（所有字段可选）"""
    title: Optional[str] = Field(None, min_length=1, max_length=512)
    isbn: Optional[str] = None
    douban_id: Optional[str] = None
    custom_code: Optional[str] = None
    description: Optional[str] = None
    pub_date: Optional[str] = None
    language: Optional[str] = None
    cover_path: Optional[str] = None
    book_type: Optional[str] = None
    physical_location: Optional[str] = None
    rating: Optional[float] = Field(None, ge=0, le=10, description="评分 0-10")
    read_status: Optional[ReadStatusType] = None

    # 关联实体字段
    author_names: Optional[list[str]] = None
    publisher_name: Optional[str] = None
    file_id: Optional[int] = None

    @field_validator("cover_path")
    @classmethod
    def validate_cover_path(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return v
        if not re.match(r"^(https?://|/covers/)", v, re.IGNORECASE):
            raise ValueError("cover_path 必须是以 http://, https:// 或 /covers/ 开头的安全路径")
        return v


# ═══════════════════════════════════════════════════════
#  分页响应
# ═══════════════════════════════════════════════════════

class PaginatedBooks(BaseModel):
    """分页图书列表"""
    items: list[BookOut]
    total: int
    page: int
    page_size: int
