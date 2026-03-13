# backend/app/services/scraper.py
"""
Metomi 异步刮削服务
- 豆瓣刮削：参考 Calibre 豆瓣插件，使用 httpx + BeautifulSoup 解析
- OpenLibrary 备份源：免费 REST API
- 统一输出格式的字典
"""

import asyncio
import logging
import random
import re
from typing import Optional
from urllib.parse import urlencode, urlparse, unquote

import httpx
from bs4 import BeautifulSoup

from app.core.settings_cache import settings_cache

logger = logging.getLogger(__name__)

# ── 常量 ──
DOUBAN_SEARCH_URL = "https://www.douban.com/search"
DOUBAN_BOOK_URL = "https://book.douban.com/subject/%s/"
DOUBAN_BOOK_CAT = "1001"
DOUBAN_BOOK_URL_PATTERN = re.compile(r".*/subject/(\d+)/?")

OPENLIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
OPENLIBRARY_ISBN_URL = "https://openlibrary.org/isbn/%s.json"
OPENLIBRARY_COVERS_URL = "https://covers.openlibrary.org/b/isbn/%s-L.jpg"

# ── 随机 User-Agent 池 ──
_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
]


def _random_ua() -> str:
    return random.choice(_USER_AGENTS)


def _empty_result() -> dict:
    """返回空的统一结果结构"""
    return {
        "title": "",
        "authors": [],
        "publisher": "",
        "isbn": "",
        "douban_id": "",
        "cover_url": "",
        "description": "",
        "rating": None,
        "pub_date": "",
        "tags": [],
        "language": "",
        "source": "",
    }


def _build_douban_headers(cookie: str = "") -> dict:
    """构造豆瓣请求 headers（含随机 UA 和可选 Cookie）"""
    headers = {
        "User-Agent": _random_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Referer": "https://book.douban.com/",
    }
    if cookie:
        headers["Cookie"] = cookie
    return headers


# ═══════════════════════════════════════════════════════════
#  豆瓣刮削（主刮削源）
# ═══════════════════════════════════════════════════════════

async def scrape_douban(isbn_or_title: str) -> dict:
    """
    异步豆瓣刮削：先搜索获取书籍 URL，再解析详情页。
    从 SettingsCache 读取 douban_cookie。
    加入随机 User-Agent 和 3-5 秒延迟防封。
    """
    result = _empty_result()
    result["source"] = "douban"

    # 读取配置
    cookie = settings_cache.get("douban_cookie", "")
    delay = settings_cache.get_int("scrape_delay_seconds", 3)

    headers = _build_douban_headers(cookie)

    try:
        async with httpx.AsyncClient(
            headers=headers,
            timeout=20.0,
            follow_redirects=True,
        ) as client:
            # ── 随机延迟 ──
            await asyncio.sleep(random.uniform(delay, delay + 2))

            # ── 搜索：获取书籍详情页 URL ──
            book_url = await _douban_search(client, isbn_or_title)
            if not book_url:
                logger.warning("豆瓣搜索无结果: %s", isbn_or_title)
                return result

            # ── 再次随机延迟 ──
            await asyncio.sleep(random.uniform(delay, delay + 2))

            # ── 请求详情页并解析 ──
            resp = await client.get(book_url)
            if resp.status_code != 200:
                logger.warning("豆瓣详情页请求失败: %d %s", resp.status_code, book_url)
                return result

            html_text = resp.text
            if "<title>禁止访问</title>" in html_text:
                logger.warning("豆瓣访问被禁止（需要验证码或 Cookie 过期）")
                return result

            result = _parse_douban_detail(html_text, book_url)
            result["source"] = "douban"

    except httpx.HTTPError as e:
        logger.warning("豆瓣刮削网络错误: %s", e)
    except Exception as e:
        logger.warning("豆瓣刮削异常: %s", e)

    return result


async def _douban_search(client: httpx.AsyncClient, query: str) -> Optional[str]:
    """搜索豆瓣，返回第一个匹配的书籍详情页 URL"""
    results = await _douban_search_multi(client, query, limit=1)
    if results:
        return results[0]["id"] # 这里存的是 URL
    return None

