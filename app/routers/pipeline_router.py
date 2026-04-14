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

    if isinstance(article_dict, str) or not article_dict or not article_dict.get("content"):
        logger.warning("파이프라인 데이터 추출 실패 - url=%s", url)
        raise HTTPException(status_code=400, detail="기사 본문 추출 실패")

    async with httpx.AsyncClient(follow_redirects=True) as client:
        target_url = "http://localhost:8001/api/v1/crawl-runs"
        
        payload = {
            "title": article_dict.get("title") or "제목 정보 없음",
            "content": article_dict.get("content") or "본문 내용 없음",
            "summary": "AI 요약 생성 중...", 
            "original_url": str(url),
            "url": str(url),
            "source": article_dict.get("domain") or "news",
            "language": "ko",
            "published_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        }
        
        try:
            response = await client.post(target_url, json=payload, timeout=10.0)
            
            if response.status_code not in [200, 201, 202]:
                logger.error("메인 서버 전송 실패: %s", response.text)
                raise HTTPException(
                    status_code=500, 
                    detail=f"메인 서버(8001) 응답 에러: {response.status_code}"
                )
                
        except httpx.ConnectError:
            logger.error("메인 서버(8001) 연결 불가")
            raise HTTPException(status_code=503, detail="메인 서버(8001) 연결 불가")
        except Exception as e:
            logger.error("기타 연결 오류: %s", str(e))
            raise HTTPException(status_code=500, detail=f"연결 오류 발생: {str(e)}")

    logger.info("뉴스 수집 및 메인 서버 전송 성공 - url=%s", url)

    return BaseResponse(
        status="SUCCESS",
        message="데이터 수집 및 메인 서버(8001) 적재 완료 (Status: 202 Accepted)",
        data=payload
    )