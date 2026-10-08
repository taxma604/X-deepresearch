from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import compat, health, search, tweets, users
from app.mcp_server import mcp, mcp_http_app
from app.models.common import ErrorDetail, ErrorResponse
from app.security import RequireHTTPBearer
from app.x.exceptions import XApiError


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with mcp.session_manager.run():
        from app.api.dependencies import get_x_service
        from app.mcp_server import daily_stats_jobs

        await daily_stats_jobs.resume_pending(get_x_service())
        yield


app = FastAPI(
    title="X-deepresearch",
    description="Read-only research endpoints backed by a user's X browser session.",
    version="0.3.0",
    lifespan=lifespan,
)
app.add_middleware(RequireHTTPBearer)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://chatgpt.com", "https://chat.openai.com"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
)
app.include_router(health.router)
app.include_router(users.router)
app.include_router(search.router)
app.include_router(tweets.router)
app.include_router(compat.router)


@app.get("/", tags=["service"])
async def service_info() -> dict[str, object]:
    return {
        "name": "x-deepresearch",
        "service": "x-deepresearch",
        "status": "ok",
        "read_only": True,
        "endpoints": ["/health", "/search", "/user/{screen_name}/tweets", "/mcp"],
    }


@app.exception_handler(XApiError)
async def x_api_error_handler(_: Request, error: XApiError) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=error.code, message=error.message))
    headers = {}
    if error.status_code == 429 and error.retry_after is not None:
        headers["Retry-After"] = str(int(error.retry_after))
    return JSONResponse(
        status_code=error.status_code,
        content=body.model_dump(),
        headers=headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, __: RequestValidationError) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorDetail(
            code="invalid_request",
            message="The request parameters are invalid.",
        )
    )
    return JSONResponse(status_code=422, content=body.model_dump())


@app.exception_handler(Exception)
async def unexpected_error_handler(_: Request, __: Exception) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code="internal_error", message="Internal server error."))
    return JSONResponse(status_code=500, content=body.model_dump())


# Keep this catch-all mount last so the REST routes above remain reachable.
app.mount("/", mcp_http_app)
