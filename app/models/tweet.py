from __future__ import annotations

from pydantic import BaseModel, Field

from .user import UserProfile


class MediaItem(BaseModel):
    id: str | None = None
    type: str | None = None
    url: str | None = None
    display_url: str | None = None


class ResearchAuthor(BaseModel):
    id: str | None = None
    name: str | None = None
    screen_name: str | None = None


class ResearchMetrics(BaseModel):
    likes: int | None = None
    reposts: int | None = None
    replies: int | None = None
    quotes: int | None = None
    views: int | None = None
    bookmarks: int | None = None


class ResearchTweet(BaseModel):
    id: str | None = None
    url: str | None = None
    created_at: str | None = None
    text: str | None = None
    lang: str | None = None
    author: ResearchAuthor = Field(default_factory=ResearchAuthor)
    metrics: ResearchMetrics = Field(default_factory=ResearchMetrics)
    is_reply: bool = False
    is_quote: bool = False
    is_repost: bool = False


class Tweet(BaseModel):
    id: str | None = None
    text: str | None = None
    created_at: str | None = None
    lang: str | None = None
    user: UserProfile | None = None
    reply_count: int | None = None
    retweet_count: int | None = None
    like_count: int | None = None
    quote_count: int | None = None
    view_count: int | None = None
    bookmark_count: int | None = None
    is_reply: bool = False
    is_quote: bool = False
    is_repost: bool = False
    url: str | None = None
    media: list[MediaItem] = Field(default_factory=list)
    quoted_tweet: Tweet | None = None


Tweet.model_rebuild()
