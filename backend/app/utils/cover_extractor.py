# backend/app/utils/cover_extractor.py
import logging
import traceback
import uuid
import fitz  # PyMuPDF
import httpx
import ebooklib
from ebooklib import epub
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

def extract_cover_from_file_sync(file_path: str, format_ext: str) -> Optional[str]:
    """
    同步从文件中提取封面，保存到 COVERS_DIR，并返回相对于 COVERS_DIR 的文件名。
    """
    try:
        covers_dir = Path(settings.COVERS_DIR)
        covers_dir.mkdir(parents=True, exist_ok=True)
        
        file_ext = format_ext.lower().lstrip('.')
        if file_ext == 'pdf':
            return _extract_from_pdf(file_path, covers_dir)
        elif file_ext == 'epub':
            return _extract_from_epub(file_path, covers_dir)
        else:
            logger.warning("Unsupported format for cover extraction: %s", file_ext)
            return None
    except Exception as e:
        logger.error("Failed to extract cover from %s: %s", file_path, e)
        return None

def _extract_from_pdf(file_path: str, covers_dir: Path) -> Optional[str]:
    """使用 PyMuPDF 从 PDF 渲染第一页作为封面"""
    try:
        doc = fitz.open(file_path)
        if len(doc) == 0:
            return None
            
        page = doc[0]
        # 缩小一些比例，提高提取速度，作为封面不需要太高兴像素
        matrix = fitz.Matrix(1.5, 1.5)
        pix = page.get_pixmap(matrix=matrix)
        
        filename = f"cover_{uuid.uuid4().hex[:12]}.png"
        save_path = covers_dir / filename
        pix.save(str(save_path))
        
        doc.close()
        return filename
    except Exception as e:
        logger.error("Error rendering PDF cover for %s: %s", file_path, e)
        return None

def _extract_from_epub(file_path: str, covers_dir: Path) -> Optional[str]:
    """使用 ebooklib 从 EPUB 中提取封面图片"""
    try:
        book = epub.read_epub(file_path)
        cover_image = None
        
        # 1. 尝试找 cover items
        # ebooklib 有时候把 cover 标记存储在一些固定 property 或者是 id="cover" 这种
        for item in book.get_items_of_type(ebooklib.ITEM_COVER):
            cover_image = item
            break
            
        if not cover_image:
            # 2. 从所有图片中尝试找到 cover
            for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
                if 'cover' in item.id.lower() or 'cover' in item.file_name.lower():
                    cover_image = item
                    break
                    
        if not cover_image:
            # 3. 退而求其次，拿到第一张大一点的图
            images = list(book.get_items_of_type(ebooklib.ITEM_IMAGE))
            if images:
                cover_image = images[0]
                
        if cover_image:
            content = cover_image.get_content()
            # 简单判断后缀
            orig_name = cover_image.file_name.lower()
            ext = ".jpg"
            if orig_name.endswith('.png'): ext = ".png"
            elif orig_name.endswith('.jpeg'): ext = ".jpg"
            elif orig_name.endswith('.gif'): ext = ".gif"
            
            filename = f"cover_{uuid.uuid4().hex[:12]}{ext}"
            save_path = covers_dir / filename
            
            with open(save_path, "wb") as f:
                f.write(content)
            return filename
            
        return None
    except Exception as e:
        logger.error("Error extracting EPUB cover from %s: %s\n%s", file_path, e, traceback.format_exc())
        return None


def download_remote_cover(url: str) -> Optional[str]:
    """
    下载远程封面图片到 COVERS_DIR 并返回文件名（同步方法）。
    如果 url 不是 http/https 开头则返回 None。
    增加域名白名单和大小限制以防 SSRF 与资源耗尽。
    """
    if not url or not url.startswith(("http://", "https://")):
        return None

    # ── SSRF 防护：域名白名单 ──
    from urllib.parse import urlparse
    _COVER_DOMAIN_ALLOWLIST = {
        "img1.doubanio.com", "img2.doubanio.com", "img3.doubanio.com",
        "img9.doubanio.com", "img.doubanio.com",
        "covers.openlibrary.org",
        "images-na.ssl-images-amazon.com",
        "m.media-amazon.com",
    }
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    if hostname not in _COVER_DOMAIN_ALLOWLIST:
        logger.warning("封面下载被拒绝：域名 %s 不在白名单中 (url=%s)", hostname, url)
        return None

    # ── 大小限制 ──
    _MAX_COVER_SIZE = 10 * 1024 * 1024  # 10 MB

    try:
        covers_dir = Path(settings.COVERS_DIR)
        covers_dir.mkdir(parents=True, exist_ok=True)

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/122.0.0.0 Safari/537.36",
            "Referer": "https://book.douban.com/",
        }

        with httpx.Client(headers=headers, timeout=15.0, follow_redirects=True) as client:
            # 流式下载，避免大文件一次性读入内存
            with client.stream("GET", url) as resp:
                resp.raise_for_status()

                # 预检 Content-Length
                cl = resp.headers.get("Content-Length")
                if cl and int(cl) > _MAX_COVER_SIZE:
                    logger.warning("封面文件过大 (Content-Length=%s)，跳过: %s", cl, url)
                    return None

                # 判断后缀
                content_type = resp.headers.get("Content-Type", "")
                if "png" in content_type:
                    ext = ".png"
                elif "webp" in content_type:
                    ext = ".webp"
                elif "gif" in content_type:
                    ext = ".gif"
                else:
                    ext = ".jpg"

                filename = f"cover_{uuid.uuid4().hex[:12]}{ext}"
                save_path = covers_dir / filename

                downloaded = 0
                with open(save_path, "wb") as f:
                    for chunk in resp.iter_bytes(8192):
                        downloaded += len(chunk)
                        if downloaded > _MAX_COVER_SIZE:
                            logger.warning("封面下载超过大小限制 (%d bytes)，中止: %s", downloaded, url)
                            f.close()
                            save_path.unlink(missing_ok=True)
                            return None
                        f.write(chunk)

        # 验证文件大小（太小可能是占位符/错误）
        if save_path.stat().st_size < 500:
            save_path.unlink(missing_ok=True)
            logger.warning("下载的封面文件过小 (<%d bytes)，丢弃: %s", 500, url)
            return None

        logger.info("封面已下载到本地: %s -> %s", url, filename)
        return filename
    except Exception as e:
        logger.warning("下载远程封面失败 [%s]: %s", url, e)
        return None
