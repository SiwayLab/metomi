# backend/app/routers/progress.py
"""
阅读进度路由
- POST /progress                    ：提交/更新阅读进度（UPSERT）
- GET  /progress/{book_id}/{file_id} ：获取当前用户某书某文件的最新进度
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.all_models import ReadingProgress, User
from app.schemas.api_schemas import MessageResponse
from app.schemas.progress import ReadingProgressCreate, ReadingProgressOut

logger = logging.getLogger(__name__)

router = APIRouter(tags=["阅读进度"])


@router.post(
    "/progress",
    response_model=ReadingProgressOut,
    summary="提交阅读进度",
)
async def upsert_progress(
    payload: ReadingProgressCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    提交或更新阅读进度（UPSERT 逻辑）。

    根据 (user_id, book_id, file_id) 唯一约束：
    - 已存在 → 更新 location、progress_percent、device_name、last_read_at
    - 不存在 → 新建记录

    阅读器每 10 秒或翻页时静默调用此端点。
    """
    # ── 校验 book_id ↔ file_id 关联关系 ──
    from app.models.all_models import book_file_link, Book, File
    book_exists = await db.execute(select(Book).where(Book.id == payload.book_id))
    if book_exists.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"书籍 {payload.book_id} 不存在")

    link_check = await db.execute(
        select(book_file_link).where(
            book_file_link.c.book_id == payload.book_id,
            book_file_link.c.file_id == payload.file_id,
        )
    )
    if link_check.first() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"文件 {payload.file_id} 不属于书籍 {payload.book_id}",
        )

    # 查询是否已有进度记录
    result = await db.execute(
        select(ReadingProgress).where(
            ReadingProgress.user_id == current_user.id,
            ReadingProgress.book_id == payload.book_id,
            ReadingProgress.file_id == payload.file_id,
        )
    )
    progress = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if progress is not None:
        # ── 更新 ──
        progress.location = payload.location
        progress.progress_percent = payload.progress_percent
        progress.device_name = payload.device_name
        progress.last_read_at = now
    else:
        # ── 新建 ──
        progress = ReadingProgress(
            user_id=current_user.id,
            book_id=payload.book_id,
            file_id=payload.file_id,
            location=payload.location,
            progress_percent=payload.progress_percent,
            device_name=payload.device_name,
            last_read_at=now,
        )
        db.add(progress)

    await db.commit()
    await db.refresh(progress)

    logger.info(
        "进度同步: user=%d book=%d file=%d loc=%s",
        current_user.id,
        payload.book_id,
        payload.file_id,
        payload.location,
    )
    return progress


@router.get(
    "/progress/{book_id}/{file_id}",
    response_model=ReadingProgressOut | None,
    summary="获取阅读进度",
)
async def get_progress(
    book_id: int,
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取当前用户在指定图书/文件上的最新阅读进度。
    如果没有进度记录，返回 null。
    """
    result = await db.execute(
        select(ReadingProgress).where(
            ReadingProgress.user_id == current_user.id,
            ReadingProgress.book_id == book_id,
            ReadingProgress.file_id == file_id,
        )
    )
    progress = result.scalar_one_or_none()
    return progress
