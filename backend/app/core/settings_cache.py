# backend/app/core/settings_cache.py
"""
Metomi 全局设置内存缓存单例
- 系统启动时从 system_settings 表批量加载到内存
- 设置中心修改后立即刷新缓存，实现真正的热更新
- 线程安全：使用 threading.Lock 保护写操作
"""

import json
import threading
from typing import Any


class SettingsCache:
    """线程安全的全局设置缓存单例"""

    _instance: "SettingsCache | None" = None
    _lock: threading.Lock = threading.Lock()

    # ── 开发文档规定的默认配置 ──
    DEFAULTS: dict[str, str] = {
        "scraper_priority": '["OpenLibrary", "Douban"]',
        "custom_code_prefix": "MTM-",
        "export_filename_template": "{authors} - {title} ({year})",
        "scrape_delay_seconds": "3",
        "douban_cookie": "",
        "is_initialized": "false",
        "view_mode_editable_fields": '["read_status"]',
    }

    def __new__(cls) -> "SettingsCache":
        with cls._lock:
            if cls._instance is None:
                obj = super().__new__(cls)
                obj._cache: dict[str, str] = {}
                obj._initialized: bool = False
                cls._instance = obj
            return cls._instance

    # ── 读取 ──────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> str | None:
        """获取设置值（字符串），未命中则查找 DEFAULTS"""
        val = self._cache.get(key)
        if val is not None:
            return val
        return self.DEFAULTS.get(key, default)

    def get_json(self, key: str, default: Any = None) -> Any:
        """获取设置值并尝试 JSON 反序列化"""
        raw = self.get(key)
        if raw is None:
            return default
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    def get_int(self, key: str, default: int = 0) -> int:
        """获取设置值并转为整数"""
        raw = self.get(key)
        if raw is None:
            return default
        try:
            return int(raw)
        except (ValueError, TypeError):
            return default

    def get_all(self) -> dict[str, str]:
        """获取所有设置（DEFAULTS + 数据库覆盖）"""
        merged: dict[str, str] = dict(self.DEFAULTS)
        merged.update(self._cache)
        return merged

    # ── 写入 ──────────────────────────────────────────

    def set(self, key: str, value: str) -> None:
        """设置单个值（热更新时调用）"""
        with self._lock:
            self._cache[key] = value

    def delete(self, key: str) -> None:
        """删除单个值"""
        with self._lock:
            self._cache.pop(key, None)

    # ── 批量加载 ──────────────────────────────────────

    def load_from_records(self, records: list) -> None:
        """
        从 SystemSetting ORM 记录列表批量加载到缓存。
        每条 record 需要有 .setting_key 和 .setting_value 属性。
        使用原子赋值替换整个字典，避免 clear + 逐条写入期间的并发读取问题。
        """
        new_cache: dict[str, str] = {}
        for record in records:
            new_cache[record.setting_key] = record.setting_value
        with self._lock:
            self._cache = new_cache
            self._initialized = True

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def clear(self) -> None:
        """清空缓存（测试用）"""
        with self._lock:
            self._cache.clear()
            self._initialized = False


# 全局单例
settings_cache = SettingsCache()
