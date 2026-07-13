import asyncio
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote

import feedparser
from googlenewsdecoder import gnewsdecoder

from app.services.crawler_service import crawler_service

logger = logging.getLogger(__name__)

NEWS_SOURCE_TIMEOUT = 16.0


def decode_google_news_url(google_url: str) -> str:
    try:
        decoded = gnewsdecoder(google_url)
        if isinstance(decoded, dict):
            return decoded.get("decoded_url") or decoded.get("url") or google_url
        return google_url
    except Exception:
        return google_url


def _clamp_limit(limit: int | None) -> int:
    try:
        value = int(limit or 10)
    except (TypeError, ValueError):
        value = 10
    return max(1, min(value, 1000))


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


async def get_news(
    keyword: str,
    *,
    limit: int = 10,
    published_after: str | None = None,
    published_before: str | None = None,
    timeout_seconds: float = NEWS_SOURCE_TIMEOUT,
) -> list[dict]:
    cleaned_keyword = keyword.strip()
    if not cleaned_keyword:
        return []

    max_items = _clamp_limit(limit)
    start_at = _parse_datetime(published_after)
    end_at = _parse_datetime(published_before)
    rss_url = f"https://news.google.com/rss/search?q={quote(cleaned_keyword)}&hl=ko&gl=KR&ceid=KR:ko"

    semaphore = asyncio.Semaphore(15)
    results: list[dict] = []

    try:
        feed = await asyncio.to_thread(feedparser.parse, rss_url)
        entries = list(feed.entries)[:max_items]

        async def process_entry(entry):
            entry_published = getattr(entry, "published", "")
            if not _in_window(entry_published, start_at, end_at):
                return

            google_link = getattr(entry, "link", "")
            async with semaphore:
                article_link = await asyncio.to_thread(decode_google_news_url, google_link)
                crawled = await crawler_service.crawl_article(article_link)
            source_info = getattr(entry, "source", {}) or {}
            source_name = source_info.get("title") if isinstance(source_info, dict) else "Unknown"
            published = (crawled.get("published_at") if crawled else None) or entry_published

            if not _in_window(published, start_at, end_at):
                return

            results.append({
                "title": getattr(entry, "title", ""),
                "link": google_link,
                "article_link": article_link,
                "original_url": article_link,
                "source_name": (crawled.get("source_name") if crawled else None) or source_name,
                "source_url": source_info.get("href") if isinstance(source_info, dict) else None,
                "published": published,
                "content": (crawled.get("content") if crawled else "") or "",
                "language": "ko",
            })

        tasks = [asyncio.create_task(process_entry(e)) for e in entries]
        try:
            await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            logger.warning("구글 뉴스 수집 시간 초과 - 부분 결과 %d건 반환", len(results))
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

        return results
    except Exception as e:
        logger.error(f"Error: {e}")
        return results


async def get_news_stats(keyword: str) -> dict:
    cleaned_keyword = keyword.strip()
    if not cleaned_keyword:
        return {"total_count": 0, "min_count": 0, "max_count": 0}

    rss_url = f"https://news.google.com/rss/search?q={quote(cleaned_keyword)}&hl=ko&gl=KR&ceid=KR:ko"

    feed = await asyncio.to_thread(feedparser.parse, rss_url)
    total = len(feed.entries)

    return {
        "keyword": cleaned_keyword,
        "total_count": total,
        "min_count": min(10, total),
        "max_count": total,
    }
