---
name: openwrt-package-bump
description: Use for this repository when asked to bump an OpenWrt package under a path like `net/veex` to a new release version and produce a commit message. Supports GitHub codeload packages whose Makefile uses `PKG_SOURCE_URL:=https://codeload.github.com/.../tar.gz/v$(PKG_VERSION)?`.
---

# OpenWrt Package Bump

Use this skill only inside this repository.

## Quick Start

1. Confirm the target package path is `category/name` and contains a `Makefile`.
2. Run:

```bash
python3 .agents/skills/openwrt-package-bump/scripts/bump_github_codeload_package.py net/veex 0.4.3
```

3. Review the diff.
4. If the bump is correct, either rerun with `--commit` or commit manually:

```bash
git commit -m 'net/veex: bump to 0.4.3' -- net/veex/Makefile
```

## What The Script Updates

- `PKG_VERSION`
- `PKG_HASH`
- The `# v... tag resolves to commit ...` comment above `PKG_SOURCE`

It resolves the upstream tag through the GitHub API and computes the tarball SHA256 from `codeload.github.com`.

## Recommended Usage

- Default tag format is `v<version>`.
- If upstream tags do not use `v`, pass `--tag-prefix ''`.
- Use `--dry-run` to preview the diff without writing the file.
- Use `--commit` only after checking the target package bump is self-contained.

## Limits

Do not use this skill when any of the following is true:

- The package is not sourced from GitHub codeload.
- The Makefile layout does not match the current repository pattern.
- The bump needs patch refreshes, build fixes, or extra file edits.
- The version is a snapshot or otherwise not a simple release tag bump.

In those cases, handle the bump manually and keep the commit message format consistent.

## Validation

- `git diff -- <package>/Makefile`
- `git show --stat HEAD -- <package>/Makefile`
- If needed, open the package `Makefile` and verify version, resolved commit comment, and hash agree with upstream.
