# Security

Do not post session cookies, tokens, HARs, account databases or private data in GitHub issues, PRs or logs. Report vulnerabilities privately using GitHub private vulnerability reporting when enabled.

- A copied X cookie is a credential. Revoke compromised sessions immediately.
- Hosted HTTP requires a strong X_RESEARCH_ACCESS_TOKEN; limit network access and use TLS.
- The same hosted service uses one owner's X session: do not operate it as a shared public proxy.
- Stdio stores credentials under the user's home directory, outside Git.
- Results may be incomplete; do not interpret coverage_complete as global completeness.
- Do not bypass platform access controls or evade rate limits.

See DISCLAIMER.md for platform terms, permission and licensing risks.

On Windows, file mode bits alone do not enforce NTFS ACLs: verify that the cookie directory and file are readable only by the intended Windows user, or use WSL with owner-only POSIX permissions. Do not upload cookie files to cloud drives.
