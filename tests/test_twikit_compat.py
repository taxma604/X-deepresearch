import asyncio

from app.config import Settings
from app.x.client import _build_client


def test_twikit_client_imports_on_python312() -> None:
    client = _build_client(Settings())
    try:
        assert client.__class__.__name__ == "ResilientClient"
    finally:
        asyncio.run(client.http.aclose())
