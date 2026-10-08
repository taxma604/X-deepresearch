from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.api.dependencies import get_x_service
from app.models.common import SuccessResponse
from app.models.tweet import Tweet
from app.services.x_service import XService

router = APIRouter(prefix="/api/v1/x", tags=["tweets"])


@router.get("/tweet/{tweet_id}", response_model=SuccessResponse[Tweet])
async def get_tweet(
    tweet_id: Annotated[str, Path(min_length=1, max_length=32)],
    service: Annotated[XService, Depends(get_x_service)],
):
    data = await service.tweet_detail(tweet_id)
    return SuccessResponse[Tweet](data=data)
