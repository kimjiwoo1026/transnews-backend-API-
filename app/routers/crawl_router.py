from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl

from app.schemas.models import BaseResponse
from app.services.crawler_service import CrawlerService

router = APIRouter(prefix="/crawl", tags=["crawl"])

crawler_service = CrawlerService()


class CrawlRequest(BaseModel):
    url: HttpUrl


@router.post("", response_model=BaseResponse)
async def crawl_article(request: CrawlRequest):
    result = await crawler_service.crawl_article(str(request.url))

    if result is None:
        raise HTTPException(status_code=400, detail="기사 본문을 가져오지 못했습니다.")

    return BaseResponse(
        status="SUCCESS",
        message="기사 크롤링 성공",
        data=result,
    )