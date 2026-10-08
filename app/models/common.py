from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    ok: Literal[False] = False
    error: ErrorDetail


class SuccessResponse[T](BaseModel):
    ok: Literal[True] = True
    data: T


class PageData[T](BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[T]
    next_cursor: str | None = None
    has_more: bool = False
    pagination_complete: bool = True
    pagination_issue: str | None = None


class AnySuccessResponse(BaseModel):
    ok: Literal[True] = True
    data: Any
