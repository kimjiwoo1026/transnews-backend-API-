import logging

from fastapi import APIRouter, HTTPException, Query

from app.schemas.models import BaseResponse
from app.services.crawler_service import CrawlerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/crawl", tags=["Crawl"])

crawler_service = CrawlerService()


@router.get("", response_model=BaseResponse)
async def crawl_article(
    url: str = Query(..., description="크롤링할 기사 URL"),
):
    logger.info("기사 크롤링 요청 - url=%s", url)

    content = await crawler_service.crawl_article(url)

    if not content:
        logger.warning("기사 본문 추출 실패 - url=%s", url)
        raise HTTPException(status_code=400, detail="기사 본문 추출 실패")

    logger.info("기사 크롤링 성공 - url=%s, length=%d", url, len(content))

    return BaseResponse(
        status="SUCCESS",
        message="기사 크롤링 성공",
        data={
            "url": url,
            "content": content,
        },
    )