"""Fail-closed bearer access control for HTTP and mounted MCP.

Local stdio MCP is a separate process transport and does not expose an HTTP port.
"""
from __future__ import annotations

import hmac

from fastapi.responses import JSONResponse

from app.config import Settings


class RequireHTTPBearer:
    """Protect all data endpoints, including mounted MCP, with one deployment token."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if (scope.get("path") in {"/", "/health"} and scope.get("method") == "GET") or scope.get("method") == "OPTIONS":
            await self.app(scope, receive, send)
            return

        token = Settings().http_access_token
        if token is None or len(token) < 32:
            response = JSONResponse(
                {"error": {"code": "http_auth_not_configured",
                           "message": "HTTP access is disabled until a secure access token is configured."}},
                status_code=503,
            )
        else:
            authorization = dict(scope.get("headers", [])).get(b"authorization", b"")
            prefix = b"Bearer "
            valid = authorization.startswith(prefix) and hmac.compare_digest(
                authorization[len(prefix):], token.encode("utf-8")
            )
            response = None if valid else JSONResponse(
                {"error": {"code": "unauthorized", "message": "Bearer token required."}},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )

        if response is not None:
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)
