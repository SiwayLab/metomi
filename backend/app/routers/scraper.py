# backend/app/routers/scraper.py
"""
刮削路由
- POST /scrape        ：提交刮削任务，立即返回 task_id（不阻塞）
- GET  /scrape/status ：短轮询获取刮削结果

任务持久化到数据库（ScrapeTask 表），支持多实例部署。
"""

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.all_models import User, ScrapeTask
from app.services.scraper import scrape_by_priority

logger = logging.getLogger(__name__)

router = APIRouter(tags=["刮削"])

# 僵尸任务过期时间
_TASK_TTL = timedelta(hours=1)


# ═══════════════════════════════════════════════════════
#  请求 / 响应模型
# ═══════════════════════════════════════════════════════

class ScrapeRequest(BaseModel):
    """刮削请求"""
    query: str = Field(..., min_length=1, description="ISBN 或书名")


class ScrapeTaskResponse(BaseModel):
    """任务提交响应"""
    task_id: str
    status: str


class ScrapeStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    status: str  # processing / completed / failed
    result: dict | None = None
    error: str | None = None


# ═══════════════════════════════════════════════════════
#  后台刮削任务（写入数据库）
# ═══════════════════════════════════════════════════════

async def _run_scrape_task(task_id: str, query: str) -> None:
    """在后台执行刮削并将结果写入数据库"""
    from app.core.db import async_session_factory

    try:
        result = await scrape_by_priority(query)

        async with async_session_factory() as session:
            row = await session.execute(
                select(ScrapeTask).where(ScrapeTask.task_id == task_id)
            )
            task = row.scalar_one_or_none()
            if task is None:
                return

            if result is not None and result.get("title"):
                task.status = "completed"
                task.result_json = json.dumps(result, ensure_ascii=False)
                task.error = None
            else:
                task.status = "failed"
                task.result_json = None
                task.error = f"所有刮削源均未找到: {query}"
            await session.commit()
    except Exception as e:
        logger.error("刮削任务失败 [%s]: %s", task_id, e)
        try:
            async with async_session_factory() as session:
                row = await session.execute(
                    select(ScrapeTask).where(ScrapeTask.task_id == task_id)
                )
                task = row.scalar_one_or_none()
                if task:
                    task.status = "failed"
                    task.error = str(e)
                    await session.commit()
        except Exception:
            logger.error("无法更新失败状态 [%s]", task_id)


# ═══════════════════════════════════════════════════════
#  路由
# ═══════════════════════════════════════════════════════

@router.post("/scrape", response_model=ScrapeTaskResponse, summary="提交刮削任务")
async def submit_scrape(
    payload: ScrapeRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    提交刮削任务，立即返回 task_id。
    前端通过 GET /scrape/status/{task_id} 轮询结果。
    """
    # 先清理过期任务
    cutoff = datetime.now(timezone.utc) - _TASK_TTL
    await db.execute(
        delete(ScrapeTask).where(ScrapeTask.created_at < cutoff)
    )

    task_id = uuid.uuid4().hex
    new_task = ScrapeTask(
        task_id=task_id,
        query=payload.query,
        status="processing",
        user_id=current_user.id,
    )
    db.add(new_task)
    await db.commit()

    background_tasks.add_task(_run_scrape_task, task_id, payload.query)

    logger.info("刮削任务已提交: task_id=%s, query=%s", task_id, payload.query)
    return ScrapeTaskResponse(task_id=task_id, status="processing")


@router.get(
    "/scrape/status/{task_id}",
    response_model=ScrapeStatusResponse,
    summary="查询刮削任务状态",
)
async def get_scrape_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    前端短轮询端点。
    返回 processing / completed / failed 状态及结果。
    """
    result = await db.execute(
        select(ScrapeTask).where(
            ScrapeTask.task_id == task_id,
            ScrapeTask.user_id == current_user.id
        )
    )
    task = result.scalar_one_or_none()

    if task is None:
        return ScrapeStatusResponse(
            task_id=task_id,
            status="not_found",
            error="任务不存在或已过期",
        )

    parsed_result = None
    if task.result_json:
        try:
            parsed_result = json.loads(task.result_json)
        except json.JSONDecodeError:
            parsed_result = None

    return ScrapeStatusResponse(
        task_id=task_id,
        status=task.status,
        result=parsed_result,
        error=task.error,
    )


from app.services.scraper import search_candidates, fetch_candidate_detail
import httpx
from fastapi.responses import StreamingResponse

class CandidateSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)

class CandidateFetchRequest(BaseModel):
    source: str
    id: str

@router.post(
    "/scrape/search/candidates",
    summary="搜索返回多个刮削候选",
)
async def api_search_candidates(
    payload: CandidateSearchRequest,
    current_user: User = Depends(get_current_user),
):
    """
    快速搜索多个对应书籍的候选结果。
    """
    candidates = await search_candidates(payload.query)
    return {"candidates": candidates}

@router.post(
    "/scrape/fetch/candidate",
    summary="获取单个候选的完整详情",
)
async def api_fetch_candidate(
    payload: CandidateFetchRequest,
    current_user: User = Depends(get_current_user),
):
    """
    根据给定的来源和候选 ID，爬取完整的书籍元数据。
    """
    res = await fetch_candidate_detail(payload.source, payload.id)
    return {"result": res}


# ── proxy-image 安全常量 ──
_PROXY_IMAGE_ALLOWED_DOMAINS = {
    "douban.com",
    "doubanio.com",
    "openlibrary.org",
    "covers.openlibrary.org",
}
_PROXY_IMAGE_MAX_BYTES = 10 * 1024 * 1024  # 10 MB


def _is_allowed_image_domain(url: str) -> bool:
    """检查 URL 域名是否在白名单内"""
    try:
        from urllib.parse import urlparse
        hostname = urlparse(url).hostname or ""
        return any(
            hostname == domain or hostname.endswith("." + domain)
            for domain in _PROXY_IMAGE_ALLOWED_DOMAINS
        )
    except Exception:
        return False


@router.get(
    "/scrape/proxy-image",
    summary="代理请求外部图片，绕过防盗链",
)
async def proxy_image(
    url: str,
    current_user: User = Depends(get_current_user),
):
    """
    接收外部图片 URL，后端请求后流式返回给前端。
    伪造 User-Agent 和 Referer 绕过豆瓣等图床防盗链（403 Forbidden）。

    安全措施：
    - 需要登录鉴权
    - 仅允许白名单域名（豆瓣、OpenLibrary 等图床）
    - 响应体大小限制 10 MB
    """
    from fastapi.responses import JSONResponse

    if not url.startswith("http"):
        return JSONResponse({"error": "Invalid URL"}, status_code=400)

    if not _is_allowed_image_domain(url):
        return JSONResponse({"error": "Domain not allowed"}, status_code=403)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://book.douban.com/",
    }

    async def _stream_image():
        total = 0
        async with httpx.AsyncClient(timeout=15.0) as client:
            async with client.stream("GET", url, headers=headers, follow_redirects=True) as response:
                if response.status_code == 200:
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > _PROXY_IMAGE_MAX_BYTES:
                            break
                        yield chunk

    return StreamingResponse(_stream_image(), media_type="image/jpeg")
