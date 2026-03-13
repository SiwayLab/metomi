# backend/app/models/base.py
"""
SQLAlchemy 2.0 声明式基类与通用 Mixin
所有业务模型继承 Base，并通过 TimestampMixin 自动获得 created_at / updated_at。
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """声明式基类 — 所有 ORM 模型的根"""
    pass


class TimestampMixin:
    """
    通用时间戳 Mixin
    - created_at：记录创建时间（数据库侧默认 CURRENT_TIMESTAMP）
    - updated_at：记录更新时间（ORM 侧 onupdate 自动刷新）
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
    )
