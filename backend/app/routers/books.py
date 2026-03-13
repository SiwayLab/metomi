# backend/app/routers/books.py
"""
图书管理路由
- GET  /books      ：分页列表 + 模糊搜索（title / author / isbn）
- POST /books      ：核心入库（含多格式合并检查 + UPSERT 关联实体）
- GET  /books/{id} ：图书详情
- PUT  /books/{id} ：更新图书信息
"""

import asyncio
import logging
import os
import shutil
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File as FastAPIFile, status
from sqlalchemy import func, or_, select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.settings_cache import settings_cache
from app.core.db import get_db
from app.core.security import get_current_user
from app.models.all_models import (
    Author,
    Book,
    File,
    Publisher,
    SystemSetting,
    User,
    book_author_link,
    book_file_link,
)
from app.schemas.api_schemas import MessageResponse
from app.schemas.book import BookCreate, BookOut, BookUpdate, PaginatedBooks
from app.utils.cover_extractor import extract_cover_from_file_sync, download_remote_cover

logger = logging.getLogger(__name__)

router = APIRouter(tags=["图书管理"])


# ═══════════════════════════════════════════════════════
#  辅助函数：UPSERT 关联实体
# ═══════════════════════════════════════════════════════

async def _upsert_authors(db: AsyncSession, names: list[str]) -> list[Author]:
    """对作者列表执行批量 UPSERT：一次查出已有，仅新建不存在的"""
    # 去重并过滤空白
    clean_names = list(dict.fromkeys(n.strip() for n in names if n.strip()))
    if not clean_names:
        return []

    # 一次性查出所有已有作者
    result = await db.execute(
        select(Author).where(Author.name.in_(clean_names))
    )
    existing = {a.name: a for a in result.scalars().all()}

    authors = []
    for name in clean_names:
        if name in existing:
            authors.append(existing[name])
        else:
            author = Author(name=name)
            db.add(author)
            await db.flush()
            existing[name] = author
            authors.append(author)
    return authors



async def _upsert_publisher(db: AsyncSession, name: str) -> Publisher | None:
    """对出版社执行 UPSERT"""
    name = name.strip()
    if not name:
        return None
    result = await db.execute(
        select(Publisher).where(Publisher.name == name)
    )
    publisher = result.scalar_one_or_none()
    if publisher is None:
        publisher = Publisher(name=name)
        db.add(publisher)
        await db.flush()
    return publisher


def _book_query_with_relations():
    """返回预加载所有关联的 Book 查询"""
    return (
        select(Book)
        .options(
            selectinload(Book.authors),
            selectinload(Book.files),
            selectinload(Book.publisher),
        )
    )


# ═══════════════════════════════════════════════════════
#  GET /books — 分页 + 模糊搜索
# ═══════════════════════════════════════════════════════

