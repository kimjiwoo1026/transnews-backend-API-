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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
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
        if not text: return ""

        cut_patterns = [
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            r"무단\s*전재\s*및\s*재배포\s*금지",
            r"저작권자\s*\(c\)",
            r"Copyright",
            r"ⓒ",
            r"이\s*기사를\s*추천합니다",
            r"재배포\s*금지",
            r"관련기사",
            r"구독신청",
            r"네이버\s*메인에서"
        ]
        
        for pattern in cut_patterns:
            match = re.search(pattern, text, flags=re.I)
            if match:
                text = text[:match.start()]

        text = re.sub(r"\[[가-힣\s]*기자\]", "", text)
        text = re.sub(r"\[[가-힣\s]*특파원\]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        
        return text

    def _extract_title(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"].strip()
        title_tag = soup.find("title")
        return title_tag.get_text(strip=True) if title_tag else "제목 없음"

    def _extract_content(self, html: str, url: str) -> str:
        content = trafilatura.extract(html, url=url, include_comments=False, include_tables=False, no_fallback=False)
        
        if not content or len(content) < 200:
            soup = BeautifulSoup(html, "html.parser")
            article_body = (
                soup.find("article") or 
                soup.find("div", id="dic_area") or 
                soup.find("div", id="articleBodyContents") or
                soup.find("div", class_="article_body") or
                soup.find("div", id="newsct_article")
            )
            if article_body:
                for s in article_body(["script", "style", "iframe", "button", "aside"]):
                    s.decompose()
                content = article_body.get_text(" ", strip=True)
            else:
                content = " ".join([p.get_text() for p in soup.find_all("p")])

        return self._clean_text(content)

    async def crawl_article(self, url: str, retries: int = 3) -> dict | None:
        for attempt in range(1, retries + 1):
            try:
                response = await self.client.get(url)
                response.raise_for_status()
                final_url = str(response.url)
                html = response.text
                
                content = self._extract_content(html, final_url)
                
                if len(content) > 30:
                    return {
                        "title": self._extract_title(html),
                        "url": final_url,
                        "domain": urlparse(final_url).netloc,
                        "content": content,
                    }
            except Exception:
                if attempt < retries: await asyncio.sleep(1)
        return None