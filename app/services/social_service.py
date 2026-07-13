import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote

import feedparser
import httpx

logger = logging.getLogger(__name__)

SOCIAL_SOURCES = [
    {"source": "x", "query": "site:x.com OR site:twitter.com"},
    {"source": "instagram", "query": "site:instagram.com"},
    {"source": "youtube", "query": "site:youtube.com OR site:youtu.be"},
    {"source": "reddit", "query": "site:reddit.com"},
    {"source": "community", "query": "site:theqoo.net OR site:instiz.net OR site:dcinside.com"},
]

POSITIVE_HINTS = ["좋", "추천", "만족", "기대", "인기", "화제", "성공", "positive", "love", "best"]
NEGATIVE_HINTS = ["논란", "불매", "비판", "실망", "문제", "위기", "부정", "negative", "hate", "worst"]




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

def _count_hints(text: str, hints: list[str]) -> int:
    lowered = text.lower()
    return sum(1 for hint in hints if hint.lower() in lowered)


def _iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _entry_datetime(entry) -> datetime | None:
    published = getattr(entry, "published", None) or getattr(entry, "updated", None)
    if not published:
        return None
    try:
        parsed = parsedate_to_datetime(published)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _empty_source(source: str, *, method: str, reason: str, limit: int) -> dict:
    return {
        "source": source,
        "mention_count": 0,
        "positive_hint_count": 0,
        "negative_hint_count": 0,
        "samples": [],
        "is_capped": False,
        "max_sample_size": limit,
        "metric_label": "post_count",
        "method": method,
        "status": "unavailable",
        "reason": reason,
    }


async def _fetch_youtube_official(keyword: str, start_at: datetime, end_at: datetime, limit: int) -> dict | None:
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        return None

    params = {
        "part": "snippet",
        "q": keyword,
        "type": "video",
        "order": "date",
        "publishedAfter": _iso_z(start_at),
        "publishedBefore": _iso_z(end_at),
        "maxResults": min(limit, 50),
        "key": api_key,
    }
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get("https://www.googleapis.com/youtube/v3/search", params=params)
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        logger.warning("youtube official stats failed keyword=%s: %s", keyword, exc)
        return _empty_source("youtube", method="youtube_data_api_search_list", reason=str(exc), limit=limit)

    samples = []
    positive = 0
    negative = 0
    for item in payload.get("items", []):
        snippet = item.get("snippet", {})
        title = snippet.get("title", "")
        description = snippet.get("description", "")
        text = f"{title} {description}"
        positive += _count_hints(text, POSITIVE_HINTS)
        negative += _count_hints(text, NEGATIVE_HINTS)
        samples.append({
            "title": title,
            "url": f"https://www.youtube.com/watch?v={item.get('id', {}).get('videoId', '')}",
            "published": snippet.get("publishedAt", ""),
        })

    return {
        "source": "youtube",
        "mention_count": int(payload.get("pageInfo", {}).get("totalResults") or len(samples)),
        "positive_hint_count": positive,
        "negative_hint_count": negative,
        "samples": samples[:5],
        "is_capped": bool(payload.get("nextPageToken")),
        "max_sample_size": limit,
        "metric_label": "official_recent_video_count",
        "method": "youtube_data_api_search_list",
        "status": "official",
    }


async def _fetch_x_official(keyword: str, start_at: datetime, end_at: datetime, limit: int) -> dict | None:
    bearer_token = os.getenv("X_BEARER_TOKEN") or os.getenv("TWITTER_BEARER_TOKEN")
    if not bearer_token:
        return None

    params = {
        "query": keyword,
        "start_time": _iso_z(start_at),
        "end_time": _iso_z(end_at),
        "granularity": "hour",
    }
    headers = {"Authorization": f"Bearer {bearer_token}"}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get("https://api.x.com/2/tweets/counts/recent", params=params, headers=headers)
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        logger.warning("x official stats failed keyword=%s: %s", keyword, exc)
        return _empty_source("x", method="x_recent_counts", reason=str(exc), limit=limit)

    total = payload.get("meta", {}).get("total_tweet_count")
    if total is None:
        total = sum(int(item.get("tweet_count") or 0) for item in payload.get("data", []))
    return {
        "source": "x",
        "mention_count": int(total or 0),
        "positive_hint_count": 0,
        "negative_hint_count": 0,
        "samples": [],
        "is_capped": False,
        "max_sample_size": limit,
        "metric_label": "official_recent_post_count",
        "method": "x_recent_counts",
        "status": "official",
    }


