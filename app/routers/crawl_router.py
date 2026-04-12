import asyncio
import logging
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class CrawlerService:
    def __init__(self) -> None:
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

    async def crawl_article(self, url: str, retries: int = 3) -> dict | None:
        domain = urlparse(url).netloc
        
        for attempt in range(1, retries + 1):
            try:
                logger.info("Crawling attempt %s/%s: %s", attempt, retries, url)

                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    response = await client.get(url, headers=self.headers)
                    response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")

                title_tag = soup.find("title")
                title = title_tag.get_text(strip=True) if title_tag else "제목 없음"

                article = (
                    soup.find("article")
                    or soup.find("div", id="articleBodyContents")
                    or soup.find("div", class_="article_body")
                    or soup.find("div", class_="newsct_article")
                    or soup.find("div", id="newsct_article")
                    or soup.find("div", class_="article-view-content-div")
                    or soup.find("div", id="harmonyContainer")
                )

                if article is None:
                    continue

                for s in article(["script", "style", "iframe", "ins"]):
                    s.decompose()

                content = article.get_text("\n", strip=True)

                if len(content) >= 100:
                    return {
                        "title": title,
                        "content": content,
                        "domain": domain
                    }

            except Exception as e:
                logger.warning("Attempt %s failed: %s", attempt, str(e))

            if attempt < retries:
                await asyncio.sleep(1)

        return None