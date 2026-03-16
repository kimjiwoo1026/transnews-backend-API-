import logging

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.schemas.models import BaseResponse
from app.services.crawler_service import CrawlerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/crawl", tags=["Crawl"])

crawler_service = CrawlerService()


@router.get("", response_model=BaseResponse)
async def crawl_article(
    url: str = Query(..., description="크롤링할 기사 URL"),
):
    try:
        content = await crawler_service.crawl_article(url)

        if not content:
            return JSONResponse(
                status_code=400,
                content=BaseResponse(
                    status="FAILURE",
                    message="기사 본문 추출 실패",
                    data=None,
                ).model_dump(),
            )

        return BaseResponse(
            status="SUCCESS",
            message="기사 크롤링 성공",
            data={
                "url": url,
                "content": content,
            },
        )

    except Exception as e:
        logger.exception("Crawl failed")
        return JSONResponse(
            status_code=500,
            content=BaseResponse(
                status="FAILURE",
                message=f"크롤링 실패: {str(e)}",
                data=None,
            ).model_dump(),
        )