async def _douban_search_multi(client: httpx.AsyncClient, query: str, limit: int = 5) -> list[dict]:
    """搜索豆瓣，返回多个匹配项基本信息"""
    params = {"cat": DOUBAN_BOOK_CAT, "q": query}
    url = DOUBAN_SEARCH_URL + "?" + urlencode(params)
    logger.info("豆瓣搜索多项: %s", url)

    resp = await client.get(url)
    if resp.status_code != 200:
        return []

    html = BeautifulSoup(resp.text, "html.parser")
    items = html.select(".result-list .result")
    
    results = []
    
    # 如果没有 .result-list，尝试兜底解析
    if not items:
        for link in html.select("a.nbg"):
            href = link.get("href", "")
            parsed_url = _extract_book_url(href)
            if parsed_url:
                title_img = link.select_one("img")
                title = title_img.get("title", "") if title_img else ""
                cover = title_img.get("src", "") if title_img else ""
                
                # 找作者/出版社兄弟节点 (比较简陋)
                parent_td = link.find_parent("td")
                info = ""
                if parent_td and parent_td.find_next_sibling("td"):
                    info = parent_td.find_next_sibling("td").get_text(separator=" ", strip=True)
                
                results.append({
                    "id": parsed_url,
                    "title": title or "未知标题",
                    "authors": [info.split("/")[0].strip()] if info else [],
                    "publisher": info.split("/")[-3].strip() if info and len(info.split("/")) > 2 else "",
                    "cover_url": cover,
                    "source": "douban"
                })
                if len(results) >= limit: break
        return results
        
    for item in items:
        # 解析标准搜索结果项
        title_el = item.select_one(".title a")
        if not title_el:
            continue
            
        href = title_el.get("href", "")
        parsed_url = _extract_book_url(href)
        if not parsed_url:
            continue
            
        title = title_el.get_text(strip=True)
        cover_el = item.select_one("img")
        cover_url = cover_el.get("src", "") if cover_el else ""
        
        info_el = item.select_one(".subject-cast")
        info = info_el.get_text(strip=True) if info_el else ""
        
        parts = info.split("/")
        authors = [parts[0].strip()] if parts else []
        publisher = parts[-3].strip() if len(parts) > 2 else ""
        
        results.append({
            "id": parsed_url,  # 对于豆瓣，id 存完整的 url 以便后续获取详情
            "title": title,
            "authors": authors,
            "publisher": publisher,
            "cover_url": cover_url,
            "source": "douban"
        })
        if len(results) >= limit:
            break
            
    return results


def _extract_book_url(href: str) -> Optional[str]:
    """从搜索结果的跳转链接中提取真实书籍 URL"""
    try:
        query = urlparse(href).query
        if not query:
            if DOUBAN_BOOK_URL_PATTERN.match(href):
                return href
            return None
        params = dict(item.split("=", 1) for item in query.split("&") if "=" in item)
        url = unquote(params.get("url", ""))
        if DOUBAN_BOOK_URL_PATTERN.match(url):
            return url
    except Exception:
        pass
    return None


def _parse_douban_detail(html_text: str, url: str) -> dict:
    """参考 Calibre 插件 DoubanBookHtmlParser.parse_book 解析豆瓣详情页"""
    result = _empty_result()
    html = BeautifulSoup(html_text, "html.parser")

    # 标题
    title_el = html.select_one("span[property='v:itemreviewed']")
    if title_el:
        result["title"] = title_el.get_text(strip=True)

    # 豆瓣 ID
    id_match = DOUBAN_BOOK_URL_PATTERN.match(url)
    if id_match:
        result["douban_id"] = id_match.group(1)

    # 封面
    cover_el = html.select_one("a.nbg")
    if cover_el:
        cover_href = cover_el.get("href", "")
        if cover_href and not cover_href.endswith("update_image"):
            result["cover_url"] = cover_href

    # 评分
    rating_el = html.select_one("strong[property='v:average']")
    if rating_el:
        try:
            result["rating"] = round(float(rating_el.get_text(strip=True)) / 2, 1)
        except (ValueError, TypeError):
            pass

    # 解析 info 区域的 span.pl 字段
    for span in html.select("span.pl"):
        text = span.get_text(strip=True)
        parent = span.find_parent()
        if not parent:
            continue

        if text.startswith("作者"):
            authors = []
            for a in parent.select("a"):
                a_href = a.get("href", "")
                if "/author" in a_href or "/search" in a_href:
                    name = a.get_text(strip=True)
                    if name:
                        authors.append(name)
            result["authors"] = authors

        elif text.startswith("出版社"):
            result["publisher"] = _get_tail_text(span)

        elif text.startswith("副标题"):
            subtitle = _get_tail_text(span)
            if subtitle:
                result["title"] = result["title"] + ":" + subtitle

        elif text.startswith("出版年"):
            result["pub_date"] = _get_tail_text(span)

        elif text.startswith("ISBN"):
            result["isbn"] = _get_tail_text(span)

    # 简介
    summary_divs = html.select("div#link-report div.intro")
    if summary_divs:
        # 取最后一个 intro（展开后的完整版）
        intro_html = summary_divs[-1]
        # 提取纯文本段落
        paragraphs = [p.get_text(strip=True) for p in intro_html.select("p")]
        result["description"] = "\n".join(paragraphs) if paragraphs else intro_html.get_text(strip=True)

    # 标签
    tag_pattern = re.compile(r"criteria = '(.+)'")
    tag_match = tag_pattern.findall(html_text)
    if tag_match:
        tags = []
        for tag in tag_match[0].split("|"):
            if tag and tag.startswith("7:"):
                tags.append(tag[2:])
        result["tags"] = tags

    # 语言推断
    if result["title"]:
        if "英文版" in result["title"] or re.match(r"^[a-zA-Z\-_ ]+$", result["title"]):
            result["language"] = "en"
        else:
            result["language"] = "zh"

    return result


