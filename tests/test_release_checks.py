from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from check_external_release import resolve_ref, validate_release  # noqa: E402
from check_release_contents import check_history, check_tree, find_forbidden  # noqa: E402
from check_release_metadata import check_paths  # noqa: E402


def _bytes(*parts: str) -> bytes:
    return "".join(parts).encode()


def test_metadata_rejects_missing_and_stale_markers(tmp_path: Path) -> None:
    (tmp_path / "doc.md").write_text("> Status: DRAFT\n> Version: 2.1\n> Last Updated: 2026-07-28\n\nVersion: 2.2\n2026-07-29\n")
    issues = check_paths(tmp_path, ("doc.md", "missing.md"))
    assert "missing_version:doc.md" in issues
    assert "missing_date:doc.md" in issues
    assert "missing_metadata_file:missing.md" in issues


def test_metadata_accepts_designated_draft_or_external_blocked_fields(tmp_path: Path) -> None:
    (tmp_path / "doc.md").write_text("---\nstatus: EXTERNAL-BLOCKED\nversion: 2.2\ndate: 2026-07-29\n---\n")
    assert check_paths(tmp_path, ("doc.md",)) == ()


def test_contents_rejects_restricted_content() -> None:
    assert find_forbidden("evidence.txt", _bytes("OPEN_ROUTER", "_API_KEY=secret"))
    assert not find_forbidden(".env.example", _bytes("OPEN_ROUTER", "_API_KEY=\n"))
    assert find_forbidden("article.json", _bytes('{"full', '_text": "payload"}'))


CHALLENGE_NAME = "Desafio de " "GenAI.txt"


RESTRICTED_FIXTURES = (
    (CHALLENGE_NAME, b"safe", f"forbidden_path:{CHALLENGE_NAME}"),
    ("notes.txt", _bytes("GenAI chall", "enge instructions"), "forbidden_content:notes.txt:restricted_challenge"),
    ("settings.txt", _bytes("OPEN", "AI_API_KEY=secret"), "forbidden_content:settings.txt:credential"),
    ("data/source/source.csv", b"safe", "forbidden_path:data/source/source.csv"),
    ("records.txt", _bytes("patient_", "name: Ana"), "forbidden_content:records.txt:raw_clinical_data"),
    ("data/snapshots/release.duckdb", b"safe", "forbidden_path:data/snapshots/release.duckdb"),
    ("runs/release/audit.json", b"safe", "forbidden_path:runs/release/audit.json"),
    ("article.json", _bytes('{"full', '_text": "payload"}'), "forbidden_content:article.json:full_article_payload"),
    (".agent/state/session.json", b"safe", "forbidden_path:.agent/state/session.json"),
)


def _init_repo(root: Path) -> None:
    import subprocess

    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "fixture@example.test"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Fixture"], cwd=root, check=True)


@pytest.mark.parametrize(("name", "content", "expected"), RESTRICTED_FIXTURES)
def test_contents_rejects_every_restricted_class_in_current_tree(
    tmp_path: Path, name: str, content: bytes, expected: str
) -> None:
    import subprocess

    _init_repo(tmp_path)
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    subprocess.run(["git", "add", "-f", name], cwd=tmp_path, check=True)
    assert expected in check_tree(tmp_path)


@pytest.mark.parametrize(("name", "content", "expected"), RESTRICTED_FIXTURES)
def test_contents_rejects_every_restricted_class_in_reachable_history(
    tmp_path: Path, name: str, content: bytes, expected: str
) -> None:
    import subprocess

    _init_repo(tmp_path)
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    subprocess.run(["git", "add", "-f", name], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "restricted fixture"], cwd=tmp_path, check=True, capture_output=True)
    history_expected = expected.replace("forbidden_path:", "forbidden_history_path:")
    assert history_expected in check_history(tmp_path)


def test_contents_only_scans_tracked_current_tree(tmp_path: Path) -> None:
    import subprocess

    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / ".gitignore").write_text("data/raw/\n")
    (tmp_path / "safe.md").write_text("safe")
    (tmp_path / "data/raw").mkdir(parents=True)
    (tmp_path / "data/raw/secret.csv").write_text("OPENAI_API_KEY=secret")
    subprocess.run(["git", "add", ".gitignore", "safe.md"], cwd=tmp_path, check=True)
    assert check_tree(tmp_path) == ()


def test_contents_scans_removed_reachable_history_blob(tmp_path: Path) -> None:
    import subprocess

    _init_repo(tmp_path)
    (tmp_path / "release.txt").write_bytes(_bytes("OPEN", "AI_API_KEY=secret"))
    subprocess.run(["git", "add", "release.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "restricted fixture"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "release.txt").write_text("safe")
    subprocess.run(["git", "add", "release.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "remove restricted fixture"], cwd=tmp_path, check=True, capture_output=True)
    assert "forbidden_content:release.txt:credential" in check_history(tmp_path)


def test_external_release_requires_tag_sha_asset_and_clone_status() -> None:
    assert validate_release({"tag_name": "v2.1", "target_commitish": "old", "assets": [], "body": ""}, "sha") == (
        "missing_or_wrong_release_tag", "release_sha_mismatch", "missing_release_evidence_asset", "missing_release_evidence"
    )


def test_external_release_accepts_fixture() -> None:
    payload = {"tag_name": "v2.2", "target_commitish": "abc", "assets": [{"name": "release-verification.json"}]}
    assert validate_release(payload, "abc", {"commit_sha": "abc", "anonymous_clone": "passed"}) == ()


def test_external_release_resolves_lightweight_and_annotated_tags() -> None:
    responses = {
        "https://api.example/git/ref/tags/v2.2": {"object": {"type": "tag", "sha": "tag-object"}},
        "https://api.example/git/tags/tag-object": {"object": {"type": "commit", "sha": "commit-sha"}},
        "https://api.example/git/ref/tags/light": {"object": {"type": "commit", "sha": "light-sha"}},
    }
    assert resolve_ref("https://api.example", "v2.2", responses.__getitem__) == "commit-sha"
    assert resolve_ref("https://api.example", "refs/tags/light", responses.__getitem__) == "light-sha"
