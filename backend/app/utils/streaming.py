# backend/app/utils/streaming.py
"""
Metomi HTTP Range Requests 流式响应工具

支持 HTTP 206 Partial Content，配合 pdf.js / epub.js 实现按需加载。
使用 StreamingResponse 分块传输，避免将大文件整个读入内存。
"""

import os
import stat
from typing import Generator

from fastapi import Request
from starlette.responses import StreamingResponse, Response


# 每次分块传输的大小
_CHUNK_SIZE = 64 * 1024  # 64 KB


def _file_chunk_generator(
    file_path: str, start: int, length: int
) -> Generator[bytes, None, None]:
    """按块生成文件内容"""
    with open(file_path, "rb") as f:
        f.seek(start)
        remaining = length
        while remaining > 0:
            chunk_size = min(_CHUNK_SIZE, remaining)
            data = f.read(chunk_size)
            if not data:
                break
            remaining -= len(data)
            yield data


def range_requests_response(
    request: Request,
    file_path: str,
    content_type: str,
    download_name: str = None,
) -> Response:
    """
    根据 HTTP Range 请求头返回文件的部分或全部内容。

    - 有 Range 头：返回 206 Partial Content + Content-Range
    - 无 Range 头：返回 200 OK + 完整文件（分块流式传输）
    """
    file_size = os.stat(file_path)[stat.ST_SIZE]
    range_header = request.headers.get("range")

    # ── 无 Range 头：流式返回完整文件 ──
    if range_header is None:
        import urllib.parse
        headers = {
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes",
            "Content-Type": content_type,
        }
        if download_name:
            encoded_name = urllib.parse.quote(download_name)
            headers["Content-Disposition"] = f"attachment; filename*=utf-8''{encoded_name}"
        return StreamingResponse(
            _file_chunk_generator(file_path, 0, file_size),
            status_code=200,
            headers=headers,
            media_type=content_type,
        )

    # ── 解析 Range 头 ──
    range_str = range_header.strip().lower()
    if not range_str.startswith("bytes="):
        return Response(
            content=b"Invalid Range header",
            status_code=416,
            headers={
                "Content-Range": f"bytes */{file_size}",
                "Content-Type": "text/plain",
            },
        )

    range_spec = range_str[6:]
    parts = range_spec.split("-", 1)

    start: int
    end: int

    try:
        if parts[0] == "":
            suffix_length = int(parts[1])
            start = max(0, file_size - suffix_length)
            end = file_size - 1
        elif parts[1] == "":
            start = int(parts[0])
            end = file_size - 1
        else:
            start = int(parts[0])
            end = int(parts[1])
    except ValueError:
        return Response(
            content=b"Invalid Range header values",
            status_code=416,
            headers={
                "Content-Range": f"bytes */{file_size}",
                "Content-Type": "text/plain",
            },
        )

    # 边界校验
    if start < 0:
        start = 0
    if end >= file_size:
        end = file_size - 1
    if start > end:
        return Response(
            content=b"Range Not Satisfiable",
            status_code=416,
            headers={
                "Content-Range": f"bytes */{file_size}",
                "Content-Type": "text/plain",
            },
        )

    content_length = end - start + 1

    resp = StreamingResponse(
        _file_chunk_generator(file_path, start, content_length),
        status_code=206,
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Content-Length": str(content_length),
            "Accept-Ranges": "bytes",
            "Content-Type": content_type,
        },
        media_type=content_type,
    )

    if download_name:
        import urllib.parse
        encoded_name = urllib.parse.quote(download_name)
        resp.headers["Content-Disposition"] = f"attachment; filename*=utf-8''{encoded_name}"
    
    return resp
