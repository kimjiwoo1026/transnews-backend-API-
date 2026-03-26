import asyncio
import logging
import re
from urllib.parse import urlparse

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
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,*/*;q=0.8"
            ),
        }
        self.client = httpx.AsyncClient(
            timeout=settings.REQUEST_TIMEOUT,
            follow_redirects=True,
            headers=self.headers,
        )

    async def close(self) -> None:
        await self.client.aclose()

    def _clean_text(self, text: str) -> str:
        text = re.sub(
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            "",
            text,
        )
        text = re.sub(r"무단\s*전재\s*및\s*재배포\s*금지", "", text)
        text = re.sub(r"저작권자\s*\(c\).*", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    async def crawl_article(self, url: str, retries: int = 3) -> dict | None:
        domain = urlparse(url).netloc

        for attempt in range(1, retries + 1):
            try:
                logger.info("크롤링 시도 %s/%s - url=%s", attempt, retries, url)

                response = await self.client.get(url)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")

                title_tag = soup.find("title")
                title = title_tag.get_text(strip=True) if title_tag else ""

                article_box = (
                    soup.find("article")
                    or soup.find("div", id=re.compile(r"articleBody|newsct_article|articeBody"))
                    or soup.find("div", class_=re.compile(r"article_body|view-content"))
                    or soup.find("div", class_="article-view-content-div")
                )

                paragraphs = article_box.find_all("p") if article_box else soup.find_all("p")

                raw_content = " ".join(
                    p.get_text(" ", strip=True)
                    for p in paragraphs
                    if p.get_text(strip=True)
                )
                clean_content = self._clean_text(raw_content)

                if len(clean_content) >= 100:
                    logger.info("크롤링 성공 - url=%s, length=%d", url, len(clean_content))
                    return {
                        "url": url,
                        "domain": domain,
                        "title": title,
                        "content": clean_content,
                    }

                logger.warning("본문 길이 부족 - url=%s, length=%d", url, len(clean_content))

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