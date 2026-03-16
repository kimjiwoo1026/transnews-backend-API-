import logging

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.schemas.models import BaseResponse
from app.services.crawler_service import CrawlerService
from app.services.llm_proxy_service import LLMProxyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])

crawler_service = CrawlerService()
llm_proxy_service = LLMProxyService()


@router.post("/news-summary", response_model=BaseResponse)
async def news_summary_pipeline(
    url: str = Query(..., description="기사 원문 URL"),
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

        summary = await llm_proxy_service.summarize(content)

        return BaseResponse(
            status="SUCCESS",
            message="뉴스 요약 파이프라인 성공",
            data={
                "url": url,
                "content": content,
                "summary": summary,
            },
        )

    except Exception as e:
        logger.exception("Pipeline failed")
        return JSONResponse(
            status_code=500,
            content=BaseResponse(
                status="FAILURE",
                message=f"파이프라인 처리 실패: {str(e)}",
                data=None,
            ).model_dump(),
        )