def _get_tail_text(element) -> str:
    """获取 span.pl 后面的兄弟文本节点（参考 Calibre 插件 get_tail）"""
    text = ""
    if element and element.next_siblings:
        for sibling in element.next_siblings:
            if isinstance(sibling, str):
                text += sibling.strip()
            else:
                if not text:
                    text = sibling.get_text(strip=True)
                break
    return text.strip()


# ═══════════════════════════════════════════════════════════
#  OpenLibrary 备份刮削源
# ═══════════════════════════════════════════════════════════

async def scrape_openlibrary(isbn_or_title: str) -> dict:
    """
    OpenLibrary 备份刮削源。
    优先用 ISBN 精确查询，无 ISBN 时退化为标题搜索。
    """
    result = _empty_result()
    result["source"] = "openlibrary"

    headers = {"User-Agent": _random_ua()}

    try:
        async with httpx.AsyncClient(
            headers=headers,
            timeout=15.0,
            follow_redirects=True,
        ) as client:
            # 判断是否为 ISBN
            clean_query = isbn_or_title.replace("-", "").strip()
            is_isbn = bool(re.match(r"^\d{10,13}$", clean_query))

            if is_isbn:
                result = await _openlibrary_by_isbn(client, clean_query)
            else:
                result = await _openlibrary_by_title(client, isbn_or_title)

            result["source"] = "openlibrary"

    except httpx.HTTPError as e:
        logger.warning("OpenLibrary 网络错误: %s", e)
    except Exception as e:
        logger.warning("OpenLibrary 刮削异常: %s", e)

    return result


async def _openlibrary_by_isbn(client: httpx.AsyncClient, isbn: str) -> dict:
    """通过 ISBN 查询 OpenLibrary"""
    result = _empty_result()
    params = {"bibkeys": f"ISBN:{isbn}", "format": "data", "jscmd": "data"}
    resp = await client.get("https://openlibrary.org/api/books", params=params)
    if resp.status_code != 200:
        return result

    data = resp.json()
    key = f"ISBN:{isbn}"
    if key not in data:
        return result

    book = data[key]
    result["title"] = book.get("title", "")
    result["authors"] = [a.get("name", "") for a in book.get("authors", [])]
    result["publisher"] = book.get("publishers", [{}])[0].get("name", "") if book.get("publishers") else ""
    result["isbn"] = isbn
    result["pub_date"] = book.get("publish_date", "")
    result["description"] = ""
    result["cover_url"] = book.get("cover", {}).get("large", "") or OPENLIBRARY_COVERS_URL % isbn

    # 获取 subjects 作为 tags
    result["tags"] = [s.get("name", "") for s in book.get("subjects", [])[:10]]

    return result


async def _openlibrary_by_title(client: httpx.AsyncClient, title: str) -> dict:
    """通过标题搜索 OpenLibrary（返回第一个）"""
    results = await _openlibrary_search_multi(client, title, limit=1)
    if results:
        # 返回类似单本书的结构
        res = _empty_result()
        res.update(results[0])
        # _openlibrary_search_multi 没返回年份/isbn/tags等完整详情，需要补全(简单实现)
        res["pub_date"] = results[0].get("pub_date", "")
        res["isbn"] = results[0].get("isbn", "")
        res["tags"] = results[0].get("tags", [])
        return res
    return _empty_result()


async def _openlibrary_search_multi(client: httpx.AsyncClient, query: str, limit: int = 5) -> list[dict]:
    """搜 OpenLibrary 返回多个"""
    params = {"q": query, "limit": limit, "fields": "key,title,author_name,isbn,publisher,first_publish_year,subject,cover_i"}
    resp = await client.get(OPENLIBRARY_SEARCH_URL, params=params)
    if resp.status_code != 200:
        return []

    data = resp.json()
    docs = data.get("docs", [])
    
    results = []
    for doc in docs:
        isbns = doc.get("isbn", [])
        isbn = isbns[0] if isbns else ""
        cover_id = doc.get("cover_i")
        cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else ""
        
        results.append({
            "id": doc.get("key", ""),
            "title": doc.get("title", ""),
            "authors": doc.get("author_name", []),
            "publisher": doc.get("publisher", [""])[0] if doc.get("publisher") else "",
            "cover_url": cover_url,
            "source": "openlibrary",
            "isbn": isbn,
            "pub_date": str(doc.get("first_publish_year", "")),
            "tags": doc.get("subject", [])[:10]
        })
        
    return results


