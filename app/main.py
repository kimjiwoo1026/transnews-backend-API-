import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import news_router, pipeline_router, crawl_router, social_router
from app.services.crawler_service import crawler_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await crawler_service.close()

app = FastAPI(
    title="TransNews Backend API",
    version="1.0.0",
    description="News search, crawling, and LLM proxy pipeline API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(news_router.router, prefix="/api/v1")
app.include_router(pipeline_router.router, prefix="/api/v1")
app.include_router(crawl_router.router, prefix="/api/v1")
app.include_router(social_router.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "status": "SUCCESS",
        "message": "TransNews backend server is running",
        "data": None,
    }
