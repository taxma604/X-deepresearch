"""Conservative Git-history credential scan, not a substitute for Gitleaks/TruffleHog."""
from __future__ import annotations

import re
import subprocess
import sys

PATTERNS = {
    "github-token": re.compile(rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{60,})"),
    "openai-token": re.compile(rb"sk-(?:proj-)?[A-Za-z0-9_-]{30,}"),
    "aws-access-key": re.compile(rb"(?:AKIA|ASIA)[A-Z0-9]{16}"),
    "private-key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "x-session-cookie": re.compile(
        rb"(?:TWIKIT_AUTH_TOKEN|auth_token)[\x22\x27\s]*[:=][\x22\x27\s]*[a-fA-F0-9]{35,}"
    ),
    "x-csrf-cookie": re.compile(
        rb"(?:TWIKIT_CT0|ct0)[\x22\x27\s]*[:=][\x22\x27\s]*[a-fA-F0-9]{35,}"
    ),
}


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], stderr=subprocess.DEVNULL)


def main() -> int:
    seen: set[str] = set()
    findings: list[tuple[str, str]] = []
    for line in git("rev-list", "--objects", "--all").decode("utf-8").splitlines():
        object_id, _, path = line.partition(" ")
        if not path or object_id in seen:
            continue
        seen.add(object_id)
        if git("cat-file", "-t", object_id).strip() != b"blob":
            continue
        size = int(git("cat-file", "-s", object_id))
        if size > 1_000_000:
            continue
        data = git("cat-file", "-p", object_id)
        for name, pattern in PATTERNS.items():
            if pattern.search(data):
                findings.append((path, name))
    for path, kind in findings:
        print(f"Possible secret ({kind}) in historical blob at {path}.")
    print(f"Inspected {len(seen)} Git objects; {len(findings)} potential findings.")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
