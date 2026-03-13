# backend/app/routers/upload.py
"""
文件上传路由
- POST /upload ：上传电子书文件，全局 SHA-256 去重
"""

import asyncio
import logging
import shutil
import uuid
import aiofiles
from functools import partial
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.security import get_current_user
from app.models.all_models import File, User
from app.utils.file_ops import calculate_file_hash, sanitize_filename

logger = logging.getLogger(__name__)

router = APIRouter(tags=["文件上传"])

# 允许的文件扩展名
_ALLOWED_EXTENSIONS = {".pdf", ".epub"}


class UploadResponse(BaseModel):
    """上传响应"""
    file_id: int
    is_duplicate: bool
    message: str


@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="上传电子书文件",
)
async def upload_file(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    上传电子书（PDF / EPUB）文件。

    业务流程：
    1. 保存到 /data/staging/temp_{uuid}.ext
    2. 计算 SHA-256 哈希
    3. 查询 files 表去重：存在则秒传返回
    4. 重命名并移动到 /data/pool/
    5. 新增 files 记录并返回
    """

    # ── 0. 校验文件类型 ──
    original_filename = file.filename or "unknown"
    suffix = Path(original_filename).suffix.lower()

    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件格式: {suffix}，仅允许 {', '.join(_ALLOWED_EXTENSIONS)}",
        )

    # ── 1. 保存到 staging 区（流式大小校验）──
    staging_dir = Path(settings.STAGING_DIR)
    staging_dir.mkdir(parents=True, exist_ok=True)
    temp_name = f"temp_{uuid.uuid4().hex}{suffix}"
    staging_path = staging_dir / temp_name

    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    bytes_written = 0

    try:
        async with aiofiles.open(staging_path, "wb") as out:
            while True:
                chunk = await file.read(65_536)  # 64 KB
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > max_size:
                    # 超限：立即中断，清理临时文件
                    await out.close()
                    staging_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"文件大小超出限制（最大 {settings.MAX_UPLOAD_SIZE_MB}MB）",
                    )
                await out.write(chunk)
    except HTTPException:
        raise  # 直接透传 413
    except OSError as e:
        staging_path.unlink(missing_ok=True)
        logger.error("文件保存失败: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件保存失败，请重试",
        )
    finally:
        await file.close()

    file_size = bytes_written

    # ── 2. 计算 SHA-256（在线程中执行，避免阻塞事件循环）──
    loop = asyncio.get_running_loop()
    try:
        file_hash = await loop.run_in_executor(
            None, calculate_file_hash, str(staging_path)
        )
    except Exception as e:
        staging_path.unlink(missing_ok=True)
        logger.error("哈希计算失败: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件哈希计算失败",
        )

    # ── 3. 去重：查询 files 表 ──
    result = await db.execute(
        select(File).where(File.original_hash == file_hash)
    )
    existing_file = result.scalar_one_or_none()

    if existing_file is not None:
        # 秒传：删除暂存文件，返回已有记录
        staging_path.unlink(missing_ok=True)
        logger.info(
            "秒传命中: hash=%s → file_id=%d",
            file_hash[:8],
            existing_file.id,
        )
        return UploadResponse(
            file_id=existing_file.id,
            is_duplicate=True,
            message="文件已存在（秒传）",
        )

    # ── 4. 重命名并移动到 pool（在线程中执行）──
    pool_dir = Path(settings.POOL_DIR)
    pool_dir.mkdir(parents=True, exist_ok=True)

    stem = Path(original_filename).stem
    safe_name = sanitize_filename(stem)
    short_id = uuid.uuid4().hex[:6]
    final_name = f"{file_hash[:8]}_{safe_name}_{short_id}{suffix}"
    final_path = pool_dir / final_name

    try:
        await loop.run_in_executor(
            None, partial(shutil.move, str(staging_path), str(final_path))
        )
    except OSError as e:
        staging_path.unlink(missing_ok=True)
        logger.error("文件移动到 pool 失败: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件入库失败",
        )

    # ── 5. 原子写入 files 表 (INSERT ... ON CONFLICT DO NOTHING) ──
    insert_stmt = (
        sqlite_insert(File)
        .values(
            original_hash=file_hash,
            file_path=final_name,
            format=suffix.lstrip("."),
            size_bytes=file_size,
            original_filename=original_filename,
        )
        .on_conflict_do_nothing(index_elements=["original_hash"])
    )
    result_insert = await db.execute(insert_stmt)
    await db.flush()

    # 查询最终入库的记录
    result_select = await db.execute(
        select(File).where(File.original_hash == file_hash)
    )
    final_file = result_select.scalar_one()

    # 判断是否为本次请求插入：对比 DB 中记录的 file_path 与本次的 final_name
    # 如果一致，说明本次请求是"赢家"；否则是并发竞争的"输家"
    is_dup = final_file.file_path != final_name

    if is_dup:
        # 并发秒传：清理本次请求多余的 pool 文件
        final_path.unlink(missing_ok=True)
        logger.info(
            "并发秒传命中 (ON CONFLICT): hash=%s → file_id=%d",
            file_hash[:8],
            final_file.id,
        )
        return UploadResponse(
            file_id=final_file.id,
            is_duplicate=True,
            message="文件已存在（秒传）",
        )

    logger.info(
        "文件入库成功: file_id=%d, hash=%s, path=%s",
        final_file.id,
        file_hash[:8],
        final_name,
    )

    return UploadResponse(
        file_id=final_file.id,
        is_duplicate=False,
        message="文件上传成功",
    )
