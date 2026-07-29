from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import check_external_release  # noqa: E402
from check_external_release import resolve_ref, validate_release  # noqa: E402
from check_release_contents import check_history, check_tree, find_forbidden  # noqa: E402
from check_release_metadata import DEFAULT_PATHS, check_paths  # noqa: E402


def _bytes(*parts: str) -> bytes:
    return "".join(parts).encode()


def test_metadata_rejects_missing_and_stale_markers(tmp_path: Path) -> None:
    (tmp_path / "doc.md").write_text(
        "> Status: DRAFT\n> Version: 2.1\n> Last Updated: 2026-07-28\n\nVersion: 2.2\n2026-07-29\n"
    )
    issues = check_paths(tmp_path, ("doc.md", "missing.md"))
    assert "missing_version:doc.md" in issues
    assert "missing_date:doc.md" in issues
    assert "missing_metadata_file:missing.md" in issues


def test_metadata_requires_distinct_document_and_release_status(tmp_path: Path) -> None:
    (tmp_path / "doc.md").write_text(
        "---\ndocument status: DRAFT\nrelease status: EXTERNAL-BLOCKED\n"
        "version: 2.2\ndate: 2026-07-29\n---\n"
    )
    assert check_paths(tmp_path, ("doc.md",)) == ()


def test_metadata_accepts_leading_gherkin_comment_metadata(tmp_path: Path) -> None:
    (tmp_path / "acceptance.feature").write_text(
        "# Document Status: DRAFT\n# Release Status: EXTERNAL-BLOCKED\n"
        "# Version: 2.2\n# Date: 2026-07-29\n\nFeature: example\n"
    )
    assert check_paths(tmp_path, ("acceptance.feature",)) == ()


def test_default_metadata_set_designates_all_acceptance_artifacts() -> None:
    expected = {
        ".agent/specs/01-data-foundation/acceptance.feature",
        ".agent/specs/02-epidemiological-metrics/acceptance.feature",
        ".agent/specs/03-agentic-reporting/acceptance.feature",
        ".agent/specs/04-governance-delivery/acceptance.feature",
    }
    assert expected <= set(DEFAULT_PATHS)


def test_default_metadata_set_includes_and_validates_official_source_run() -> None:
    root = Path(__file__).parents[1]

    assert "examples/official-source-run.json" in DEFAULT_PATHS
    assert check_paths(root) == ()


def test_official_source_run_is_a_complete_sanitized_aggregate() -> None:
    """The releasable example exposes aggregate evidence, never source payloads."""
    payload = json.loads(
        (Path(__file__).parents[1] / "examples/official-source-run.json").read_text()
    )

    assert payload["release"] == {
        "version": "2.2",
        "date": "2026-07-29",
        "status": "EXTERNAL-BLOCKED",
    }
    assert payload["snapshot"]["id"] == "official-20260727"
    assert payload["snapshot"]["preparation_result"] == "prepared_warning_ineligible"
    assert set(payload["sources"]) == {"sivep", "ibge", "cnes", "pni"}
    for source in ("sivep", "ibge"):
        evidence = payload["sources"][source]
        assert evidence["status"] == "verified"
        assert set(evidence) >= {
            "official_landing_url",
            "official_resource_url",
            "retrieved_at",
            "license_reuse_statement",
            "license_evidence_url",
            "size_bytes",
            "data_rows",
            "sha256",
            "encoding",
            "dictionary_version",
            "mapping_verified",
            "mapping_sha256",
            "watermark",
        }
    for source in ("cnes", "pni"):
        assert payload["sources"][source]["status"] == "unavailable"

    assert set(payload["normalization"]) == {"sivep", "ibge", "cnes", "pni"}
    for counts in payload["normalization"].values():
        assert set(counts) >= {"accepted", "filtered", "quarantined", "deduplicated", "total_input"}
    assert set(payload["minimization"]) >= {"table_counts", "excluded_data_classes"}
    assert set(payload["hashes"]) >= {
        "canonical_snapshot_sha256",
        "content_sha256",
        "file_sha256",
        "provenance_sha256",
    }
    assert payload["effective_watermarks"] == {"sivep": "2026-07-26", "ibge": "2025-07-01"}
    assert payload["run"] == {
        **payload["run"],
        "id": "official-20260727-openrouter-20260729",
        "snapshot_id": "official-20260727",
    }
    assert set(payload["metrics"]) == {
        "case_growth",
        "mortality_per_100k",
        "hospital_cfr",
        "icu_pressure",
        "icu_use",
        "influenza_coverage",
    }
    for metric in payload["metrics"].values():
        assert set(metric) >= {"state", "reason"}
    assert payload["preparation"]["golden_eligible"] is False
    assert payload["preparation"]["golden_ineligibility_reasons"]
    assert payload["gate"]["eligible"] is False
    assert payload["gate"]["failures"]
    assert set(payload["commentary"]) >= {
        "requested_model",
        "served_model",
        "validated_claim_count",
        "fallback_used",
    }
    assert set(payload["rss"]) >= {"accepted_item_count", "accepted_sources"}
    assert set(payload["limitations"]) >= {"icu_use", "icu_pressure", "influenza_coverage"}

    serialized = json.dumps(payload)
    forbidden_keys = {
        "local_path",
        "selected_column_mapping",
        "raw_rows",
        "rows",
        "article_payload",
        "full_text",
    }
    observed_keys = {key for key in re.findall(r'"([^"\\]+)"\s*:', serialized)}
    assert not forbidden_keys & observed_keys
    assert not re.search(r"(?i)(?:api[_-]?key|password|secret|token)\s*[:=]", serialized)
    assert not re.search(r'"/(?:Users|home|tmp|var|private)/', serialized)


