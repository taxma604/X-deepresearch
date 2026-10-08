"""Offline coverage for the optional Codex local bootstrap."""
import sys

import pytest

from app import setup_cli


def test_one_command_registration_does_not_expose_cookies(monkeypatch, tmp_path):
    from app.x import auth

    path = tmp_path / "session.json"
    monkeypatch.setattr(setup_cli, "cookies_file_path", lambda settings: path)
    monkeypatch.setattr(setup_cli.shutil, "which", lambda app: "/usr/bin/codex")
    secrets = iter(["secret-token", "secret-ct0"])
    monkeypatch.setattr(setup_cli, "getpass", lambda _: next(secrets))
    monkeypatch.setattr("builtins.input", lambda question: "y")
    monkeypatch.setattr(sys, "argv", ["x-deepresearch-setup", "--source", "git+https://host/repo@v1"])
    commands = []
    monkeypatch.setattr(setup_cli.subprocess, "run", lambda command, check: commands.append(command))
    setup_cli.main()
    assert auth.parse_cookies_json(path.read_text()) == {
        "auth_token": "secret-token", "ct0": "secret-ct0",
    }
    assert len(commands) == 1
    assert any(item.startswith("X_DEEPRESEARCH_CONFIG_DIR=") for item in commands[0])
    assert any(item.startswith("TWIKIT_COOKIES_FILE=") for item in commands[0])
    assert "git+https://host/repo@v1" in commands[0]
    assert "secret-token" not in repr(commands)
    assert "secret-ct0" not in repr(commands)


def test_setup_without_codex_keeps_credentials_local(monkeypatch, tmp_path):
    monkeypatch.setattr(setup_cli, "cookies_file_path", lambda settings: tmp_path / "session.json")
    secrets = iter(["secret-token", "secret-ct0"])
    monkeypatch.setattr(setup_cli, "getpass", lambda _: next(secrets))
    monkeypatch.setattr("builtins.input", lambda question: "n" if "unrestricted" in question else "alice")
    monkeypatch.setattr(sys, "argv", ["x-deepresearch-setup", "--client", "none"])
    monkeypatch.setattr(setup_cli.subprocess, "run", lambda command, check: pytest.fail("subprocess unexpected"))
    setup_cli.main()
    assert (tmp_path / "session.json").is_file()


def test_empty_credentials_do_not_replace_existing_session(monkeypatch, tmp_path):
    path = tmp_path / "session.json"
    path.write_text("old")
    monkeypatch.setattr(setup_cli, "cookies_file_path", lambda settings: path)
    monkeypatch.setattr(setup_cli.shutil, "which", lambda app: "/usr/bin/codex")
    secrets = iter(["", "ct0"])
    monkeypatch.setattr(setup_cli, "getpass", lambda _: next(secrets))
    monkeypatch.setattr("builtins.input", lambda question: "y")
    monkeypatch.setattr(sys, "argv", ["x-deepresearch-setup"])
    with pytest.raises(SystemExit):
        setup_cli.main()
    assert path.read_text() == "old"
