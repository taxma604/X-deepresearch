"""Interactive single-command setup of local X session and Codex stdio MCP.

This command never sends the user's credentials to the author or shared hosting.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import warnings
from getpass import GetPassWarning, getpass

from app.config import Settings
from app.local_settings import config_directory, outside_git, store_private_json
from app.x.auth import cookies_file_path, store_cookie_credentials

DEFAULT_SOURCE = "git+https://github.com/taxma604/X-deepresearch"
SERVER_NAME = "x-deepresearch"


def hidden_input(prompt: str) -> str:
    """Abort before getpass can fall back to visible input."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", GetPassWarning)
        try:
            return getpass(prompt)
        except (GetPassWarning, EOFError) as exc:
            raise SystemExit("Hidden input is unavailable; use a supported private terminal.") from exc


def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-command setup for a private, local X-deepresearch MCP client."
    )
    parser.add_argument(
        "--source", default=DEFAULT_SOURCE,
        help="Git source for subsequent MCP launches.",
    )
    parser.add_argument(
        "--client", choices=["codex", "none"], default="codex",
        help="Register with Codex, or configure session only.",
    )
    args = parser.parse_args()

    if args.client == "codex" and shutil.which("codex") is None:
        parser.error("Codex CLI not found. Install Codex first, or pass --client none.")

    print("X-deepresearch: local-only setup.")
    print("Unofficial access may be restricted by X's Terms. Use only where permitted.")
    try:
        path = outside_git(cookies_file_path(Settings()))
        settings_path = outside_git(config_directory() / "settings.json")
    except ValueError as exc:
        parser.error(str(exc))
    if path.exists():
        confirm = input("Overwrite the existing local X session? [y/N] ").strip().lower()
        if confirm != "y":
            print("Existing session kept; no changes made.")
            return

    token = hidden_input("Your own X auth_token (hidden): ")
    csrf = hidden_input("Your own X ct0 (hidden): ")
    # Both fields are validated before anything is overwritten.
    if not token.strip() or not csrf.strip():
        parser.error("Both X session fields are required.")

    global_answer = input("Allow unrestricted X search from this local MCP? [y/N] ")
    unrestricted = global_answer.strip().lower() == "y"
    handles = ""
    if not unrestricted:
        handles = input("Allowed X account handles (comma-separated, without @): ").strip()
        if not handles:
            parser.error("Enter at least one handle, or explicitly allow global search.")
        names = [name.strip().removeprefix("@") for name in handles.split(",")]
        if not all(re.fullmatch(r"[A-Za-z0-9_]{1,15}", name) for name in names):
            parser.error("Invalid allowlisted X handles.")
        handles = ",".join(names)

    store_cookie_credentials(path, token, csrf)
    store_private_json(settings_path, {
        "allow_arbitrary_search": unrestricted, "allowed_users": handles,
    })
    print("Your X session was saved locally with restricted file permissions.")

    if args.client == "codex":
        command = [
            "codex", "mcp", "add", SERVER_NAME,
            "--env", f"TWIKIT_COOKIES_FILE={path}",
            "--env", f"X_DEEPRESEARCH_CONFIG_DIR={config_directory()}",
            "--", "uvx", "--from", args.source, SERVER_NAME,
        ]
        try:
            subprocess.run(command, check=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            print("Codex registration failed. Your local X session remains saved.")
            raise SystemExit(1) from exc
        print("Codex MCP configured. Start a new Codex session to use it.")
    else:
        print("Local session configured. Register the MCP executable in your chosen client.")


if __name__ == "__main__":
    main()
