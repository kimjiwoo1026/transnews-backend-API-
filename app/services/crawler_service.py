import asyncio
import logging
import re
from urllib.parse import urlparse

import httpx
import trafilatura
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
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        }

        self.client = httpx.AsyncClient(
            timeout=settings.REQUEST_TIMEOUT,
            follow_redirects=True,
            headers=self.headers,
        )

    async def close(self) -> None:
        await self.client.aclose()

    def _clean_text(self, text: str) -> str:
        text = re.sub(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "", text)
        text = re.sub(r"무단\s*전재\s*및\s*재배포\s*금지", "", text)
        text = re.sub(r"저작권자\s*\(c\).*", "", text)
        text = re.sub(r"Copyright.*", "", text, flags=re.I)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _extract_title(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")

        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"].strip()

        title_tag = soup.find("title")
        if title_tag:
            return title_tag.get_text(strip=True)

        return "제목 없음"

    def _extract_content_with_bs4(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")

        article_box = (
            soup.find("article", id="dic_area")
            or soup.find("div", id="dic_area")
            or soup.find("article")
            or soup.find("div", id="newsct_article")
            or soup.find("div", id="articleBodyContents")
            or soup.find("div", id="harmonyContainer")
            or soup.find("section", class_=re.compile(r"article|news|content|view|body", re.I))
            or soup.find("div", id=re.compile(r"article|news|content|view|body", re.I))
            or soup.find("div", class_=re.compile(r"article|news|content|view|body", re.I))
        )

        if article_box:
            for tag in article_box(["script", "style", "iframe", "ins", "aside", "button"]):
                tag.decompose()

            return self._clean_text(article_box.get_text(" ", strip=True))

        paragraphs = soup.find_all("p")
        raw_content = " ".join(
            p.get_text(" ", strip=True)
            for p in paragraphs
            if p.get_text(strip=True)
        )

        return self._clean_text(raw_content)

    def _extract_content(self, html: str, url: str) -> str:
        content = trafilatura.extract(
            html,
            url=url,
            include_comments=False,
            include_tables=False,
            favor_recall=True,
        )

        if content:
            content = self._clean_text(content)

        if content and len(content) >= 100:
            return content

        return self._extract_content_with_bs4(html)

    async def crawl_article(self, url: str, retries: int = 3) -> dict | None:
        for attempt in range(1, retries + 1):
            try:
                logger.info("크롤링 시도 %s/%s - url=%s", attempt, retries, url)

                response = await self.client.get(url)
                response.raise_for_status()

                final_url = str(response.url)
                domain = urlparse(final_url).netloc
                html = response.text

                title = self._extract_title(html)
                content = self._extract_content(html, final_url)

                if len(content) >= 100:
                    logger.info("크롤링 성공 - url=%s, length=%d", final_url, len(content))

                    return {
                        "title": title,
                        "url": final_url,
                        "domain": domain,
                        "content": content,
                    }

                logger.warning("본문 길이 부족 - url=%s, length=%d", final_url, len(content))

            except Exception as e:
                logger.warning(
                    "크롤링 실패 - attempt=%s, url=%s, error=%s",
                    attempt,
                    url,
                    str(e),
                )

            if attempt < retries:
                await asyncio.sleep(1)

        logger.error("최종 크롤링 실패 - url=%s", url)
        return None