"""Validate requirement, acceptance, and task mappings in one SDD directory."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

FR_RE = re.compile(r"\b(?:NFR|FR)-[A-Z]{2}-\d+\b", re.IGNORECASE)
AC_RE = re.compile(r"\bAC-[A-Z]{2}-\d+\b", re.IGNORECASE)


def collect_ids(text: str, pattern: re.Pattern[str]) -> frozenset[str]:
    """Return normalized identifiers from prose or Gherkin tags."""
    return frozenset(match.group().lstrip("@").upper() for match in pattern.finditer(text))


def _read(spec_dir: Path, name: str) -> str:
    path = spec_dir / name
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _check_mapping(
    source: frozenset[str], mapped: frozenset[str], missing_code: str, unknown_code: str
) -> list[str]:
    return [
        *(f"{missing_code}:{identifier}" for identifier in sorted(source - mapped)),
        *(f"{unknown_code}:{identifier}" for identifier in sorted(mapped - source)),
    ]


def check_spec_dir(spec_dir: Path) -> tuple[str, ...]:
    """Return stable issue codes for one spec, feature, and task triplet.

    Requirement and acceptance identifiers are deliberately collected from all
    Gherkin text, rather than tags only: a reference in either place is a
    mapping claim and must be known to the spec.
    """
    spec = _read(spec_dir, "spec.md")
    feature = _read(spec_dir, "acceptance.feature")
    tasks = _read(spec_dir, "tasks.md")
    requirements = collect_ids(spec, FR_RE)
    acceptance = collect_ids(spec, AC_RE)
    feature_requirements = collect_ids(feature, FR_RE)
    feature_acceptance = collect_ids(feature, AC_RE)
    task_requirements = collect_ids(tasks, FR_RE)
    task_acceptance = collect_ids(tasks, AC_RE)
    issues: list[str] = []
    if not requirements:
        issues.append("no_requirement_ids_discovered")
    if not acceptance:
        issues.append("no_acceptance_ids_discovered")
    if not tasks:
        issues.append("missing_tasks_file")
    issues.extend(
        _check_mapping(
            requirements,
            feature_requirements,
            "missing_acceptance_mapping",
            "unknown_acceptance_requirement",
        )
    )
    issues.extend(
        _check_mapping(
            requirements, task_requirements, "missing_task_mapping", "unknown_task_requirement"
        )
    )
    issues.extend(
        _check_mapping(
            acceptance, feature_acceptance, "missing_feature_acceptance", "unknown_acceptance_id"
        )
    )
    issues.extend(
        _check_mapping(
            acceptance, task_acceptance, "missing_task_acceptance", "unknown_task_acceptance"
        )
    )
    return tuple(issues)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec_dir", type=Path)
    args = parser.parse_args()
    issues = check_spec_dir(args.spec_dir)
    if issues:
        print("FAIL", *issues, sep="\n")
        return 1
    spec = _read(args.spec_dir, "spec.md")
    print("OK requirements:", ", ".join(sorted(collect_ids(spec, FR_RE))))
    print("OK acceptance:", ", ".join(sorted(collect_ids(spec, AC_RE))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
