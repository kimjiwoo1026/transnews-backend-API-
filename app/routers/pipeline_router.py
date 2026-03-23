import logging

from fastapi import APIRouter, HTTPException, Query

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
    logger.info("뉴스 요약 파이프라인 요청 - url=%s", url)

    content = await crawler_service.crawl_article(url)

    if not content:
        logger.warning("파이프라인 본문 추출 실패 - url=%s", url)
        raise HTTPException(status_code=400, detail="기사 본문 추출 실패")

    summary = await llm_proxy_service.summarize(content)

    logger.info(
        "뉴스 요약 파이프라인 성공 - url=%s, content_length=%d, summary_length=%d",
        url,
        len(content),
        len(summary),
    )

    return BaseResponse(
        status="SUCCESS",
        message="뉴스 요약 파이프라인 성공",
        data={
            "url": url,
            "content": content,
            "summary": summary,
        },
    )