# backend/app/main.py
"""
Metomi FastAPI 主入口
- CORS 中间件（从配置读取允许的源）
- slowapi 全局速率限制
- Lifespan：启动时初始化配置缓存
- 路由注册：auth、settings、upload、books、scraper、stream、progress
"""

import logging
import traceback
import asyncio

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import ResponseValidationError
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import select
from starlette.staticfiles import StaticFiles

from app.core.config import settings
from app.core.db import async_session_factory
from app.core.settings_cache import SettingsCache, settings_cache
from app.models.all_models import SystemSetting
from app.routers.auth import router as auth_router
from app.routers.settings import router as settings_router
from app.routers.upload import router as upload_router
from app.routers.books import router as books_router
from app.routers.scraper import router as scraper_router
from app.routers.stream import router as stream_router
from app.routers.progress import router as progress_router
from app.routers.init import router as init_router

# ── 统一日志配置 ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════
#  速率限制器（从共享模块导入，避免循环依赖）
# ═══════════════════════════════════════════════════════

from app.core.limiter import limiter


# ═══════════════════════════════════════════════════════
#  Lifespan（启动 / 关闭事件）
# ═══════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""

    # ── 0) 自动执行数据库迁移 (初始化表结构) ──
    try:
        import subprocess
        logger.info("Checking and applying database migrations via subprocess...")
        # 强隔离：防止 alembic api 破坏事件循环或 logging 配置
        subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=str(settings.BASE_DIR),
            check=True,
            capture_output=True,
            text=True
        )
        logger.info("Database migrations applied successfully.")
    except subprocess.CalledProcessError as e:
        logger.error("Failed to apply database migrations: %s\n%s", e, e.stderr)
    except Exception as e:
        logger.error("Failed to apply database migrations automatically: %s", getattr(e, "message", str(e)))
        logger.error(traceback.format_exc())
        # 继续启动，由后续检查或日志暴露问题

    async with async_session_factory() as session:
        # ── 1) 向数据库写入默认设置（不存在时才插入）──
        for key, value in SettingsCache.DEFAULTS.items():
            exists = await session.execute(
                select(SystemSetting).where(
                    SystemSetting.setting_key == key
                )
            )
            if exists.scalar_one_or_none() is None:
                session.add(
                    SystemSetting(
                        setting_key=key,
                        setting_value=str(value),
                    )
                )
        await session.commit()

        # ── 3) 加载所有设置到内存缓存 ──
        all_settings = await session.execute(select(SystemSetting))
        records = all_settings.scalars().all()
        settings_cache.load_from_records(records)
        logger.info("SettingsCache loaded %d settings", len(records))

    yield

    logger.info("Metomi shutting down...")


# ═══════════════════════════════════════════════════════
#  FastAPI 应用实例
# ═══════════════════════════════════════════════════════

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    lifespan=lifespan,
)

# ── slowapi 速率限制 ──
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ── 全局异常兜底 ──
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """捕获所有未处理的异常，返回统一 500 JSON，避免泄露堆栈信息"""
    logger.error("未处理的异常: %s %s -> %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误，请稍后重试"},
    )

# ── ResponseValidation 调试用 ──
@app.exception_handler(ResponseValidationError)
async def response_validation_handler(request: Request, exc: ResponseValidationError):
    try:
        errors = exc.errors()
        logger.error("ResponseValidationError errors: %s", errors)
        return JSONResponse(
            status_code=500,
            content={"detail": "Response validation error", "errors": str(errors)},
        )
    except Exception:
        logger.error("ResponseValidationError (could not extract details): %s", traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"detail": "Response validation error (details unavailable)"},
        )

# ── CORS 中间件 ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 路由注册 ──
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(settings_router, prefix=settings.API_V1_PREFIX)
app.include_router(upload_router, prefix=settings.API_V1_PREFIX)
app.include_router(books_router, prefix=settings.API_V1_PREFIX)
app.include_router(scraper_router, prefix=settings.API_V1_PREFIX)
app.include_router(stream_router, prefix=settings.API_V1_PREFIX)
app.include_router(progress_router, prefix=settings.API_V1_PREFIX)
app.include_router(init_router, prefix=settings.API_V1_PREFIX)

# ── 静态文件：封面图片 ──
settings.COVERS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/covers", StaticFiles(directory=str(settings.COVERS_DIR)), name="covers")

# ── SPA catch-all：生产环境前端静态文件 ──
_FRONTEND_DIST = settings.DATA_DIR.parent / "frontend" / "dist"
_INDEX_HTML = _FRONTEND_DIST / "index.html"

if _INDEX_HTML.exists():
    # 挂载前端打包产物的静态资源（JS / CSS / 图片等）
    app.mount("/assets", StaticFiles(directory=str(_FRONTEND_DIST / "assets")), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_catch_all(full_path: str):
        """SPA 兜底路由：非 API 请求一律返回 index.html"""
        # 先检查 dist 目录下是否有对应的静态文件（如 favicon.ico）
        if full_path:
            file_path = (_FRONTEND_DIST / full_path).resolve()
            # 防御路径穿越：确保解析后的路径仍在 dist 目录内
            if file_path.is_file() and file_path.is_relative_to(_FRONTEND_DIST.resolve()):
                return FileResponse(file_path)
        return FileResponse(_INDEX_HTML)

