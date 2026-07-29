from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from check_traceability import check_spec_dir  # noqa: E402


def _spec(root: Path, *, fr: str, ac: str, task: str) -> Path:
    root.mkdir()
    (root / "spec.md").write_text(f"**{fr}:** requisito\n**{ac} ({fr}):** aceite\n")
    (root / "acceptance.feature").write_text(f"@{fr.lower()} @{ac.lower()}\nScenario: exemplo\n")
    (root / "tasks.md").write_text(task)
    return root


def test_checker_understands_domain_qualified_ids(tmp_path: Path) -> None:
    assert check_spec_dir(_spec(tmp_path / "sdd", fr="FR-AR-6", ac="AC-AR-6", task="FR-AR-6 AC-AR-6")) == ()


def test_checker_rejects_vacuous_success(tmp_path: Path) -> None:
    assert "no_requirement_ids_discovered" in check_spec_dir(_spec(tmp_path / "sdd", fr="", ac="", task=""))


def test_checker_reports_missing_and_unknown_mappings(tmp_path: Path) -> None:
    directory = _spec(tmp_path / "sdd", fr="FR-GD-2", ac="AC-GD-2", task="")
    (directory / "acceptance.feature").write_text("@ac-gd-99\nScenario: exemplo\n")
    issues = check_spec_dir(directory)
    assert "missing_acceptance_mapping:FR-GD-2" in issues
    assert "missing_task_mapping:FR-GD-2" in issues
    assert "unknown_acceptance_id:AC-GD-99" in issues
    assert "missing_feature_acceptance:AC-GD-2" in issues
    assert "missing_task_acceptance:AC-GD-2" in issues


def test_checker_rejects_unknown_requirement_in_gherkin_text_and_tasks(tmp_path: Path) -> None:
    directory = _spec(tmp_path / "sdd", fr="FR-GD-2", ac="AC-GD-2", task="FR-GD-99 AC-GD-99")
    (directory / "acceptance.feature").write_text("Scenario: FR-GD-98 AC-GD-98\n")
    issues = check_spec_dir(directory)
    assert "unknown_acceptance_requirement:FR-GD-98" in issues
    assert "unknown_task_requirement:FR-GD-99" in issues
    assert "unknown_acceptance_id:AC-GD-98" in issues
    assert "unknown_task_acceptance:AC-GD-99" in issues
