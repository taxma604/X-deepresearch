from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_x_service
from app.models.common import PageData, SuccessResponse
from app.models.tweet import Tweet
from app.services.x_service import XService

router = APIRouter(prefix="/api/v1/x", tags=["search"])


@router.get("/search", response_model=SuccessResponse[PageData[Tweet]])
async def search(
    q: Annotated[str, Query(min_length=1, max_length=512)],
    service: Annotated[XService, Depends(get_x_service)],
    product: Literal["Latest", "Top"] = "Latest",
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
):
    data = await service.search(query=q, product=product, limit=limit, cursor=cursor)
    return SuccessResponse[PageData[Tweet]](data=data)
