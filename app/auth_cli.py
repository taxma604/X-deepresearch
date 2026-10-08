"""Interactive local X cookie setup; secrets never appear in process arguments."""
from __future__ import annotations

import argparse

from app.config import Settings
from app.setup_cli import hidden_input
from app.x.auth import cookies_file_path, store_cookie_credentials


def main() -> None:
    parser = argparse.ArgumentParser(description="Store your own local X session.")
    parser.add_argument("command", choices=["init"])
    args = parser.parse_args()
    if args.command == "init":
        path = cookies_file_path(Settings())
        auth_token = hidden_input("X auth_token (hidden): ")
        ct0 = hidden_input("X ct0 (hidden): ")
        store_cookie_credentials(path, auth_token, ct0)
        print(f"Session saved locally at {path}")


if __name__ == "__main__":
    main()
