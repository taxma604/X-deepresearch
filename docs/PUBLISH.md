# Maintainer publication checklist

This is a **maintainer-only handoff**, not an instruction to make the repository public automatically.

## GitHub repository About

These are the intended values for the repository metadata. They must be set through GitHub Settings or a sufficiently authorized GitHub CLI/token; editing this file does not change the About panel.

**Description**

> Read-only X research for AI agents: search posts, track trends, compare topics, and inspect coverage.

**Topics**

`mcp`, `mcp-server`, `ai-agents`, `twitter`, `x`, `research`, `python`, `twikit`, `social-media-analytics`

**Website:** leave blank until there is a real documentation site. **Social preview:** optional, only after making an accurate project image.

## Publication sequence

1. Check [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md). In particular, **do not infer data-source distribution permission from the MIT license**; resolve the platform-terms question before publicly distributing this Twikit integration.
2. Verify `main` has a clean history and no secrets or private data, and all GitHub Actions checks pass.
3. Set About description/topics, then change visibility from Private to Public using an authorized GitHub admin account.
4. Verify anonymous visitors can view README, README.ja.md, LICENSE and setup documentation, and install from GitHub without GitHub credentials.
5. **After** the repository is Public and review is complete, create and push a signed-off annotated tag `v0.3.0` on the final `main` commit. Do not reuse a tag or tag a different version from `pyproject.toml`.
6. The [release workflow](../.github/workflows/release.yml) validates the version/tag, runs tests, builds wheel and sdist, checks installation, and creates a GitHub Release with [English release notes](releases/v0.3.0.md).
7. Confirm the [Releases](https://github.com/taxma604/X-deepresearch/releases) page shows `v0.3.0` and its two distribution files. If the workflow fails, fix the cause and rerun it; **do not assume the Release was published**.
8. Link the [Japanese release notes](releases/v0.3.0.ja.md) in the README or release description if needed. The project is **not** published to PyPI.

Once the tag exists, the stable version can be installed with:

```bash
uvx --from git+https://github.com/taxma604/X-deepresearch@v0.3.0 x-deepresearch-setup
```

**Do not change** the unrelated private development repository, existing Render service, or real local X cookie configuration.
