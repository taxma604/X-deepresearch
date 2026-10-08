from __future__ import annotations

import re

from app.config import Settings

_FROM_USER_RE = re.compile(
    r"(?<![A-Za-z0-9_])from:([A-Za-z0-9_]{1,15})(?![A-Za-z0-9_])",
    re.IGNORECASE,
)


def allowed_user_names(settings: Settings) -> frozenset[str]:
    return frozenset(
        name.lstrip("@").strip().casefold()
        for name in settings.allowed_users.split(",")
        if name.lstrip("@").strip()
    )


def search_query_is_allowed(query: str, settings: Settings) -> bool:
    if settings.allow_arbitrary_search:
        return True
    allowed = allowed_user_names(settings)
    # X search supports boolean OR and grouping. A single allowed "from:" token
    # does NOT constrain the full query if an OR branch can match anyone.
    # This allowlist is deliberately conservative; unrestricted research is an
    # explicit local setting (ALLOW_ARBITRARY_SEARCH=true).
    if re.search(r"\bOR\b|[|()]", query, re.IGNORECASE):
        return False
    if re.search(r"(?<![A-Za-z0-9_])-\s*from:", query, re.IGNORECASE):
        return False
    authors = _FROM_USER_RE.findall(query)
    return len(authors) == 1 and authors[0].casefold() in allowed
