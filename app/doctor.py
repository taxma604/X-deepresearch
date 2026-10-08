"""Offline doctor command; never prints session values or sends X requests."""
from __future__ import annotations

import sys

from app.config import Settings
from app.x.auth import cookies_file_path, require_cookie_credentials
from app.x.exceptions import AuthConfigurationError


def main() -> None:
    settings = Settings()
    print(f"X-deepresearch | Python {sys.version_info.major}.{sys.version_info.minor}")
    try:
        require_cookie_credentials(settings)
    except AuthConfigurationError:
        print("Session: not configured (run x-deepresearch-auth init)")
    else:
        print("Session: configured (secrets hidden)")
    print(f"Local session path: {cookies_file_path(settings)}")
    print(f"Job DB: {settings.job_db_path or 'disabled (opt in with X_RESEARCH_JOB_DB)'}")
    print("Live X connectivity: not tested (doctor is offline).")


if __name__ == "__main__":
    main()
