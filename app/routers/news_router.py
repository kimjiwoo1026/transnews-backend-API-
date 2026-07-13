import asyncio
import logging
from fastapi import APIRouter, HTTPException, Query
from app.config import settings
from app.schemas.models import BaseResponse
from app.services.rss_service import get_news as get_google_news, get_news_stats
from app.services.naver_service import get_news as get_naver_news

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/news", tags=["News"])


def _dedupe_key(item: dict) -> str:
    title = (item.get("title") or "").replace(" ", "").lower()
    return f"{item.get('original_url')}|{title[:30]}"


def _clamp_timeout(value: float | None) -> float:
    if value is None:
        return settings.NEWS_SOURCE_TIMEOUT
    if value <= 0:
        return settings.MAX_NEWS_TIMEOUT_SECONDS
    return min(value, settings.MAX_NEWS_TIMEOUT_SECONDS)


@router.get("", response_model=BaseResponse)
async def search_news(
    keyword: str = Query(..., min_length=1, description="뉴스 검색 키워드"),
    limit: int = Query(100, ge=1, le=1000, description="최대 수집 개수(소스별)"),
    published_after: str | None = Query(None, description="검색 시작 일시 ISO 문자열"),
    published_before: str | None = Query(None, description="검색 종료 일시 ISO 문자열"),
    timeout_seconds: float | None = Query(None, ge=0, description="소스별 처리 시간 제한(초), 최대 60초로 제한됨"),
    include_empty_content: bool = Query(False, description="본문 추출 실패한 기사도 제목/URL만 포함할지 여부"),
):
    try:
        effective_timeout = _clamp_timeout(timeout_seconds)
        google_results, naver_results = await asyncio.gather(
            get_google_news(
                keyword,
                limit=limit,
                published_after=published_after,
                published_before=published_before,
                timeout_seconds=effective_timeout,
            ),
            get_naver_news(
                keyword,
                limit=limit,
                published_after=published_after,
                published_before=published_before,
                timeout_seconds=effective_timeout,
            ),
        )

        merged: list[dict] = []
        seen: set[str] = set()
        for item in [*google_results, *naver_results]:
            if not item.get("content") and not include_empty_content:
                continue
            key = _dedupe_key(item)
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)

        return BaseResponse(status="SUCCESS", message="뉴스 검색 성공", data=merged)
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
