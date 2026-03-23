import logging

from fastapi import APIRouter, Query

from app.schemas.models import BaseResponse
from app.services.rss_service import get_news

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/news", tags=["News"])


@router.get("", response_model=BaseResponse)
async def search_news(
    keyword: str = Query(..., min_length=1, description="뉴스 검색 키워드"),
):
    logger.info("뉴스 검색 요청 - keyword=%s", keyword)

    news_list = await get_news(keyword)

    logger.info(
        "뉴스 검색 성공 - keyword=%s, count=%d",
        keyword,
        len(news_list) if news_list else 0,
    )

    return BaseResponse(
        status="SUCCESS",
        message="뉴스 검색 성공",
        data=news_list,
    )