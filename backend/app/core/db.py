# backend/app/core/db.py
"""
Metomi 异步数据库引擎与会话管理
- 使用 aiosqlite 异步驱动
- 每次连接强制执行 PRAGMA journal_mode=WAL / synchronous=NORMAL / cache_size=-64000
- 提供 FastAPI 依赖注入用的 get_db 生成器
"""

from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# ═══════════════════════════════════════════════════════
# 异步引擎
# ═══════════════════════════════════════════════════════
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False, "timeout": 15},
    # 注意：pool_size / max_overflow / pool_pre_ping 仅对 PostgreSQL 等连接池数据库有意义
    # SQLite + aiosqlite 使用 StaticPool，设置这些参数无效
)


# ═══════════════════════════════════════════════════════
# SQLite PRAGMA — 在 *每次* 原生连接建立时执行
# ═══════════════════════════════════════════════════════
@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """强制开启 WAL 模式并调优 SQLite 参数"""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=-64000")
    cursor.close()


# ═══════════════════════════════════════════════════════
# 异步会话工厂
# ═══════════════════════════════════════════════════════
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入：提供异步数据库会话，自动提交/回滚"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
