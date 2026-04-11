#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


ASSIGN_RE = re.compile(r"^([A-Z0-9_]+):=(.*)$")
SOURCE_URL_RE = re.compile(
    r"^PKG_SOURCE_URL:=https://codeload\.github\.com/\$\(([^)]+)\)/\$\(([^)]+)\)/tar\.gz/([^?]+)\?$"
)
RESOLVED_COMMENT_RE = re.compile(
    r"^# (?P<tag>.+) tag resolves to commit (?P<commit>[0-9a-f]{40})\.$"
)


@dataclass
class PackageContext:
    makefile_path: Path
    package_path: str
    owner: str
    repo: str
    source_ref_template: str
    current_text: str
    current_lines: list[str]


@dataclass
class BumpResult:
    updated_text: str
    resolved_tag: str
    resolved_commit: str
    pkg_hash: str
    commit_message: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bump an OpenWrt package Makefile backed by GitHub codeload."
    )
    parser.add_argument("package", help="Package path such as net/veex")
    parser.add_argument("version", help="Target version such as 0.4.3")
    parser.add_argument(
        "--tag-prefix",
        default="v",
        help="Prefix added before the version when resolving the upstream tag (default: v)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the diff but do not write the Makefile",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Create the git commit after writing the Makefile",
    )
    args = parser.parse_args()
    if args.dry_run and args.commit:
        parser.error("--dry-run and --commit cannot be used together")
    return args


def repo_root() -> Path:
    output = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(output.stdout.strip())


def load_package_context(root: Path, package_path: str) -> PackageContext:
    makefile_path = root / package_path / "Makefile"
    if not makefile_path.is_file():
        raise SystemExit(f"Missing package Makefile: {makefile_path}")

    current_text = makefile_path.read_text(encoding="utf-8")
    current_lines = current_text.splitlines()
    variables: dict[str, str] = {}
    source_url_line = None

    for line in current_lines:
        match = ASSIGN_RE.match(line)
        if match:
            variables[match.group(1)] = match.group(2)
        if line.startswith("PKG_SOURCE_URL:="):
            source_url_line = line

    if source_url_line is None:
        raise SystemExit("Could not find PKG_SOURCE_URL in Makefile")

    source_match = SOURCE_URL_RE.match(source_url_line)
    if source_match is None:
        raise SystemExit(
            "Unsupported PKG_SOURCE_URL. This script only supports GitHub codeload release tarballs."
        )

    owner_expr, repo_expr, source_ref_template = source_match.groups()
    owner = resolve_make_expr(owner_expr, variables)
    repo = resolve_make_expr(repo_expr, variables)

    return PackageContext(
        makefile_path=makefile_path,
        package_path=package_path,
        owner=owner,
        repo=repo,
        source_ref_template=source_ref_template,
        current_text=current_text,
        current_lines=current_lines,
    )


def resolve_make_expr(expr: str, variables: dict[str, str]) -> str:
    if expr.startswith("$(") and expr.endswith(")"):
        expr = expr[2:-1]
    if expr not in variables:
        raise SystemExit(f"Could not resolve Makefile variable: {expr}")
    return variables[expr]


def github_json(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "openwrt-foundry-bump-skill",
        },
    )
    try:
        with urllib.request.urlopen(request) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"GitHub API request failed: {exc.code} {url}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"GitHub API request failed: {exc.reason}") from exc


def resolve_commit(owner: str, repo: str, tag: str) -> str:
    url = (
        f"https://api.github.com/repos/{urllib.parse.quote(owner)}/"
        f"{urllib.parse.quote(repo)}/commits/{urllib.parse.quote(tag)}"
    )
    payload = github_json(url)
    sha = payload.get("sha")
    if not isinstance(sha, str) or len(sha) != 40:
        raise SystemExit(f"GitHub API did not return a commit SHA for tag {tag}")
    return sha


def sha256_from_url(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "openwrt-foundry-bump-skill"},
    )
    digest = hashlib.sha256()
    try:
        with urllib.request.urlopen(request) as response:
            while True:
                chunk = response.read(1024 * 64)
                if not chunk:
                    break
                digest.update(chunk)
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Tarball download failed: {exc.code} {url}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Tarball download failed: {exc.reason}") from exc
    return digest.hexdigest()


def build_bump_result(context: PackageContext, version: str, tag_prefix: str) -> BumpResult:
    resolved_tag = f"{tag_prefix}{version}"
    resolved_commit = resolve_commit(context.owner, context.repo, resolved_tag)
    pkg_hash = sha256_from_url(
        f"https://codeload.github.com/{context.owner}/{context.repo}/tar.gz/{resolved_tag}"
    )

    updated_lines = list(context.current_lines)
    version_index = find_line_index(updated_lines, "PKG_VERSION:=")
    hash_index = find_line_index(updated_lines, "PKG_HASH:=")
    comment_index = find_resolved_comment_index(updated_lines)

    updated_lines[version_index] = f"PKG_VERSION:={version}"
    updated_lines[hash_index] = f"PKG_HASH:={pkg_hash}"
    updated_lines[comment_index] = (
        f"# {resolved_tag} tag resolves to commit {resolved_commit}."
    )

    updated_text = "\n".join(updated_lines) + "\n"
    commit_message = f"{context.package_path}: bump to {version}"

    return BumpResult(
        updated_text=updated_text,
        resolved_tag=resolved_tag,
        resolved_commit=resolved_commit,
        pkg_hash=pkg_hash,
        commit_message=commit_message,
    )


def find_line_index(lines: list[str], prefix: str) -> int:
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            return index
    raise SystemExit(f"Could not find required Makefile line: {prefix}")


def find_resolved_comment_index(lines: list[str]) -> int:
    for index, line in enumerate(lines):
        if RESOLVED_COMMENT_RE.match(line):
            return index
    raise SystemExit("Could not find upstream resolved-commit comment in Makefile")


def print_diff(path: Path, before: str, after: str) -> None:
    diff = difflib.unified_diff(
        before.splitlines(),
        after.splitlines(),
        fromfile=f"a/{path.as_posix()}",
        tofile=f"b/{path.as_posix()}",
        lineterm="",
    )
    for line in diff:
        print(line)


def create_commit(package_makefile: Path, commit_message: str) -> None:
    subprocess.run(
        [
            "git",
            "commit",
            "-m",
            commit_message,
            "--only",
            "--",
            package_makefile.as_posix(),
        ],
        check=True,
    )


def main() -> int:
    args = parse_args()
    root = repo_root()
    context = load_package_context(root, args.package)
    result = build_bump_result(context, args.version, args.tag_prefix)

    print(f"Package: {context.package_path}")
    print(f"Resolved tag: {result.resolved_tag}")
    print(f"Resolved commit: {result.resolved_commit}")
    print(f"PKG_HASH: {result.pkg_hash}")
    print(f"Commit message: {result.commit_message}")

    if context.current_text == result.updated_text:
        print("No Makefile changes are required.")
        return 0

    print_diff(context.makefile_path.relative_to(root), context.current_text, result.updated_text)

    if args.dry_run:
        return 0

    context.makefile_path.write_text(result.updated_text, encoding="utf-8", newline="\n")
    print(f"Updated {context.makefile_path.relative_to(root)}")

    if args.commit:
        create_commit(context.makefile_path.relative_to(root), result.commit_message)
        print("Created git commit.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
