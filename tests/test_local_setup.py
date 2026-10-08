import json
import os
import sys
import warnings
from getpass import GetPassWarning

import pytest

from app import setup_cli
from app.config import Settings
from app.x.auth import cookies_file_path


def configure(monkeypatch, client="none", handles="alice,bob_2", unrestricted=False):
    monkeypatch.setattr(sys, "argv", ["x-deepresearch-setup", "--client", client])
    values = iter(["test-session", "test-csrf"])
    monkeypatch.setattr(setup_cli, "getpass", lambda _: next(values))
    answers = iter(["y" if unrestricted else "n", handles])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr(setup_cli.shutil, "which", lambda _: "/usr/bin/codex")


def test_client_none_persists_policy(monkeypatch):
    configure(monkeypatch)
    setup_cli.main()
    settings = Settings(_env_file=None)
    assert settings.allowed_users == "alice,bob_2"
    assert settings.allow_arbitrary_search is False
    directory = cookies_file_path(settings).parent
    assert json.loads((directory / "settings.json").read_text()) == {
        "allow_arbitrary_search": False, "allowed_users": "alice,bob_2",
    }
    if os.name == "posix":
        assert directory.stat().st_mode & 0o777 == 0o700
        for name in ("cookies.json", "settings.json"):
            assert (directory / name).stat().st_mode & 0o777 == 0o600


def test_environment_overrides_saved_policy(monkeypatch):
    configure(monkeypatch, unrestricted=True)
    setup_cli.main()
    assert Settings(_env_file=None).allow_arbitrary_search is True
    monkeypatch.setenv("ALLOW_ARBITRARY_SEARCH", "false")
    monkeypatch.setenv("ALLOWED_USERS", "carol")
    settings = Settings(_env_file=None)
    assert settings.allow_arbitrary_search is False
    assert settings.allowed_users == "carol"


@pytest.mark.parametrize("handles", ["", "alice,", ",alice", "alice,,bob", "日本語", "álîce", "a b", "a-b", "a" * 16, "@@alice"])
def test_setup_rejects_invalid_allowlist_before_writing(monkeypatch, handles):
    configure(monkeypatch, handles=handles)
    with pytest.raises(SystemExit):
        setup_cli.main()
    assert not cookies_file_path(Settings(_env_file=None)).exists()


def test_setup_normalizes_handles(monkeypatch):
    configure(monkeypatch, handles=" @Alice , bob_2 ")
    setup_cli.main()
    assert Settings(_env_file=None).allowed_users == "Alice,bob_2"


def test_setup_rejects_getpass_fallback_without_reading_plaintext(monkeypatch):
    configure(monkeypatch)

    def fallback(_):
        warnings.warn("Cannot control echo on the terminal.", GetPassWarning)
        pytest.fail("plaintext fallback must not execute")

    monkeypatch.setattr(setup_cli, "getpass", fallback)
    with pytest.raises(SystemExit):
        setup_cli.main()
    assert not cookies_file_path(Settings(_env_file=None)).exists()


def test_custom_cookie_and_config_paths_reach_codex_without_values(monkeypatch, tmp_path):
    path = tmp_path / "custom" / "session.json"
    monkeypatch.setenv("TWIKIT_COOKIES_FILE", str(path))
    configure(monkeypatch, client="codex", unrestricted=True)
    commands = []
    monkeypatch.setattr(setup_cli.subprocess, "run", lambda command, check: commands.append(command))
    setup_cli.main()
    command = commands[0]
    assert command[:4] == ["codex", "mcp", "add", "x-deepresearch"]
    assert f"TWIKIT_COOKIES_FILE={path}" in command
    assert f"X_DEEPRESEARCH_CONFIG_DIR={os.environ['X_DEEPRESEARCH_CONFIG_DIR']}" in command
    assert "test-session" not in repr(command)
    assert "test-csrf" not in repr(command)
    assert command[-3:] == ["--from", "git+https://github.com/taxma604/X-deepresearch", "x-deepresearch"]


def test_default_sqlite_is_disabled():
    assert Settings(_env_file=None).job_db_path is None


def test_session_path_inside_git_is_rejected(monkeypatch, tmp_path):
    repository = tmp_path / "checkout"
    repository.mkdir()
    (repository / ".git").mkdir()
    monkeypatch.setenv("TWIKIT_COOKIES_FILE", str(repository / "session.json"))
    configure(monkeypatch)
    with pytest.raises(SystemExit):
        setup_cli.main()
    assert not (repository / "session.json").exists()
