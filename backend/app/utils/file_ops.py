# backend/app/utils/file_ops.py
"""
Metomi 文件操作工具
- calculate_file_hash ：流式 SHA-256 哈希（分块读取，不撑爆内存）
- sanitize_filename   ：清理非法字符，防止路径穿越与系统报错
"""

import hashlib
import re
import unicodedata
from pathlib import Path

# 分块大小：64 KB（兼顾大文件性能与内存占用）
_CHUNK_SIZE = 65_536


def calculate_file_hash(file_path: str | Path) -> str:
    """
    流式计算文件的 SHA-256 十六进制摘要。

    使用 64 KB 分块读取，即使处理数百 MB 的扫描 PDF
    也仅占用固定大小的内存。

    参数:
        file_path: 待计算哈希的文件绝对路径

    返回:
        64 字符的十六进制 SHA-256 哈希字符串

    异常:
        FileNotFoundError: 文件不存在
        PermissionError:   无读取权限
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(_CHUNK_SIZE)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest()


def sanitize_filename(filename: str) -> str:
    """
    清理文件名中的非法字符，使其安全可用于任何操作系统。

    处理规则:
    1. Unicode 标准化 (NFC)
    2. 去除路径分隔符（防止路径穿越攻击 ../../）
    3. 替换 Windows/Linux/macOS 非法字符为下划线
    4. 合并连续下划线
    5. 去除首尾空格与点号
    6. 限制最大长度为 200 字符
    7. 空文件名兜底为 "unnamed"

    参数:
        filename: 原始文件名（不含路径，不含扩展名为佳）

    返回:
        安全的文件名字符串
    """
    # 1. Unicode 标准化
    filename = unicodedata.normalize("NFC", filename)

    # 2. 去除路径分隔符（防穿越）
    filename = filename.replace("/", "_").replace("\\", "_")

    # 3. 替换 OS 非法字符：< > : " | ? * 以及控制字符
    filename = re.sub(r'[<>:"|?*\x00-\x1f]', "_", filename)

    # 4. 合并连续下划线
    filename = re.sub(r"_+", "_", filename)

    # 5. 去除首尾空格与点号（Windows 不允许文件名以点结尾）
    filename = filename.strip(" .")

    # 6. 限制长度
    if len(filename) > 200:
        filename = filename[:200]

    # 7. 兜底
    if not filename:
        filename = "unnamed"

    return filename
