# backend/app/core/config.py
"""
Metomi 全局配置模块
使用 pydantic-settings 从环境变量 / .env 文件读取配置，支持一键覆盖。
"""

import secrets
import logging
from pathlib import Path
from typing import List

from pydantic import model_validator
from pydantic_settings import BaseSettings

_config_logger = logging.getLogger(__name__)

# ── 路径常量（基于文件位置推导，不依赖 CWD）──
_BASE_DIR = Path(__file__).resolve().parent.parent.parent  # metomi/backend/
_PROJECT_ROOT = _BASE_DIR.parent                           # metomi/
_DATA_DIR = _PROJECT_ROOT / "data"


class Settings(BaseSettings):
    """应用全局配置，可通过环境变量或 .env 文件覆盖"""

    # ── 项目基本信息 ──
    PROJECT_NAME: str = "Metomi"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # ── JWT 鉴权与 Cookie ──
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 小时
    
    # 【安全说明】当前使用 HttpOnly Cookie 存放凭证，依赖浏览器的 SameSite 策略防御 CSRF。
    # - "lax" (默认): 允许部分顶级导航携带 Cookie，适合前后端同源或部分简单跨域场景。
    # - "strict": 最安全的 CSRF 防御，但禁止所有跨站带 Cookie 的请求。
    # - "none": 若未来完全放开 CORS (如前后端分离部署在完全不同的域名)，必须设为 "none" 且强制 COOKIE_SECURE=True，
    #   同时强烈建议在后端配合引入自定义 CSRF Token 校验中间件（例如 X-CSRF-Token 请求头）。
    COOKIE_SAMESITE: str = "lax"
    COOKIE_SECURE: bool = False  # 视乎环境决定，可通过 DEBUG=False 在下方的 Validator 里强制设 True

    # ── 数据库 ──
    # Note: sqlite requires 4 slashes for an absolute path on Linux/macOS
    DATABASE_URL: str = f"sqlite+aiosqlite:////{_DATA_DIR / 'db' / 'metomi.db'}"

    # ── 文件路径 ──
    BASE_DIR: Path = _BASE_DIR
    DATA_DIR: Path = _DATA_DIR
    DB_DIR: Path = _DATA_DIR / "db"
    POOL_DIR: Path = _DATA_DIR / "pool"
    COVERS_DIR: Path = _DATA_DIR / "covers"
    STAGING_DIR: Path = _DATA_DIR / "staging"

    # ── 速率限制 ──
    RATE_LIMIT: str = "60/minute"

    # ── 上传限制 ──
    MAX_UPLOAD_SIZE_MB: int = 1024

    # ── CORS 允许的源 ──
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @model_validator(mode="after")
    def _check_secret_key(self):
        _placeholder = {"metomi-secret-key-please-change-in-production", "secret", ""}
        if self.SECRET_KEY in _placeholder:
            generated = secrets.token_urlsafe(32)
            _config_logger.warning(
                "⚠️  SECRET_KEY 未配置或使用了占位符！已自动生成临时密钥（每次重启后登录态将失效）。"
                "请在 .env 文件中设置 SECRET_KEY=<your-random-key> 以持久化会话。"
            )
            self.SECRET_KEY = generated
        return self

    @model_validator(mode="after")
    def _check_cookie_secure(self):
        # Default to False. Allow setting it via ENV if the user deploys with HTTPS
        # We cannot force True here because many users will deploy via IP address (http://IP_ADDRESS:8000)
        # and browsers will block Secure cookies over HTTP, causing an infinite login loop.
        pass
        return self

    @model_validator(mode="before")
    @classmethod
    def _parse_cors_origins(cls, values):
        """支持环境变量中逗号分隔的 CORS_ORIGINS，如 CORS_ORIGINS=http://a.com,http://b.com"""
        origins = values.get("CORS_ORIGINS")
        if isinstance(origins, str):
            values["CORS_ORIGINS"] = [o.strip() for o in origins.split(",") if o.strip()]
        return values


# 全局单例
settings = Settings()
