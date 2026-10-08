from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any

from app.config import Settings
from app.local_settings import config_directory, store_private_json

from .exceptions import AuthConfigurationError


def _cookie_value(value: Any) -> str | None:
    if isinstance(value, dict) and "value" in value:
        value = value["value"]
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def parse_cookies_json(raw: str) -> dict[str, str]:
    """Parse a cookie mapping or browser-export cookie list without logging values."""

    try:
        payload = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise AuthConfigurationError("TWIKIT_COOKIES_JSON must contain valid cookie JSON.") from error

    if isinstance(payload, dict) and isinstance(payload.get("cookies"), list):
        payload = payload["cookies"]

    cookies: dict[str, str] = {}
    if isinstance(payload, dict):
        for name, value in payload.items():
            parsed = _cookie_value(value)
            if parsed is not None:
                cookies[str(name)] = parsed
    elif isinstance(payload, list):
        for item in payload:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            value = _cookie_value(item.get("value"))
            if name and value is not None:
                cookies[str(name)] = value
    else:
        raise AuthConfigurationError("TWIKIT_COOKIES_JSON must be a cookie object or list.")

    if not cookies.get("auth_token") or not cookies.get("ct0"):
        raise AuthConfigurationError("TWIKIT_COOKIES_JSON must contain auth_token and ct0.")
    return cookies


def cookies_file_path(settings: Settings) -> Path:
    if settings.twikit_cookies_file:
        return Path(settings.twikit_cookies_file).expanduser()
    return config_directory() / "cookies.json"


def store_cookie_credentials(path: Path, auth_token: str, ct0: str) -> None:
    """Atomic local session storage, using owner-only POSIX permissions."""
    if not auth_token.strip() or not ct0.strip():
        raise ValueError("Both auth_token and ct0 are required.")
    store_private_json(path, {"auth_token": auth_token.strip(), "ct0": ct0.strip()})


def _cookies_from_file(path: Path) -> dict[str, str]:
    if not path.is_file() or path.is_symlink():
        raise AuthConfigurationError("Set browser cookies or initialize a local cookie file.")
    if os.name == "posix" and stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise AuthConfigurationError("Cookie file permissions must be owner-only (chmod 600).")
    try:
        return parse_cookies_json(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise AuthConfigurationError("Unable to read the local cookie file.") from exc


def require_cookie_credentials(settings: Settings) -> dict[str, str]:
    """Return browser-session cookies without exposing their values."""

    if settings.twikit_cookies_json and settings.twikit_cookies_json.strip():
        return parse_cookies_json(settings.twikit_cookies_json)

    auth_token = (settings.twikit_auth_token or "").strip()
    ct0 = (settings.twikit_ct0 or "").strip()
    if auth_token and ct0:
        return {"auth_token": auth_token, "ct0": ct0}
    if auth_token or ct0:
        raise AuthConfigurationError("Set both TWIKIT_AUTH_TOKEN and TWIKIT_CT0.")
    return _cookies_from_file(cookies_file_path(settings))
