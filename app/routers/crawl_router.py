from fastapi import APIRouter, HTTPException, Query
from app.schemas.models import BaseResponse
from app.services.crawler_service import CrawlerService

router = APIRouter(prefix="", tags=["crawl"])
crawler_service = CrawlerService()

@router.get("/crawl", response_model=BaseResponse)
async def crawl_article(url: str = Query(..., description="크롤링할 기사 URL")):
    result = await crawler_service.crawl_article(url)

    if result is None:
        raise HTTPException(status_code=400, detail="기사 본문을 가져오지 못했습니다.")

    return BaseResponse(
        status="SUCCESS",
        message="기사 크롤링 성공",
        data=result,
    )