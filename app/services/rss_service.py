from urllib.parse import quote

import feedparser


async def get_news(keyword: str) -> list[dict]:
    cleaned_keyword = keyword.strip()
    if not cleaned_keyword:
        return []

    rss_url = (
        f"https://news.google.com/rss/search?q={quote(cleaned_keyword)}"
        f"&hl=ko&gl=KR&ceid=KR:ko"
    )

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

    return results