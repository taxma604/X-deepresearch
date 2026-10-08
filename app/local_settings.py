"""Local configuration stored outside Git; no session values in settings."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def config_directory() -> Path:
    return Path(os.environ.get(
        "X_DEEPRESEARCH_CONFIG_DIR", str(Path.home() / ".config" / "x-deepresearch")
    )).expanduser().resolve()


def local_search_settings() -> dict[str, Any]:
    path = config_directory() / "settings.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {key: data[key] for key in ("allow_arbitrary_search", "allowed_users") if key in data}


def outside_git(path: Path) -> Path:
    path = path.expanduser().resolve()
    if any((parent / ".git").exists() for parent in path.parents):
        raise ValueError("Choose a local configuration path outside Git repositories.")
    return path


def store_private_json(path: Path, data: dict[str, Any]) -> None:
    path = outside_git(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".x-deepresearch-")
    try:
        if os.name == "posix":
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file)
            file.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