async def _fetch_public_source(keyword: str, source: dict, start_at: datetime, end_at: datetime, limit: int) -> dict:
    query = f'{keyword} ({source["query"]})'
    rss_url = f"https://news.google.com/rss/search?q={quote(query)}&hl=ko&gl=KR&ceid=KR:ko"
    try:
        feed = await asyncio.to_thread(feedparser.parse, rss_url)
        all_entries = list(feed.entries)
        entries = []
        for entry in all_entries:
            published_at = _entry_datetime(entry)
            if published_at and start_at <= published_at <= end_at:
                entries.append(entry)
            if len(entries) >= limit:
                break
    except Exception as exc:
        logger.warning("social public source failed source=%s keyword=%s: %s", source["source"], keyword, exc)
        all_entries = []
        entries = []

    positive = 0
    negative = 0
    samples = []
    for entry in entries:
        title = getattr(entry, "title", "") or ""
        summary = getattr(entry, "summary", "") or ""
        text = f"{title} {summary}"
        positive += _count_hints(text, POSITIVE_HINTS)
        negative += _count_hints(text, NEGATIVE_HINTS)
        if len(samples) < 5:
            samples.append({
                "title": title,
                "url": getattr(entry, "link", ""),
                "published": getattr(entry, "published", ""),
            })

    return {
        "source": source["source"],
        "mention_count": len(entries),
        "positive_hint_count": positive,
        "negative_hint_count": negative,
        "samples": samples,
        "is_capped": len(entries) >= limit,
        "max_sample_size": limit,
        "metric_label": "public_search_sample_count",
        "method": "google_news_rss_site_query",
        "status": "estimate",
    }


async def get_social_stats(
    keyword: str,
    limit: int = 30,
    hours: int = 24,
    window_start: str | None = None,
    window_end: str | None = None,
) -> dict:
    cleaned_keyword = keyword.strip()
    now = datetime.now(timezone.utc)
    requested_start = _parse_datetime(window_start)
    requested_end = _parse_datetime(window_end)
    if requested_start and requested_end and requested_start < requested_end:
        start_at = requested_start
        end_at = requested_end
    else:
        window_hours = max(1, min(int(hours or 24), 168))
        end_at = now
        start_at = now - timedelta(hours=window_hours)
    max_items = max(1, min(int(limit or 30), 100))

    if not cleaned_keyword:
        return {
            "keyword": keyword,
            "total_count": 0,
            "sources": [],
            "sampled_at": end_at.isoformat(),
            "window_start": start_at.isoformat(),
            "window_end": end_at.isoformat(),
            "method": "mixed_official_or_public_estimate",
            "metric_label": "post_count_or_public_search_sample_count",
            "disclaimer": "Official APIs are used only when credentials are configured. Otherwise this returns dated public-search samples, not true platform-wide search volume.",
        }

    public_source_map = {item["source"]: item for item in SOCIAL_SOURCES}
    official_youtube, official_x = await asyncio.gather(
        _fetch_youtube_official(cleaned_keyword, start_at, end_at, max_items),
        _fetch_x_official(cleaned_keyword, start_at, end_at, max_items),
    )

    tasks = []
    for source in SOCIAL_SOURCES:
        if source["source"] == "youtube" and official_youtube is not None:
            continue
        if source["source"] == "x" and official_x is not None:
            continue
        tasks.append(_fetch_public_source(cleaned_keyword, source, start_at, now, max_items))

    fallback_sources = await asyncio.gather(*tasks)
    sources = []
    if official_x is not None:
        sources.append(official_x)
    if official_youtube is not None:
        sources.append(official_youtube)
    sources.extend(fallback_sources)

    source_order = {source["source"]: index for index, source in enumerate(SOCIAL_SOURCES)}
    sources.sort(key=lambda item: source_order.get(item["source"], 999))
    total = sum(item["mention_count"] for item in sources)
    return {
        "keyword": cleaned_keyword,
        "total_count": total,
        "sources": sources,
        "sampled_at": end_at.isoformat(),
        "window_start": start_at.isoformat(),
        "window_end": end_at.isoformat(),
        "method": "mixed_official_or_public_estimate",
        "metric_label": "post_count_or_public_search_sample_count",
        "disclaimer": "Official APIs are used for YouTube/X only when credentials are configured. Instagram and other unsupported sources are dated public-search samples, not true platform-wide search volume.",
    }
