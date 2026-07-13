import asyncio
import html
import logging
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx

from app.config import settings
from app.services.crawler_service import crawler_service

logger = logging.getLogger(__name__)

SEARCH_API_URL = "https://openapi.naver.com/v1/search/news.json"
PAGE_SIZE = 100
MAX_START = 1000

_TAG_RE = re.compile(r"<[^>]+>")


def _clean_text(value: str) -> str:
    return html.unescape(_TAG_RE.sub("", value or "")).strip()


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        try:
            parsed = parsedate_to_datetime(str(value))
        except Exception:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _in_window(value: str | None, start_at: datetime | None, end_at: datetime | None) -> bool:
    published_at = _parse_datetime(value)
    if published_at is None:
        return True
    if start_at and published_at < start_at:
        return False
    if end_at and published_at > end_at:
        return False
    return True


async def _search_naver_links(
    keyword: str,
    max_results: int,
    deadline: float,
    start_at: datetime | None,
    end_at: datetime | None,
) -> list[dict]:
    if not settings.NAVER_CLIENT_ID or not settings.NAVER_CLIENT_SECRET:
        logger.warning("NAVER_CLIENT_ID/SECRET이 설정되지 않아 네이버 소스를 건너뜁니다.")
        return []

    headers = {
        "X-Naver-Client-Id": settings.NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": settings.NAVER_CLIENT_SECRET,
    }
    results: list[dict] = []
    seen_links: set[str] = set()

    async with httpx.AsyncClient(headers=headers, timeout=10) as client:
        start = 1
        while len(results) < max_results and start <= MAX_START:
            if time.monotonic() >= deadline:
                logger.warning("네이버 링크 수집 시간 초과 - %d건까지 수집됨", len(results))
                break

            params = {
                "query": keyword,
                "display": PAGE_SIZE,
                "start": start,
                "sort": "date",
            }
            try:
                resp = await client.get(SEARCH_API_URL, params=params)
                resp.raise_for_status()
                payload = resp.json()
            except Exception as e:
                logger.warning("네이버 검색 API 요청 실패 start=%s: %s", start, e)
                break

            items = payload.get("items", [])
            if not items:
                break

            for item in items:
                if not _in_window(item.get("pubDate"), start_at, end_at):
                    continue
                link = item.get("originallink") or item.get("link")
                if not link or link in seen_links:
                    continue
                seen_links.add(link)
                results.append({
                    "title": _clean_text(item.get("title", "")),
                    "link": link,
                    "pub_date": item.get("pubDate", ""),
                })
                if len(results) >= max_results:
                    break

            start += PAGE_SIZE

    return results[:max_results]


async def get_news(
    keyword: str,
    *,
    limit: int = 100,
    published_after: str | None = None,
    published_before: str | None = None,
    timeout_seconds: float = settings.NEWS_SOURCE_TIMEOUT,
) -> list[dict]:
    cleaned_keyword = keyword.strip()
    if not cleaned_keyword:
        return []

    start_at = _parse_datetime(published_after)
    end_at = _parse_datetime(published_before)

    start_time = time.monotonic()
    discovery_deadline = start_time + min(settings.LINK_DISCOVERY_TIMEOUT, timeout_seconds)
    links = await _search_naver_links(cleaned_keyword, limit, discovery_deadline, start_at, end_at)

    remaining = timeout_seconds - (time.monotonic() - start_time)
    if remaining <= 0 or not links:
        return []

    semaphore = asyncio.Semaphore(settings.CRAWL_CONCURRENCY)
    results: list[dict] = []

    async def process_item(item: dict):
        async with semaphore:
            crawled = await crawler_service.crawl_article(item["link"])
        published = (crawled.get("published_at") if crawled else None) or item["pub_date"]
        if not _in_window(published, start_at, end_at):
            return
        results.append({
            "title": item["title"],
            "link": item["link"],
            "article_link": item["link"],
            "original_url": item["link"],
            "source_name": (crawled.get("source_name") if crawled else None) or "Unknown",
            "source_url": None,
            "published": published,
            "content": (crawled.get("content") if crawled else "") or "",
            "language": "ko",
        })

    tasks = [asyncio.create_task(process_item(item)) for item in links]
    try:
        await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=remaining)
    except asyncio.TimeoutError:
        logger.warning("네이버 뉴스 크롤링 시간 초과 - 부분 결과 %d건 반환", len(results))
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        logger.error(f"Naver 뉴스 수집 오류: {e}")

    return results
