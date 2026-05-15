import logging
from fastapi import APIRouter, HTTPException, Query
from app.schemas.models import BaseResponse
from app.services.rss_service import get_news, get_news_stats

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/news", tags=["News"])

@router.get("", response_model=BaseResponse)
async def search_news(
    keyword: str = Query(..., min_length=1, description="뉴스 검색 키워드"),
):
    try:
        news_list = await get_news(keyword)
        return BaseResponse(status="SUCCESS", message="뉴스 검색 성공", data=news_list)
    except Exception as e:
        logger.exception("News search failed")
        raise HTTPException(status_code=500, detail=f"뉴스 검색 실패: {str(e)}")

@router.get("/stats", response_model=BaseResponse)
async def search_news_stats(
    keyword: str = Query(..., min_length=1, description="뉴스 검색 키워드"),
):
    try:
        stats = await get_news_stats(keyword)
        return BaseResponse(status="SUCCESS", message="검색 통계 조회 성공", data=stats)
    except Exception as e:
        logger.exception("News stats failed")
        raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")