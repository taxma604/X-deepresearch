import json
import os

import pytest

from app.config import Settings
from app.x.auth import require_cookie_credentials, store_cookie_credentials
from app.x.exceptions import AuthConfigurationError


def test_local_cookie_file_round_trip(tmp_path, monkeypatch):
    for key in ("TWIKIT_AUTH_TOKEN", "TWIKIT_CT0", "TWIKIT_COOKIES_JSON"):
        monkeypatch.delenv(key, raising=False)
    path = tmp_path / "own" / "cookies.json"
    store_cookie_credentials(path, "test-token", "test-ct0")
    settings = Settings(_env_file=None, TWIKIT_COOKIES_FILE=str(path))
    assert require_cookie_credentials(settings) == {"auth_token": "test-token", "ct0": "test-ct0"}
    assert json.loads(path.read_text(encoding="utf-8"))["ct0"] == "test-ct0"
    if os.name == "posix":
        assert path.stat().st_mode & 0o077 == 0


def test_world_readable_cookie_file_fails_closed(tmp_path):
    if os.name != "posix":
        pytest.skip("POSIX file permissions only")
    path = tmp_path / "cookies.json"
    path.write_text('{"auth_token":"test-token","ct0":"test-ct0"}', encoding="utf-8")
    path.chmod(0o644)
    with pytest.raises(AuthConfigurationError, match="owner-only"):
        require_cookie_credentials(Settings(_env_file=None, TWIKIT_COOKIES_FILE=str(path)))


def test_blank_credentials_rejected(tmp_path):
    with pytest.raises(ValueError):
        store_cookie_credentials(tmp_path / "cookies.json", "", "ct0")


def test_custom_cookie_file_does_not_chmod_parent(tmp_path):
    if os.name != "posix":
        pytest.skip("POSIX permissions")
    directory = tmp_path / "already-created"
    directory.mkdir(mode=0o755)
    directory.chmod(0o755)
    store_cookie_credentials(directory / "cookies.json", "token", "ct0")
    assert directory.stat().st_mode & 0o777 == 0o755
