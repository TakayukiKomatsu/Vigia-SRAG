"""Reject restricted material from tracked files and reachable Git history."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

CHALLENGE_RE = re.compile(r"desafio\s+de\s+genai|genai\s+challenge", re.IGNORECASE)
SECRET_RE = re.compile(
    r"(?:OPENAI|OPEN_ROUTER|OPENROUTER|ANTHROPIC|GITHUB)_API_KEY\s*(?:=|:)\s*(?![\"']?\s*(?:\n|$))[\"']?[^\s#\"']+",
    re.IGNORECASE,
)
FULL_ARTICLE_RE = re.compile(r"(?:full[_ -]?text|article[_ -]?(?:body|payload)|raw[_ -]?article)[\"']?\s*(?:=|:)", re.IGNORECASE)
RAW_CLINICAL_DATA_RE = re.compile(
    r"(?:patient[_ -]?(?:name|id)|nome[_ -]?paciente|cpf|cns)[\"']?\s*(?:=|:)",
    re.IGNORECASE,
)
FORBIDDEN_PATH_PARTS = (
    "data/raw/",
    "data/source/",
    "data/sources/",
    "data/snapshots/",
    "runs/",
    ".agent/state/",
    ".codex/",
    ".omc/",
    ".superpowers/",
)
FORBIDDEN_FILENAMES = ("desafio de genai", "challenge brief")


def _path_issue(name: str) -> str | None:
    lowered = name.lower()
    if any(part in lowered for part in FORBIDDEN_PATH_PARTS) or any(token in lowered for token in FORBIDDEN_FILENAMES):
        return f"forbidden_path:{name}"
    return None


def find_forbidden(name: str, content: bytes) -> tuple[str, ...]:
    """Identify restricted challenge material, secrets, and raw payloads."""
    text = content.decode("utf-8", errors="ignore")
    issues: list[str] = []
    if CHALLENGE_RE.search(text):
        issues.append(f"forbidden_content:{name}:restricted_challenge")
    if SECRET_RE.search(text):
        issues.append(f"forbidden_content:{name}:credential")
    if FULL_ARTICLE_RE.search(text):
        issues.append(f"forbidden_content:{name}:full_article_payload")
    if RAW_CLINICAL_DATA_RE.search(text):
        issues.append(f"forbidden_content:{name}:raw_clinical_data")
    return tuple(issues)


def _tracked_paths(root: Path) -> tuple[str, ...]:
    output = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, check=True, capture_output=True
    ).stdout
    return tuple(path.decode("utf-8") for path in output.split(b"\0") if path)


def check_tree(root: Path) -> tuple[str, ...]:
    """Scan the current working tree only at paths Git tracks.

    This intentionally leaves ignored local acquisitions and run output alone;
    their presence is normal during development and they cannot be released.
    """
    issues: list[str] = []
    for relative in _tracked_paths(root):
        path = root / relative
        if not path.is_file():
            continue
        if issue := _path_issue(relative):
            issues.append(issue)
        issues.extend(find_forbidden(relative, path.read_bytes()))
    return tuple(sorted(set(issues)))


def check_history(root: Path) -> tuple[str, ...]:
    """Scan every blob reachable from any ref, including annotated-tag objects."""
    output = subprocess.run(
        ["git", "rev-list", "--objects", "--all"], cwd=root, check=True, text=True, capture_output=True
    ).stdout
    objects: dict[str, set[str]] = {}
    for line in output.splitlines():
        object_id, _, name = line.partition(" ")
        if name:
            objects.setdefault(object_id, set()).add(name)
    issues: list[str] = []
    for object_id, names in objects.items():
        kind = subprocess.run(
            ["git", "cat-file", "-t", object_id], cwd=root, check=True, text=True, capture_output=True
        ).stdout.strip()
        if kind != "blob":
            continue
        content = subprocess.run(
            ["git", "cat-file", "-p", object_id], cwd=root, check=True, capture_output=True
        ).stdout
        for name in names:
            if issue := _path_issue(name):
                issues.append(f"forbidden_history_path:{name}")
            issues.extend(find_forbidden(name, content))
    return tuple(sorted(set(issues)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", action="store_true")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    issues = check_history(args.root) if args.history else check_tree(args.root)
    if issues:
        print("FAIL", *issues, sep="\n")
        return 1
    print("OK release contents")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
