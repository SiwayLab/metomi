# backend/migrations/env.py
"""
Alembic 异步迁移环境配置
- 从 app.core.config 读取 DATABASE_URL（与应用共享同一配置源）
- 导入所有模型，确保 autogenerate 能检测全部表
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ── 导入 Base 与全部模型（autogenerate 必须）──
from app.models.base import Base
from app.models.all_models import (  # noqa: F401 — 仅为注册到 metadata
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

# ── 从应用配置获取数据库 URL ──
from app.core.config import settings

# Alembic Config 对象
config = context.config

# 用应用配置覆盖 alembic.ini 中的占位 URL
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# 配置 Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 设置 autogenerate 的目标 metadata
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式迁移（仅生成 SQL，不连接数据库）"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,  # SQLite 需要 batch 模式以支持 ALTER TABLE
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """异步在线模式迁移"""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """在线模式迁移入口"""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
