# backend/app/models/__init__.py
"""
模型包 — 导出所有 ORM 模型与关联表，方便外部统一导入。
"""

from app.models.base import Base, TimestampMixin
from app.models.all_models import (
    Author,
    Book,
    File,
    Publisher,
    ReadingProgress,
    SystemSetting,
    User,
    book_author_link,
    book_file_link,
)

__all__ = [
    "Base",
    "TimestampMixin",
    "Author",
    "Book",
    "File",
    "Publisher",
    "ReadingProgress",
    "SystemSetting",
    "User",
    "book_author_link",
    "book_file_link",
]
