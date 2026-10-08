from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query

from app.api.dependencies import get_x_service
from app.models.common import PageData, SuccessResponse
from app.models.tweet import ResearchTweet
from app.services.x_service import XService
from app.x.serializers import research_tweet_to_model

router = APIRouter(tags=["read-only research"])


def _research_page(
    raw_items,
    next_cursor: str | None,
    pagination_issue: str | None = None,
):
    items = [
        serialized
        for raw in raw_items
        if (serialized := research_tweet_to_model(raw)) is not None
    ]
    return PageData[ResearchTweet](
        items=items,
        next_cursor=next_cursor,
        has_more=bool(next_cursor),
        pagination_complete=not bool(next_cursor) and pagination_issue is None,
        pagination_issue=pagination_issue,
    )


@router.get("/search", response_model=SuccessResponse[PageData[ResearchTweet]])
async def compatibility_search(
    q: Annotated[str, Query(min_length=1, max_length=512)],
    service: Annotated[XService, Depends(get_x_service)],
    product: Literal["Latest", "Top"] = "Latest",
    pages: Annotated[int | None, Query(ge=1, le=500)] = None,
    limit: Annotated[int, Query(ge=1, le=10000)] = 100,
):
    raw_items, next_cursor, _, pagination_issue = await service.search_pages(
        query=q,
        product=product,
        pages=pages,
        limit=limit,
        page_size=service.settings.page_size,
    )
    return SuccessResponse[PageData[ResearchTweet]](
        data=_research_page(raw_items, next_cursor, pagination_issue)
    )


@router.get(
    "/user/{screen_name}/tweets",
    response_model=SuccessResponse[PageData[ResearchTweet]],
)
async def compatibility_user_tweets(
    screen_name: Annotated[str, Path(min_length=1, max_length=15)],
    service: Annotated[XService, Depends(get_x_service)],
    pages: Annotated[int, Query(ge=1, le=100)] = 1,
    limit: Annotated[int, Query(ge=1, le=10000)] = 20,
):
    raw_items, next_cursor, _ = await service.user_tweets_pages(
        screen_name,
        pages=pages,
        limit=limit,
        page_size=service.settings.page_size,
    )
    return SuccessResponse[PageData[ResearchTweet]](
        data=_research_page(raw_items, next_cursor)
    )
