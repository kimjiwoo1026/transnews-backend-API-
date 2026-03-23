import logging
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import crawl_router, news_router, pipeline_router
from app.schemas.models import BaseResponse

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="News search, crawling, and LLM proxy pipeline API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info("Request started - %s %s", request.method, request.url.path)

    try:
        response = await call_next(request)
        duration = round(time.time() - start_time, 4)
        logger.info(
            "Request completed - %s %s | status=%s | duration=%ss",
            request.method,
            request.url.path,
            response.status_code,
            duration,
        )
        return response
    except Exception as e:
        duration = round(time.time() - start_time, 4)
        logger.exception(
            "Request failed - %s %s | duration=%ss | error=%s",
            request.method,
            request.url.path,
            duration,
            str(e),
        )
        raise


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(
        "HTTP exception - %s %s | status=%s | detail=%s",
        request.method,
        request.url.path,
        exc.status_code,
        exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=BaseResponse(
            status="FAILURE",
            message=str(exc.detail),
            data=None,
        ).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(
        "Validation error - %s %s | detail=%s",
        request.method,
        request.url.path,
        exc.errors(),
    )
    return JSONResponse(
        status_code=422,
        content=BaseResponse(
            status="FAILURE",
            message="요청 데이터가 올바르지 않습니다.",
            data=exc.errors(),
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server error - %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=BaseResponse(
            status="FAILURE",
            message="서버 내부 오류가 발생했습니다.",
            data=None,
        ).model_dump(),
    )


app.include_router(news_router.router, prefix="/api/v1")
app.include_router(crawl_router.router, prefix="/api/v1")
app.include_router(pipeline_router.router, prefix="/api/v1")


@app.get("/", response_model=BaseResponse)
async def root():
    return BaseResponse(
        status="SUCCESS",
        message="TransNews backend server is running",
        data=None,
    )


@app.get("/health", response_model=BaseResponse)
async def health_check():
    return BaseResponse(
        status="SUCCESS",
        message="Server is healthy",
        data=None,
    )