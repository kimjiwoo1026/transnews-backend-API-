import logging
from urllib.parse import quote

import feedparser

logger = logging.getLogger(__name__)


async def get_news(keyword: str) -> list[dict[str, str]]:
    cleaned_keyword = keyword.strip()

    if not cleaned_keyword:
        logger.warning("빈 키워드로 뉴스 검색 요청이 들어왔습니다.")
        return []

    rss_url = (
        f"https://news.google.com/rss/search?q={quote(cleaned_keyword)}"
        f"&hl=ko&gl=KR&ceid=KR:ko"
    )

    logger.info("뉴스 RSS 검색 시작 - keyword=%s", cleaned_keyword)

    try:
        feed = feedparser.parse(rss_url)

        results = []
        for entry in feed.entries[:10]:
            results.append(
                {
                    "title": getattr(entry, "title", ""),
                    "link": getattr(entry, "link", ""),
                    "published": getattr(entry, "published", ""),
                }
            )

        logger.info("뉴스 RSS 검색 성공 - keyword=%s, count=%d", cleaned_keyword, len(results))
        return results

    except Exception:
        logger.exception("뉴스 RSS 검색 실패 - keyword=%s", cleaned_keyword)
        raise