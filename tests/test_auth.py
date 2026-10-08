import json

import pytest

from app.config import Settings
from app.x.auth import parse_cookies_json, require_cookie_credentials
from app.x.exceptions import AuthConfigurationError


def test_cookie_credentials_are_resolved_without_exposing_values() -> None:
    settings = Settings(_env_file=None, TWIKIT_AUTH_TOKEN="AUTH", TWIKIT_CT0="CT0")
    assert require_cookie_credentials(settings) == {
        "auth_token": "AUTH",
        "ct0": "CT0",
    }


def test_both_cookies_are_required() -> None:
    settings = Settings(_env_file=None, TWIKIT_AUTH_TOKEN="AUTH")
    with pytest.raises(AuthConfigurationError, match="both"):
        require_cookie_credentials(settings)


def test_cookie_json_accepts_a_mapping_and_preserves_extra_cookies() -> None:
    settings = Settings(
        _env_file=None,
        TWIKIT_COOKIES_JSON=json.dumps(
            {"auth_token": "test-auth-token", "ct0": "test-ct0", "guest_id": "test-guest"}
        ),
    )
    assert require_cookie_credentials(settings) == {
        "auth_token": "test-auth-token",
        "ct0": "test-ct0",
        "guest_id": "test-guest",
    }


def test_cookie_json_accepts_a_browser_cookie_list() -> None:
    parsed = parse_cookies_json(
        json.dumps(
            [
                {"name": "auth_token", "value": "test-auth-token"},
                {"name": "ct0", "value": "test-ct0"},
            ]
        )
    )
    assert set(parsed) == {"auth_token", "ct0"}
