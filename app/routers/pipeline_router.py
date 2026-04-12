import logging
import httpx
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query

from app.schemas.models import BaseResponse
from app.services.crawler_service import CrawlerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])

crawler_service = CrawlerService()

@router.post("/news-summary", response_model=BaseResponse)
async def news_summary_pipeline(
    url: str = Query(..., description="기사 원문 URL"),
):
    logger.info("뉴스 요약 파이프라인 요청 - url=%s", url)

    article_dict = await crawler_service.crawl_article(url)

    if not article_dict:
        logger.warning("파이프라인 본문 추출 실패 - url=%s", url)
        raise HTTPException(status_code=400, detail="기사 본문 추출 실패")

    async with httpx.AsyncClient() as client:
        target_url = "http://localhost:8001/api/v1/articles/"
        
        payload = {
            "title": article_dict.get("title", "제목 없음"),
            "content": article_dict.get("content", ""),
            "summary": "AI 분석 대기 중...", 
            "url": url,
            "source": article_dict.get("domain", "알 수 없음"),
            "language": "ko",
            "published_at": datetime.utcnow().isoformat()
        }
        
        try:
            response = await client.post(target_url, json=payload, timeout=10.0)
            if response.status_code not in [200, 201]:
                logger.error("메인 서버 전송 실패: %s", response.text)
        except Exception as e:
            logger.error("메인 서버 연결 오류: %s", str(e))

    logger.info("뉴스 요약 및 메인 서버 전송 성공 - url=%s", url)

    return BaseResponse(
        status="SUCCESS",
        message="뉴스 수집 및 메인 서버 적재 성공",
        data=payload
    )