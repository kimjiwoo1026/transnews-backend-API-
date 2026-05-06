import logging
import httpx
from app.config import settings
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
            response = await client.post(f"{settings.MAIN_SERVER_URL}/api/v1/crawl-runs", json=payload, timeout=10.0)
            
            if response.status_code == 409:
                return BaseResponse(status="SUCCESS", message="이미 존재하는 데이터입니다.", data=payload)
            
            response.raise_for_status()
            return BaseResponse(status="SUCCESS", message="성공", data=payload)
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                return BaseResponse(status="SUCCESS", message="이미 존재함", data=payload)
            raise HTTPException(status_code=e.response.status_code, detail=f"전송 실패: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"전송 실패: {str(e)}")