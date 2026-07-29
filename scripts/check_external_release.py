"""Validate immutable GitHub-release evidence supplied by the release owner."""

from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

JsonFetcher = Callable[[str], dict[str, Any]]


def _load_json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url) as response:  # noqa: S310 - explicit GitHub API URL from owner
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object from {url}")
    return payload


def resolve_ref(api_url: str, ref: str, fetch_json: JsonFetcher = _load_json) -> str:
    """Resolve a branch, lightweight tag, or annotated tag to a commit SHA."""
    if re.fullmatch(r"[0-9a-f]{40}", ref, re.IGNORECASE):
        return ref
    normalized = ref.removeprefix("refs/")
    candidates = [normalized] if normalized.startswith(("heads/", "tags/")) else [f"tags/{normalized}", f"heads/{normalized}"]
    reference: dict[str, Any] | None = None
    for candidate in candidates:
        try:
            reference = fetch_json(f"{api_url.rstrip('/')}/git/ref/{urllib.parse.quote(candidate, safe='/')}")
            break
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
    if reference is None:
        raise ValueError(f"GitHub ref not found: {ref}")
    target = reference.get("object")
    while isinstance(target, dict) and target.get("type") == "tag":
        tag_sha = target.get("sha")
        if not isinstance(tag_sha, str):
            raise ValueError(f"annotated tag without SHA: {ref}")
        tag = fetch_json(f"{api_url.rstrip('/')}/git/tags/{tag_sha}")
        target = tag.get("object")
    if not isinstance(target, dict) or target.get("type") != "commit" or not isinstance(target.get("sha"), str):
        raise ValueError(f"ref does not resolve to a commit: {ref}")
    return target["sha"]


def validate_release(
    payload: dict[str, Any], sha: str, evidence: dict[str, Any] | None = None, *, release_sha: str | None = None
) -> tuple[str, ...]:
    """Validate release fields after refs have been resolved to immutable SHAs."""
    issues: list[str] = []
    if payload.get("tag_name") != "v2.2":
        issues.append("missing_or_wrong_release_tag")
    if (release_sha or payload.get("target_commitish")) != sha:
        issues.append("release_sha_mismatch")
    assets = payload.get("assets", [])
    if not any(asset.get("name") == "release-verification.json" for asset in assets if isinstance(asset, dict)):
        issues.append("missing_release_evidence_asset")
    evidence = evidence or payload.get("release_evidence")
    if not isinstance(evidence, dict):
        issues.append("missing_release_evidence")
    elif evidence.get("commit_sha") != sha:
        issues.append("release_evidence_sha_mismatch")
    elif evidence.get("anonymous_clone") != "passed":
        issues.append("anonymous_clone_not_passing")
    return tuple(issues)


def _api_root(release_url: str) -> str:
    marker = "/releases/"
    if marker not in release_url:
        raise ValueError("release URL must be a GitHub API /releases/ endpoint; pass --api-url otherwise")
    return release_url.split(marker, 1)[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release_url")
    parser.add_argument("ref", help="Expected Git ref or immutable commit SHA")
    parser.add_argument("--api-url", help="GitHub repository API root, e.g. https://api.github.com/repos/owner/repo")
    args = parser.parse_args()
    payload = _load_json(args.release_url)
    api_url = args.api_url or _api_root(args.release_url)
    expected_sha = resolve_ref(api_url, args.ref)
    release_target = payload.get("target_commitish")
    if not isinstance(release_target, str):
        release_sha = None
    else:
        try:
            release_sha = resolve_ref(api_url, release_target)
        except (urllib.error.HTTPError, ValueError):
            release_sha = None
    asset = next((item for item in payload.get("assets", []) if item.get("name") == "release-verification.json"), None)
    evidence: dict[str, Any] | None = None
    if isinstance(asset, dict) and isinstance(asset.get("browser_download_url"), str):
        evidence = _load_json(asset["browser_download_url"])
    issues = validate_release(payload, expected_sha, evidence, release_sha=release_sha)
    if issues:
        print("FAIL", *issues, sep="\n")
        return 1
    print(f"OK external release v2.2 targets {expected_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
