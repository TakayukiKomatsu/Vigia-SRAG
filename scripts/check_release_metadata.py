"""Validate designated release metadata fields after documentation closeout."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

VERSION = "2.2"
DATE = "2026-07-29"
DEFAULT_PATHS = (
    ".agent/specs/02-epidemiological-metrics/spec.md",
    ".agent/specs/02-epidemiological-metrics/tasks.md",
    ".agent/specs/03-agentic-reporting/spec.md",
    ".agent/specs/03-agentic-reporting/tasks.md",
    ".agent/specs/04-governance-delivery/spec.md",
    ".agent/specs/04-governance-delivery/tasks.md",
    ".agent/specs/traceability.md",
    "README.md",
    "docs/architecture.html",
    "examples/live-smoke-result.json",
)
MARKDOWN_METADATA_RE = re.compile(
    r"\A(?:---\n(?P<frontmatter>.*?)\n---\n|(?P<blockquote>(?:> [^\n]*\n)+))", re.DOTALL
)


def _markdown_metadata(text: str) -> dict[str, str]:
    """Read only the leading frontmatter or leading blockquote metadata."""
    match = MARKDOWN_METADATA_RE.match(text)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in (match.group("frontmatter") or match.group("blockquote") or "").splitlines():
        line = line.removeprefix("> ").strip()
        key, separator, value = line.partition(":")
        if separator:
            fields[key.strip().lower().replace("_", " ")] = value.strip()
    return fields


def _metadata(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".md":
        return _markdown_metadata(text)
    if path.suffix == ".html":
        return {
            match.group("name").lower(): match.group("content")
            for match in re.finditer(
                r'<meta\s+name=["\'](?P<name>release-(?:version|date|status))["\']\s+content=["\'](?P<content>[^"\']*)["\']\s*/?>',
                text,
                re.IGNORECASE,
            )
        }
    if path.suffix == ".json":
        payload: Any = json.loads(text)
        release = payload.get("release", {}) if isinstance(payload, dict) else {}
        return {str(key): str(value) for key, value in release.items()} if isinstance(release, dict) else {}
    return {}


def _allowed_status(status: str | None) -> bool:
    return status in {"DRAFT", "EXTERNAL-BLOCKED"}


def check_paths(root: Path, paths: tuple[str, ...] = DEFAULT_PATHS) -> tuple[str, ...]:
    issues: list[str] = []
    for relative in paths:
        path = root / relative
        if not path.is_file():
            issues.append(f"missing_metadata_file:{relative}")
            continue
        try:
            fields = _metadata(path)
        except json.JSONDecodeError:
            issues.append(f"invalid_metadata:{relative}")
            continue
        version = fields.get("version") or fields.get("release-version")
        date = fields.get("last updated") or fields.get("date") or fields.get("release-date")
        status = fields.get("status") or fields.get("release-status")
        if version != VERSION:
            issues.append(f"missing_version:{relative}")
        if date != DATE:
            issues.append(f"missing_date:{relative}")
        if not _allowed_status(status):
            issues.append(f"invalid_release_status:{relative}")
    return tuple(issues)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    issues = check_paths(args.root)
    if issues:
        print("FAIL", *issues, sep="\n")
        return 1
    print(f"OK release metadata version {VERSION} date {DATE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
