from __future__ import annotations

from pydantic import BaseModel


class UserProfile(BaseModel):
    id: str | None = None
    username: str | None = None
    display_name: str | None = None
    description: str | None = None
    followers: int | None = None
    following: int | None = None
    verified: bool | None = None
    is_blue_verified: bool | None = None
    profile_url: str | None = None
