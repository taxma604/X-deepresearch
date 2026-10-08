from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.services.x_service import XService
from app.x.client import XClient


@lru_cache(maxsize=1)
def get_x_service() -> XService:
    settings = get_settings()
    return XService(XClient(settings), settings)
