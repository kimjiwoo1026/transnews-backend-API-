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
            return decoded.get("decoded_url") or decoded.get("url") or google_url
        return google_url
    except Exception:
        return google_url

async def get_news(keyword: str) -> list[dict]:
    cleaned_keyword = keyword.strip()
    if not cleaned_keyword:
        return []

    rss_url = f"https://news.google.com/rss/search?q={quote(cleaned_keyword)}&hl=ko&gl=KR&ceid=KR:ko"
    crawler = CrawlerService()
    
    try:
        feed = feedparser.parse(rss_url)

        async def process_entry(entry):
            google_link = getattr(entry, "link", "")
            article_link = decode_google_news_url(google_link)
            crawled = await crawler.crawl_article(article_link)
            
            source_info = getattr(entry, "source", {}) or {}
            source_name = source_info.get("title") if isinstance(source_info, dict) else "알 수 없음"
            
            return {
                "title": getattr(entry, "title", ""),
                "link": google_link,
                "article_link": article_link,
                "original_url": article_link,
                "source_name": source_name,
                "source_url": source_info.get("href") if isinstance(source_info, dict) else None,
                "published": getattr(entry, "published", ""),
                "content": crawled["content"] if crawled else ""
            }

        results = await asyncio.gather(*[process_entry(e) for e in feed.entries[:10]])
        return results
    except Exception as e:
        logger.error(f"Error: {e}")
        return []