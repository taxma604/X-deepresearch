from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.api.dependencies import get_x_service
from app.models.common import PageData, SuccessResponse
from app.models.tweet import Tweet
from app.models.user import UserProfile
from app.services.x_service import XService

router = APIRouter(prefix="/api/v1/x", tags=["users"])


@router.get("/user/{username}", response_model=SuccessResponse[UserProfile])
async def get_user(
    username: Annotated[str, Path(min_length=1, max_length=15)],
    service: Annotated[XService, Depends(get_x_service)],
):
    data = await service.user_profile(username)
    return SuccessResponse[UserProfile](data=data)


@router.get("/user/{username}/tweets", response_model=SuccessResponse[PageData[Tweet]])
async def get_user_tweets(
    username: Annotated[str, Path(min_length=1, max_length=15)],
    service: Annotated[XService, Depends(get_x_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 40,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
    include_replies: bool = False,
):
    data = await service.user_tweets(
        username,
        limit=limit,
        cursor=cursor,
        include_replies=include_replies,
    )
    return SuccessResponse[PageData[Tweet]](data=data)