def test_contents_rejects_restricted_content() -> None:
    assert find_forbidden("evidence.txt", _bytes("OPEN_ROUTER", "_API_KEY=secret"))
    assert not find_forbidden(".env.example", _bytes("OPEN_ROUTER", "_API_KEY=\n"))
    assert find_forbidden("article.json", _bytes('{"full', '_text": "payload"}'))


@pytest.mark.parametrize(
    "name, content",
    (
        (".gitignore", _bytes("Desafio de ", "GenAI.txt\n")),
        ("plan.md", _bytes("Keep `Desafio de ", "GenAI.txt` ignored.\n")),
        ("settings.md", _bytes("Set `OPEN_ROUTER", "_API_KEY=` in the environment template.\n")),
        ("readme.md", _bytes("export OPEN_ROUTER", "_API_KEY='...'\n")),
        ("scanner.py", _bytes('FORBIDDEN_FILENAMES = ("desafio de ", "genai")\n')),
        (
            "tests/test_release_checks.py",
            _bytes('(tmp_path / "secret").write_text("OPEN', 'AI_API_KEY=secret")\n'),
        ),
    ),
)
def test_contents_allows_policy_references_and_placeholder_credentials(
    name: str, content: bytes
) -> None:
    assert find_forbidden(name, content) == ()


def test_contents_still_rejects_unquoted_challenge_material_and_real_credentials() -> None:
    assert find_forbidden("notes.txt", _bytes("GenAI chall", "enge instructions\n"))
    assert find_forbidden(".env", _bytes("OPEN_ROUTER", "_API_KEY=not-a-placeholder\n"))


def test_contents_rejects_write_text_secret_syntax_in_production_code() -> None:
    assert find_forbidden(
        "production/app.py",
        _bytes('(tmp_path / "secret").write_text("OPEN', 'AI_API_KEY=secret")\n'),
    ) == ("forbidden_content:production/app.py:credential",)


CHALLENGE_NAME = "Desafio de " "GenAI.txt"


