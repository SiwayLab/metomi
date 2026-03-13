# backend/app/core/limiter.py
"""
共享速率限制器实例，供 main.py 和各 router 引用。
独立模块避免循环导入。
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT],
)
