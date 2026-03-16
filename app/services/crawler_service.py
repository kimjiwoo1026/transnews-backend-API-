import asyncio
import logging

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class CrawlerService:
    def __init__(self) -> None:
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        }

    async def crawl_article(self, url: str, retries: int = 3) -> str | None:
        for attempt in range(1, retries + 1):
            try:
                logger.info("Crawling attempt %s/%s: %s", attempt, retries, url)

                async with httpx.AsyncClient(
                    timeout=10.0,
                    follow_redirects=True,
                ) as client:
                    response = await client.get(url, headers=self.headers)
                    response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")

                article = (
                    soup.find("article")
                    or soup.find("div", id="articleBodyContents")
                    or soup.find("div", class_="article_body")
                    or soup.find("div", class_="newsct_article")
                    or soup.find("div", class_="article-view-content-div")
                )

                if article is None:
                    logger.warning("Article container not found: %s", url)
                    continue

                paragraphs = article.find_all("p")
                content = " ".join(
                    p.get_text(" ", strip=True)
                    for p in paragraphs
                    if p.get_text(strip=True)
                ).strip()

                if len(content) >= 100:
                    return content

                logger.warning("Extracted content too short: %s", url)

            except Exception as e:
                logger.warning("Crawling failed on attempt %s: %s", attempt, str(e))

            if attempt < retries:
                await asyncio.sleep(1)

        logger.error("Final crawl failed: %s", url)
        return None