# ═══════════════════════════════════════════════════════════
#  统一调度：按优先级依次尝试
# ═══════════════════════════════════════════════════════════

async def scrape_by_priority(isbn_or_title: str) -> dict | None:
    """
    根据 system_settings.scraper_priority 依次尝试刮削源。
    第一个返回有效结果的源即终止。
    """
    priority = settings_cache.get_json("scraper_priority", ["OpenLibrary", "Douban"])

    scrapers = {
        "Douban": scrape_douban,
        "OpenLibrary": scrape_openlibrary,
    }

    for source_name in priority:
        func = scrapers.get(source_name)
        if func is None:
            logger.warning("未知刮削源: %s", source_name)
            continue

        logger.info("尝试刮削源: %s，查询: %s", source_name, isbn_or_title)
        try:
            result = await func(isbn_or_title)
            if result.get("title"):
                logger.info("刮削成功 [%s]: %s", source_name, result["title"])
                return result
        except Exception as e:
            logger.warning("刮削源 %s 失败: %s", source_name, e)
            continue

    # 所有源均失败，返回 None
    return None

async def search_candidates(query: str, limit: int = 5) -> list[dict]:
    """
    返回包含多个候选书籍的列表（包含不同数据源）。
    此函数仅做轻量级搜索，返回：title, authors, publisher, cover_url, id, source
    """
    candidates = []
    
    # 豆瓣
    cookie = settings_cache.get("douban_cookie", "")
    douban_headers = _build_douban_headers(cookie)

    try:
        async with httpx.AsyncClient(headers=douban_headers, timeout=15.0, follow_redirects=True) as client:
            douban_res = await _douban_search_multi(client, query, limit=3)
            candidates.extend(douban_res)
    except Exception as e:
        logger.warning("豆瓣搜索候选失败: %s", e)

    # OpenLibrary
    try:
        async with httpx.AsyncClient(headers={"User-Agent": _random_ua()}, timeout=10.0, follow_redirects=True) as client:
            ol_res = await _openlibrary_search_multi(client, query, limit=2)
            candidates.extend(ol_res)
    except Exception as e:
        logger.warning("OpenLibrary 搜索候选失败: %s", e)
        
    return candidates

async def fetch_candidate_detail(source: str, candidate_id: str) -> dict:
    """
    获取单个候选对象的详情。
    若是豆瓣，candidate_id 即为详情页 URL。
    若是 OpenLibrary，candidate_id 则是 key (如 "/works/OL123W") 或类似，但我们之前可以直接复用 scrape_openlibrary
    """
    if source == "douban":
        delay = settings_cache.get_int("scrape_delay_seconds", 3)
        cookie = settings_cache.get("douban_cookie", "")
        headers = {"User-Agent": _random_ua()}
        if cookie:
            headers["Cookie"] = cookie
            
        try:
            async with httpx.AsyncClient(headers=headers, timeout=20.0, follow_redirects=True) as client:
                await asyncio.sleep(random.uniform(delay, delay + 2))
                resp = await client.get(candidate_id)
                if resp.status_code == 200:
                    res = _parse_douban_detail(resp.text, candidate_id)
                    res["source"] = "douban"
                    return res
        except Exception as e:
            logger.warning("豆瓣详情获取失败: %s", e)
            
    elif source == "openlibrary":
        # 从 OpenLibrary Works API 获取详情
        try:
            async with httpx.AsyncClient(headers={"User-Agent": _random_ua()}, timeout=15.0, follow_redirects=True) as client:
                # candidate_id 是 works key 比如 /works/OL1...
                works_url = f"https://openlibrary.org{candidate_id}.json"
                resp = await client.get(works_url)
                if resp.status_code == 200:
                    data = resp.json()
                    res = _empty_result()
                    res["title"] = data.get("title", "")
                    # description 可能是字符串或字典
                    desc = data.get("description", "")
                    if isinstance(desc, dict):
                        desc = desc.get("value", "")
                    res["description"] = desc
                    # 作者需要从 author keys 来获取
                    author_keys = [a.get("author", {}).get("key", "") for a in data.get("authors", [])]
                    for ak in author_keys:
                        if ak:
                            author_resp = await client.get(f"https://openlibrary.org{ak}.json")
                            if author_resp.status_code == 200:
                                res["authors"].append(author_resp.json().get("name", ""))
                    # subjects 作为 tags
                    res["tags"] = data.get("subjects", [])[:10]
                    # 封面
                    covers = data.get("covers", [])
                    if covers:
                        res["cover_url"] = f"https://covers.openlibrary.org/b/id/{covers[0]}-L.jpg"
                    res["source"] = "openlibrary"
                    return res
        except Exception as e:
            logger.warning("OpenLibrary详情获取失败: %s", e)
            
    return _empty_result()