@router.get("/books", response_model=PaginatedBooks, summary="图书列表")
async def list_books(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页数量"),
    q: str = Query("", description="搜索关键字（匹配 title / author / isbn）"),
    sort: str = Query("recent", description="排序模式：recent, pub_date, title_az, read_status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    分页获取图书列表，支持按书名、作者、ISBN 模糊搜索。
    """
    base_query = _book_query_with_relations()

    # 公共搜索过滤条件
    search_condition = None
    if q:
        keyword = f"%{q}%"
        search_condition = or_(
            Book.title.ilike(keyword),
            Book.isbn.ilike(keyword),
            Book.custom_code.ilike(keyword),
            Book.id.in_(
                select(book_author_link.c.book_id).where(
                    book_author_link.c.author_id.in_(
                        select(Author.id).where(Author.name.ilike(keyword))
                    )
                )
            ),
        )
        base_query = base_query.where(search_condition)

    # 总数
    count_query = select(func.count()).select_from(Book)
    if search_condition is not None:
        count_query = count_query.where(search_condition)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 排序
    if sort == "recent":
        order_clause = Book.created_at.desc()
    elif sort == "pub_date":
        order_clause = Book.pub_date.desc()
    elif sort == "title_az":
        order_clause = Book.title.asc()
    elif sort == "read_status":
        order_clause = Book.read_status.asc()
    else:
        order_clause = Book.updated_at.desc()

    # 分页
    offset = (page - 1) * page_size
    items_query = base_query.order_by(order_clause).offset(offset).limit(page_size)
    result = await db.execute(items_query)
    items = result.scalars().unique().all()

    return PaginatedBooks(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


# ═══════════════════════════════════════════════════════
#  POST /books — 入库（含多格式合并）
# ═══════════════════════════════════════════════════════

@router.post("/books", response_model=BookOut, summary="图书入库")
async def create_book(
    payload: BookCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    核心入库逻辑：
    1. 多格式合并检查：ISBN 或 douban_id 已存在 → 仅关联 file
    2. 不存在 → UPSERT authors/tags/publisher → 创建 Book → 关联 File
    """

    # ── 多格式合并检查 ──
    existing_book = None
    if payload.isbn:
        result = await db.execute(
            _book_query_with_relations().where(Book.isbn == payload.isbn)
        )
        existing_book = result.scalars().first()
    if existing_book is None and payload.douban_id:
        result = await db.execute(
            _book_query_with_relations().where(Book.douban_id == payload.douban_id)
        )
        existing_book = result.scalars().first()

    if existing_book is not None:
        # ── 合并模式：仅关联新文件 ──
        if payload.file_id is not None:
            file_result = await db.execute(
                select(File).where(File.id == payload.file_id)
            )
            file_obj = file_result.scalar_one_or_none()
            if file_obj and file_obj not in existing_book.files:
                existing_book.files.append(file_obj)
                await db.flush()
                logger.info(
                    "多格式合并: book_id=%d, new file_id=%d",
                    existing_book.id,
                    payload.file_id,
                )

        # 重新加载完整关联
        await db.refresh(existing_book, ["authors", "files", "publisher"])
        return existing_book

    # ── 新建模式 ──

    # UPSERT 关联实体
    authors = await _upsert_authors(db, payload.author_names)
    publisher = await _upsert_publisher(db, payload.publisher_name or "")

    # 自编码逻辑：
    # 1. 前端已显式传入 custom_code → 直接使用
    # 2. 纯实体书（book_type=physical）且无 ISBN 且无关联文件 → 自动生成 UUID 后缀
    # 3. 其他情况（如导入电子书）→ 不分配自编码
    custom_code = payload.custom_code
    if not custom_code and not payload.isbn and payload.book_type == "physical" and payload.file_id is None:
        prefix = settings_cache.get("custom_code_prefix", "MTM-")
        # 使用 UUID4 前 6 位作为唯一后缀，避免竞态条件
        unique_suffix = uuid.uuid4().hex[:6].upper()
        custom_code = f"{prefix}{unique_suffix}"

    # 如果没有提供封面且有上传文件，尝试从文件提取封面
    extracted_cover_path = payload.cover_path
    if not extracted_cover_path and payload.file_id is not None:
        file_result = await db.execute(
            select(File).where(File.id == payload.file_id)
        )
        file_obj = file_result.scalar_one_or_none()
        if file_obj:
            full_path = settings.POOL_DIR / file_obj.file_path
            loop = asyncio.get_running_loop()
            try:
                cover_filename = await loop.run_in_executor(
                    None, extract_cover_from_file_sync, str(full_path), file_obj.format
                )
            except Exception as e:
                logger.error("封面提取异常: %s", e)
                cover_filename = None
            if cover_filename:
                extracted_cover_path = f"/covers/{cover_filename}"

    # 创建 Book
    book = Book(
        title=payload.title,
        isbn=payload.isbn,
        douban_id=payload.douban_id,
        custom_code=custom_code,
        description=payload.description,
        pub_date=payload.pub_date,
        language=payload.language,
        cover_path=extracted_cover_path,
        book_type=payload.book_type,
        physical_location=payload.physical_location,
        rating=payload.rating,
        publisher=publisher,
        authors=authors,
    )

    # 如果 cover_path 是远程 URL，下载到本地
    if book.cover_path and book.cover_path.startswith(("http://", "https://")):
        loop = asyncio.get_running_loop()
        local_filename = await loop.run_in_executor(
            None, download_remote_cover, book.cover_path
        )
        if local_filename:
            book.cover_path = f"/covers/{local_filename}"
        else:
            book.cover_path = None  # 下载失败则清空

    db.add(book)
    await db.flush()

    # 关联文件（直接插入关联表，避免 lazy-load 触发 MissingGreenlet）
    if payload.file_id is not None:
        file_result = await db.execute(
            select(File).where(File.id == payload.file_id)
        )
        file_obj = file_result.scalar_one_or_none()
        if file_obj:
            await db.execute(
                book_file_link.insert().values(
                    book_id=book.id, file_id=file_obj.id
                )
            )
            await db.flush()

    await db.refresh(book, ["authors", "files", "publisher"])

    logger.info("图书入库: book_id=%d, title=%s", book.id, book.title)
    return book


# ═══════════════════════════════════════════════════════
#  GET /books/{book_id} — 图书详情
# ═══════════════════════════════════════════════════════

@router.get("/books/{book_id}", response_model=BookOut, summary="图书详情")
async def get_book(
    book_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取单本图书完整信息（含关联实体）"""
    result = await db.execute(
        _book_query_with_relations().where(Book.id == book_id)
    )
    book = result.scalars().first()
    if book is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="图书不存在",
        )
    return book


# ═══════════════════════════════════════════════════════
#  PUT /books/{book_id} — 更新图书
# ═══════════════════════════════════════════════════════

@router.put("/books/{book_id}", response_model=BookOut, summary="更新图书")
async def update_book(
    book_id: int,
    payload: BookUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新图书元数据及关联实体"""
    result = await db.execute(
        _book_query_with_relations().where(Book.id == book_id)
    )
    book = result.scalars().first()
    if book is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="图书不存在",
        )

    # 更新标量字段（仅更新非 None 值）
    update_data = payload.model_dump(exclude_unset=True)

    # 空字符串转 None：防止 UNIQUE 约束冲突（isbn / douban_id 等）
    nullable_unique_fields = {"isbn", "douban_id", "custom_code"}
    for key in nullable_unique_fields:
        if key in update_data and update_data[key] == "":
            update_data[key] = None

    # 如果 update_data 包含 cover_path 且是远程 URL，先下载到本地
    if "cover_path" in update_data and update_data["cover_path"] and \
       update_data["cover_path"].startswith(("http://", "https://")):
        loop = asyncio.get_running_loop()
        local_filename = await loop.run_in_executor(
            None, download_remote_cover, update_data["cover_path"]
        )
        if local_filename:
            # Delete old cover file if it exists and is different
            if book.cover_path:
                old_basename = os.path.basename(book.cover_path)
                if old_basename:
                    old_cover_full = settings.COVERS_DIR / old_basename
                    if old_cover_full.exists():
                        old_cover_full.unlink(missing_ok=True)
                        logger.info(f"Scraped new cover. Deleted old cover file: {old_basename}")

            update_data["cover_path"] = f"/covers/{local_filename}"
        else:
            del update_data["cover_path"]  # 下载失败就不更新封面

    scalar_fields = [
        "title", "isbn", "douban_id", "custom_code", "description",
        "pub_date", "language", "cover_path",
        "book_type", "physical_location", "rating", "read_status",
    ]

    for field in scalar_fields:
        if field in update_data:
            setattr(book, field, update_data[field])

    # 更新关联实体
    if payload.author_names is not None:
        book.authors = await _upsert_authors(db, payload.author_names)

    if payload.publisher_name is not None:
        book.publisher = await _upsert_publisher(db, payload.publisher_name)

    if hasattr(payload, "file_id") and payload.file_id is not None:
        file_result = await db.execute(select(File).where(File.id == payload.file_id))
        file_obj = file_result.scalar_one_or_none()
        if file_obj and file_obj not in book.files:
            book.files.append(file_obj)

    await db.flush()

    # 重新查询完整对象（含所有关联），避免 refresh 后属性过期导致序列化失败
    result2 = await db.execute(
        _book_query_with_relations().where(Book.id == book_id)
    )
    updated_book = result2.scalars().first()
    return updated_book

# ═══════════════════════════════════════════════════════
#  DELETE /books/{book_id} — 删除图书
# ═══════════════════════════════════════════════════════

@router.delete("/books/{book_id}", response_model=MessageResponse, summary="删除图书")
async def delete_book(
    book_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    删除图书，同时清理：
    1. book_file_link / book_author_link 等 M2M 关联（CASCADE）
    2. 仅属于该书的 File 记录（孤儿文件）从 DB 删除 + 物理文件删除
    3. 封面图片物理文件删除
    """
    result = await db.execute(
        select(Book).options(
            selectinload(Book.files),
            selectinload(Book.authors),
        ).where(Book.id == book_id)
    )
    book = result.scalar_one_or_none()

    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="图书不存在",
        )

    # ── 清理封面文件（使用 basename 防止路径穿越）──
    if book.cover_path:
        cover_basename = os.path.basename(book.cover_path)
        if cover_basename:
            cover_full = settings.COVERS_DIR / cover_basename
            if cover_full.exists():
                cover_full.unlink(missing_ok=True)
                logger.info("已删除封面文件: %s", cover_full)

    # ── 找出仅属于此书的文件（孤儿文件）并删除 ──
    for file_obj in book.files:
        # 查 book_file_link 看这个 file 还被多少本书引用
        count_result = await db.execute(
            select(func.count()).select_from(book_file_link).where(
                book_file_link.c.file_id == file_obj.id
            )
        )
        ref_count = count_result.scalar() or 0
        if ref_count <= 1:
            # 只有当前这本书引用，删除物理文件和 DB 记录（basename 防穿越）
            safe_name = os.path.basename(file_obj.file_path)
            pool_path = settings.POOL_DIR / safe_name
            if pool_path.exists():
                pool_path.unlink(missing_ok=True)
                logger.info("已删除孤儿物理文件: %s", pool_path)
            await db.delete(file_obj)

    # ── 记录当前图书关联的 author_ids 和 publisher_id（删除前先保存）──
    old_author_ids = [a.id for a in book.authors]
    old_publisher_id = book.publisher_id

    # ── 真删除：级联清理中间表 ──
    await db.delete(book)
    # ── 清理不再被任何图书引用的废弃 Author 和 Publisher ──
    if old_author_ids:
        # 查询哪些老的 author 不再有任何引用
        author_counts = await db.execute(
            select(book_author_link.c.author_id, func.count(book_author_link.c.book_id))
            .where(book_author_link.c.author_id.in_(old_author_ids))
            .group_by(book_author_link.c.author_id)
        )
        kept_authors = dict(author_counts.all())
        for aid in old_author_ids:
            if kept_authors.get(aid, 0) == 0:
                await db.execute(delete(Author).where(Author.id == aid))

    if old_publisher_id:
        pub_count = await db.execute(
            select(func.count(Book.id)).where(Book.publisher_id == old_publisher_id)
        )
        if pub_count.scalar() == 0:
            await db.execute(delete(Publisher).where(Publisher.id == old_publisher_id))

    await db.commit()
    logger.info("已删除图书 ID: %s", book_id)

    return MessageResponse(message="图书已删除")


@router.delete("/books/{book_id}/files/{file_id}", response_model=BookOut, summary="移除图书下的关联文件")
async def delete_book_file_link_route(
    book_id: int,
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    删除图书与某个文件的关联（Fix 26）。
    也会检查如果该文件不再被任何图书关联，则清理物理文件并删除孤儿 File 记录。
    """
    stmt = select(book_file_link).where(
        book_file_link.c.book_id == book_id,
        book_file_link.c.file_id == file_id
    )
    result = await db.execute(stmt)
    if not result.first():
        raise HTTPException(status_code=404, detail="未找到该文件的关联记录")

    del_stmt = book_file_link.delete().where(
        book_file_link.c.book_id == book_id,
        book_file_link.c.file_id == file_id
    )
    await db.execute(del_stmt)

    count_stmt = select(func.count()).select_from(book_file_link).where(
        book_file_link.c.file_id == file_id
    )
    count_result = await db.execute(count_stmt)
    ref_count = count_result.scalar()

    if ref_count == 0:
        file_obj_res = await db.execute(select(File).where(File.id == file_id))
        file_obj = file_obj_res.scalar_one_or_none()
        if file_obj:
            if file_obj.file_path:
                safe_name = os.path.basename(file_obj.file_path)
                pool_path = settings.POOL_DIR / safe_name
                if pool_path.exists():
                    pool_path.unlink(missing_ok=True)
            await db.delete(file_obj)

    await db.commit()

    # 重新查询完整对象返回给前端更新
    result_book = await db.execute(
        _book_query_with_relations().where(Book.id == book_id)
    )
    updated_book = result_book.scalars().first()
    return updated_book

# ═══════════════════════════════════════════════════════
#  POST /books/{book_id}/cover — 手动上传封面
# ═══════════════════════════════════════════════════════


@router.post("/books/{book_id}/cover", response_model=BookOut, summary="手动上传封面")
async def upload_book_cover(
    book_id: int,
    cover: UploadFile = FastAPIFile(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    手动上传封面图片替换现有封面
    """
    result = await db.execute(
        _book_query_with_relations().where(Book.id == book_id)
    )
    book = result.scalars().first()

    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="图书不存在",
        )

    # 验证文件类型
    if cover.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持 JPG/PNG/WEBP 格式的图片",
        )

    covers_dir = settings.DATA_DIR / "covers"
    covers_dir.mkdir(parents=True, exist_ok=True)

    # 删除旧封面（使用 basename 防止路径穿越）
    if book.cover_path:
        old_basename = os.path.basename(book.cover_path)
        if old_basename:
            old_cover_full = settings.COVERS_DIR / old_basename
            if old_cover_full.exists():
                old_cover_full.unlink(missing_ok=True)

    # 保存新封面
    ext = ".jpg"
    if cover.content_type == "image/png": ext = ".png"
    elif cover.content_type == "image/webp": ext = ".webp"
    
    new_filename = f"cover_manual_{book_id}_{uuid.uuid4().hex[:8]}{ext}"
    new_filepath = covers_dir / new_filename

    def _sync_save_cover(src_file, dest_path):
        with open(dest_path, "wb") as f:
            shutil.copyfileobj(src_file, f)

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _sync_save_cover, cover.file, new_filepath)

    book.cover_path = f"/covers/{new_filename}"
    await db.flush()
    
    # 重新查询以便返回最新数据
    result2 = await db.execute(
        _book_query_with_relations().where(Book.id == book_id)
    )
    return result2.scalars().first()
