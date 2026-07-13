import logging

from fastapi import APIRouter, HTTPException, Query

from app.schemas.models import BaseResponse
from app.services.social_service import get_social_stats

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/social", tags=["Social"])


@router.get("/stats", response_model=BaseResponse)
async def social_stats(
    keyword: str = Query(..., min_length=1, description="SNS 언급량 조회 키워드"),
    limit: int = Query(30, ge=1, le=100, description="플랫폼별 최대 샘플 수"),
    hours: int = Query(24, ge=1, le=168, description="조회 시간 범위. 기본값은 최근 24시간"),
    window_start: str | None = Query(None, description="조회 시작 일시 ISO 문자열"),
    window_end: str | None = Query(None, description="조회 종료 일시 ISO 문자열"),
):
    try:
        data = await get_social_stats(keyword, limit=limit, hours=hours, window_start=window_start, window_end=window_end)
        return BaseResponse(status="SUCCESS", message="SNS 언급량 조회 성공", data=data)
    except Exception as e:
        logger.exception("Social stats failed")
        raise HTTPException(status_code=500, detail=f"SNS 언급량 조회 실패: {str(e)}")
