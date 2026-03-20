from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from loguru import logger

from app.api.routes import router
from app.logging import configure_logging


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    logger.info("Application startup")
    yield
    logger.info("Application shutdown")


app = FastAPI(title="Payment And Order Service", lifespan=lifespan)
app.include_router(router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info("{} {} started", request.method, request.url.path)
    response = await call_next(request)
    logger.info("{} {} -> {}", request.method, request.url.path, response.status_code)
    return response
