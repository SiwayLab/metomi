# backend/app/routers/stream.py
"""
流式阅读路由
- GET /stream/{file_id} ：支持 HTTP Range Requests (206 Partial Content)
- 仅支持 Bearer Token 鉴权（Authorization Header）
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.security import get_current_user
from app.models.all_models import File, User
from app.utils.streaming import range_requests_response

logger = logging.getLogger(__name__)

router = APIRouter(tags=["流式阅读"])

# ── MIME 类型映射 ──
_CONTENT_TYPES = {
    "pdf": "application/pdf",
    "epub": "application/epub+zip",
}


@router.get(
    "/stream/{file_id}",
    summary="流式获取电子书文件",
    responses={
        200: {"description": "完整文件"},
        206: {"description": "部分内容（Range 请求）"},
        401: {"description": "未认证"},
        404: {"description": "文件不存在"},
    },
)
async def stream_file(
    file_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    download: str = None,
):
    """
    流式返回电子书文件内容。

    完整支持 HTTP Range Requests（206 Partial Content），
    配合 pdf.js / epub.js 实现按页/按需加载。

    鉴权方式：Authorization: Bearer <token>
    """
    # 查询文件记录
    result = await db.execute(
        select(File).where(File.id == file_id)
    )
    file_record = result.scalar_one_or_none()
    if file_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在",
        )

    # 构建绝对路径
    file_path = Path(settings.POOL_DIR) / file_record.file_path
    if not file_path.exists():
        logger.error("文件不在磁盘上: %s", file_path)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件在磁盘上不存在",
        )

    # 确定 Content-Type
    content_type = _CONTENT_TYPES.get(
        file_record.format.lower(),
        "application/octet-stream",
    )

    return range_requests_response(request, str(file_path), content_type, download_name=download)