RESTRICTED_FIXTURES = (
    (CHALLENGE_NAME, b"safe", f"forbidden_path:{CHALLENGE_NAME}"),
    (
        "notes.txt",
        _bytes("GenAI chall", "enge instructions"),
        "forbidden_content:notes.txt:restricted_challenge",
    ),
    (
        "settings.txt",
        _bytes("OPEN", "AI_API_KEY=secret"),
        "forbidden_content:settings.txt:credential",
    ),
    ("data/source/source.csv", b"safe", "forbidden_path:data/source/source.csv"),
    (
        "records.txt",
        _bytes("patient_", "name: Ana"),
        "forbidden_content:records.txt:raw_clinical_data",
    ),
    ("data/snapshots/release.duckdb", b"safe", "forbidden_path:data/snapshots/release.duckdb"),
    ("runs/release/audit.json", b"safe", "forbidden_path:runs/release/audit.json"),
    (
        "article.json",
        _bytes('{"full', '_text": "payload"}'),
        "forbidden_content:article.json:full_article_payload",
    ),
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
    subprocess.run(
        ["git", "commit", "-m", "restricted fixture"], cwd=tmp_path, check=True, capture_output=True
    )
    history_expected = expected.replace("forbidden_path:", "forbidden_history_path:")
    assert history_expected in check_history(tmp_path)


def test_contents_only_scans_tracked_current_tree(tmp_path: Path) -> None:
    import subprocess

    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / ".gitignore").write_text("data/raw/\n")
    (tmp_path / "safe.md").write_text("safe")
    (tmp_path / "data/raw").mkdir(parents=True)
    (tmp_path / "data/raw/secret.csv").write_bytes(_bytes("OPEN", "AI_API_KEY=secret"))
    subprocess.run(["git", "add", ".gitignore", "safe.md"], cwd=tmp_path, check=True)
    assert check_tree(tmp_path) == ()


def test_contents_scans_removed_reachable_history_blob(tmp_path: Path) -> None:
    import subprocess

    _init_repo(tmp_path)
    (tmp_path / "release.txt").write_bytes(_bytes("OPEN", "AI_API_KEY=secret"))
    subprocess.run(["git", "add", "release.txt"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "restricted fixture"], cwd=tmp_path, check=True, capture_output=True
    )
    (tmp_path / "release.txt").write_text("safe")
    subprocess.run(["git", "add", "release.txt"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "remove restricted fixture"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    assert "forbidden_content:release.txt:credential" in check_history(tmp_path)


def test_external_release_requires_tag_sha_asset_and_clone_status() -> None:
    assert validate_release(
        {"tag_name": "v2.1", "target_commitish": "old", "assets": [], "body": ""}, "sha"
    ) == (
        "missing_or_wrong_release_tag",
        "release_sha_mismatch",
        "release_tag_sha_mismatch",
        "missing_release_evidence_asset",
        "missing_release_evidence",
    )


def test_external_release_accepts_fixture() -> None:
    payload = {
        "tag_name": "v2.2",
        "target_commitish": "abc",
        "assets": [{"name": "release-verification.json"}],
    }
    assert (
        validate_release(
            payload,
            "abc",
            {"commit_sha": "abc", "anonymous_clone": "passed"},
            release_sha="abc",
            tag_sha="abc",
        )
        == ()
    )


def test_external_release_rejects_v22_tag_resolved_to_an_old_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "tag_name": "v2.2",
        "target_commitish": "main",
        "assets": [
            {
                "name": "release-verification.json",
                "browser_download_url": "https://example/evidence",
            }
        ],
    }
    resolved = {"expected-ref": "current-sha", "main": "current-sha", "v2.2": "old-sha"}
    monkeypatch.setattr(
        check_external_release,
        "_load_json",
        lambda url: payload
        if url == "https://example/release"
        else {"commit_sha": "current-sha", "anonymous_clone": "passed"},
    )
    monkeypatch.setattr(check_external_release, "resolve_ref", lambda _api, ref: resolved[ref])
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_external_release.py",
            "https://example/release",
            "expected-ref",
            "--api-url",
            "https://api.example",
        ],
    )

    assert check_external_release.main() == 1


def test_external_release_resolves_lightweight_and_annotated_tags() -> None:
    responses = {
        "https://api.example/git/ref/tags/v2.2": {"object": {"type": "tag", "sha": "tag-object"}},
        "https://api.example/git/tags/tag-object": {
            "object": {"type": "commit", "sha": "commit-sha"}
        },
        "https://api.example/git/ref/tags/light": {
            "object": {"type": "commit", "sha": "light-sha"}
        },
    }
    assert resolve_ref("https://api.example", "v2.2", responses.__getitem__) == "commit-sha"
    assert (
        resolve_ref("https://api.example", "refs/tags/light", responses.__getitem__) == "light-sha"
    )
