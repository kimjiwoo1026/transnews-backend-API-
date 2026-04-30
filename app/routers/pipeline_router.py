import logging
import httpx
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from app.services.crawler_service import CrawlerService
from app.schemas.models import BaseResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipeline", tags=["Pipeline"])
crawler_service = CrawlerService()

@router.post("/news-summary", response_model=BaseResponse)
async def news_summary_pipeline(url: str = Query(..., description="기사 원문 URL")):
    article_dict = await crawler_service.crawl_article(url)

    if not article_dict:
        raise HTTPException(status_code=400, detail="기사 본문 추출 실패")

    actual_url = article_dict.get("url")

    async with httpx.AsyncClient() as client:
        payload = {
            "title": article_dict.get("title"),
            "content": article_dict.get("content"),
            "summary": "AI 요약 생성 중...",
            "original_url": actual_url,
            "url": actual_url,
            "source": article_dict.get("domain"),
            "language": "ko",
            "published_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        }
        
        try:
            await client.post("http://localhost:8001/api/v1/crawl-runs", json=payload, timeout=10.0)
            return BaseResponse(status="SUCCESS", message="성공", data=payload)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"전송 실패: {str(e)}")