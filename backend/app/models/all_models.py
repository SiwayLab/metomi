# backend/app/models/all_models.py
"""
Metomi 全部 SQLAlchemy 2.0 数据模型
采用 3NF 设计，多对多关联，文件池半黑箱存储，数据零冗余。

包含模型/表：
 1. User               — 用户
 2. SystemSetting       — 全局配置（k-v）
 3. Book               — 核心图书
 4. Author             — 作者
 5. Publisher           — 出版社
 6. File               — 文件池
 7. book_author_link   — 图书 ↔ 作者 (M2M)
 8. book_file_link     — 图书 ↔ 文件 (M2M)
 9. ReadingProgress    — 阅读进度（多端同步）
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


# ═══════════════════════════════════════════════════════════
#  关联表（纯多对多，无额外字段，使用 Table 构造）
# ═══════════════════════════════════════════════════════════

book_author_link = Table(
    "book_author_link",
    Base.metadata,
    Column(
        "book_id",
        Integer,
        ForeignKey("books.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "author_id",
        Integer,
        ForeignKey("authors.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


book_file_link = Table(
    "book_file_link",
    Base.metadata,
    Column(
        "book_id",
        Integer,
        ForeignKey("books.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "file_id",
        Integer,
        ForeignKey("files.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


# ═══════════════════════════════════════════════════════════
#  用户模型
# ═══════════════════════════════════════════════════════════

class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    username: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(
        String(256), nullable=False
    )
    language: Mapped[str] = mapped_column(
        String(16), nullable=False, default="zh-CN",
        server_default="zh-CN",
        comment="用户界面语言偏好",
    )
    token_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="JWT 版本号，修改密码时 +1 使旧 Token 失效",
    )

    # ── 关联 ──
    reading_progresses: Mapped[list["ReadingProgress"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r}>"


# ═══════════════════════════════════════════════════════════
#  系统设置（全局配置表）
# ═══════════════════════════════════════════════════════════

class SystemSetting(TimestampMixin, Base):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    setting_key: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    setting_value: Mapped[str] = mapped_column(
        Text, nullable=False, default=""
    )

    def __repr__(self) -> str:
        return f"<SystemSetting {self.setting_key!r}={self.setting_value!r}>"


# ═══════════════════════════════════════════════════════════
#  核心图书模型
# ═══════════════════════════════════════════════════════════

class Book(TimestampMixin, Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    title: Mapped[str] = mapped_column(
        String(512), nullable=False, index=True
    )

    isbn: Mapped[Optional[str]] = mapped_column(
        String(20), unique=True, nullable=True, index=True
    )
    douban_id: Mapped[Optional[str]] = mapped_column(
        String(32), unique=True, nullable=True, index=True
    )
    custom_code: Mapped[Optional[str]] = mapped_column(
        String(32), unique=True, nullable=True, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    publisher_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("publishers.id", ondelete="SET NULL"),
        nullable=True,
    )
    pub_date: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True
    )
    language: Mapped[Optional[str]] = mapped_column(
        String(16), nullable=True
    )
    cover_path: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True
    )
    book_type: Mapped[str] = mapped_column(
        String(128), default="ebook", nullable=False,
        comment="书籍类型：ebook, physical 等，逗号分隔支持多选"
    )
    physical_location: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True,
        comment="纸质书物理位置"
    )
    rating: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    read_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="unread",
        comment="阅读状态: unread, reading, read, want_to_read, skimmed, shelved"
    )

    # ── 关联 ──
    publisher: Mapped[Optional["Publisher"]] = relationship(
        back_populates="books"
    )
    authors: Mapped[list["Author"]] = relationship(
        secondary=book_author_link, back_populates="books"
    )

    files: Mapped[list["File"]] = relationship(
        secondary=book_file_link, back_populates="books"
    )
    reading_progresses: Mapped[list["ReadingProgress"]] = relationship(
        back_populates="book", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Book id={self.id} title={self.title!r}>"


# ═══════════════════════════════════════════════════════════
#  规范化实体表：作者 / 出版社 / 标签
# ═══════════════════════════════════════════════════════════

class Author(TimestampMixin, Base):
    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(
        String(256), unique=True, nullable=False, index=True
    )

    # ── 关联 ──
    books: Mapped[list["Book"]] = relationship(
        secondary=book_author_link, back_populates="authors"
    )

    def __repr__(self) -> str:
        return f"<Author id={self.id} name={self.name!r}>"


class Publisher(TimestampMixin, Base):
    __tablename__ = "publishers"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(
        String(256), unique=True, nullable=False, index=True
    )

    # ── 关联 ──
    books: Mapped[list["Book"]] = relationship(
        back_populates="publisher"
    )

    def __repr__(self) -> str:
        return f"<Publisher id={self.id} name={self.name!r}>"





# ═══════════════════════════════════════════════════════════
#  文件池模型
# ═══════════════════════════════════════════════════════════

class File(TimestampMixin, Base):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    original_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True,
        comment="SHA-256 全文哈希，用于全局去重",
    )
    file_path: Mapped[str] = mapped_column(
        String(512), nullable=False,
        comment="pool/ 下的相对路径",
    )
    format: Mapped[str] = mapped_column(
        String(16), nullable=False,
        comment="文件格式：pdf / epub",
    )
    size_bytes: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="文件大小（字节）",
    )
    original_filename: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True,
        comment="原始上传文件名",
    )

    # ── 关联 ──
    books: Mapped[list["Book"]] = relationship(
        secondary=book_file_link, back_populates="files"
    )
    reading_progresses: Mapped[list["ReadingProgress"]] = relationship(
        back_populates="file", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<File id={self.id} format={self.format!r} hash={self.original_hash[:8]}>"


# ═══════════════════════════════════════════════════════════
#  阅读进度模型（多端同步）
# ═══════════════════════════════════════════════════════════

class ReadingProgress(TimestampMixin, Base):
    __tablename__ = "reading_progress"

    __table_args__ = (
        UniqueConstraint(
            "user_id", "book_id", "file_id",
            name="uq_user_book_file",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    book_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
    )
    location: Mapped[str] = mapped_column(
        String(256), nullable=False, default="",
        comment="PDF 页码 / EPUB CFI 定位符",
    )
    progress_percent: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True,
        comment="阅读进度百分比 0-100",
    )
    device_name: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True,
        comment="最后阅读设备名称",
    )
    last_read_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="最后阅读时间",
    )

    # ── 关联 ──
    user: Mapped["User"] = relationship(
        back_populates="reading_progresses"
    )
    book: Mapped["Book"] = relationship(
        back_populates="reading_progresses"
    )
    file: Mapped["File"] = relationship(
        back_populates="reading_progresses"
    )

    def __repr__(self) -> str:
        return (
            f"<ReadingProgress user={self.user_id} "
            f"book={self.book_id} loc={self.location!r}>"
        )


# ═══════════════════════════════════════════════════════════
#  刮削任务（持久化到数据库，支持多实例部署）
# ═══════════════════════════════════════════════════════════

class ScrapeTask(TimestampMixin, Base):
    """
    刮削任务持久化模型。
    替代原先的进程内存 TTLDict，支持多实例部署场景。
    """
    __tablename__ = "scrape_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True,
        comment="客户端唯一任务标识 (UUID hex)",
    )
    query: Mapped[str] = mapped_column(
        String(512), nullable=False,
        comment="刮削查询 (ISBN 或书名)",
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="processing",
        comment="processing / completed / failed",
    )
    result_json: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="JSON 序列化的刮削结果",
    )
    error: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="失败时的错误信息",
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False,
        comment="提交任务的用户 ID",
    )

    def __repr__(self) -> str:
        return f"<ScrapeTask {self.task_id} status={self.status}>"

