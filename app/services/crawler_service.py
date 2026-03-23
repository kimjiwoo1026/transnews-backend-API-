import asyncio
import logging

import httpx
from bs4 import BeautifulSoup

from app.config import settings

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
                logger.info("크롤링 시도 %s/%s - url=%s", attempt, retries, url)

                async with httpx.AsyncClient(
                    timeout=settings.REQUEST_TIMEOUT,
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
                    logger.warning("본문 영역 탐색 실패 - url=%s", url)
                    continue

                paragraphs = article.find_all("p")
                content = " ".join(
                    p.get_text(" ", strip=True)
                    for p in paragraphs
                    if p.get_text(strip=True)
                ).strip()

                if len(content) >= 100:
                    logger.info("크롤링 성공 - url=%s, length=%d", url, len(content))
                    return content

                logger.warning("본문 길이 부족 - url=%s, length=%d", url, len(content))

            except httpx.HTTPStatusError as e:
                logger.warning(
                    "HTTP 상태 오류 - attempt=%s, url=%s, status=%s",
                    attempt,
                    url,
                    e.response.status_code,
                )
            except httpx.RequestError as e:
                logger.warning(
                    "HTTP 요청 실패 - attempt=%s, url=%s, error=%s",
                    attempt,
                    url,
                    str(e),
                )
            except Exception as e:
                logger.exception(
                    "크롤링 중 예기치 못한 오류 - attempt=%s, url=%s, error=%s",
                    attempt,
                    url,
                    str(e),
                )

            if attempt < retries:
                await asyncio.sleep(1)

        logger.error("최종 크롤링 실패 - url=%s", url)
        return None