import asyncio
import logging
from urllib.parse import quote

import feedparser
from googlenewsdecoder import gnewsdecoder

from app.services.crawler_service import CrawlerService

logger = logging.getLogger(__name__)


def decode_google_news_url(google_url: str) -> str:
    try:
        decoded = gnewsdecoder(google_url)

        if isinstance(decoded, dict):
            real_url = (
                decoded.get("decoded_url")
                or decoded.get("url")
                or decoded.get("source_url")
            )

            if real_url:
                logger.info("Google News URL 디코딩 성공 - %s -> %s", google_url, real_url)
                return real_url

        logger.warning("Google News URL 디코딩 결과 없음 - url=%s, result=%s", google_url, decoded)
        return google_url

    except Exception as e:
        logger.warning("Google News URL 디코딩 실패 - url=%s, error=%s", google_url, str(e))
        return google_url


async def get_news(keyword: str) -> list[dict]:
    cleaned_keyword = keyword.strip()

    if not cleaned_keyword:
        logger.warning("빈 키워드로 뉴스 검색 요청이 들어왔습니다.")
        return []

    rss_url = (
        f"https://news.google.com/rss/search?q={quote(cleaned_keyword)}"
        f"&hl=ko&gl=KR&ceid=KR:ko"
    )

    logger.info("뉴스 RSS 검색 시작 - keyword=%s", cleaned_keyword)

    crawler = CrawlerService()

    try:
        feed = feedparser.parse(rss_url)

        async def add_content(entry):
            google_link = getattr(entry, "link", "")
            article_link = decode_google_news_url(google_link)

            crawled = await crawler.crawl_article(article_link)

            source = getattr(entry, "source", {}) or {}

            return {
                "title": getattr(entry, "title", ""),
                "link": google_link,
                "article_link": crawled["url"] if crawled else article_link,
                "source_name": source.get("title") if isinstance(source, dict) else None,
                "source_url": source.get("href") if isinstance(source, dict) else None,
                "published": getattr(entry, "published", ""),
                "content": crawled["content"] if crawled else None,
            }

        results = await asyncio.gather(
            *[add_content(entry) for entry in feed.entries[:10]]
        )

        logger.info(
            "뉴스 RSS 검색 성공 - keyword=%s, count=%d",
            cleaned_keyword,
            len(results),
        )

        return results

    except Exception:
        logger.exception("뉴스 RSS 검색 실패 - keyword=%s", cleaned_keyword)
        raise

    finally:
        await crawler.close()