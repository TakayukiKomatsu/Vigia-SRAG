"""
Source-contract loading and validation for the SRAG data foundation.

load_source_contract() is the primary public entry point.  It reads a versioned
JSON document, validates it with Pydantic (strict, no extra keys), and then checks
business-rule invariants.  All errors are collected before raising — fail-closed,
not fail-on-first.

evaluate_quality_state() maps a completeness fraction to a QualityState.
Structural blockers must be applied by the caller after this function.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from ..domain.models import SourceContractDocument
from ..domain.source import (
    CNES_COMPETENCIA,
    CNES_ICU_ALLOWLIST,
    QUALITY_THRESHOLD_AVAILABLE,
    QUALITY_THRESHOLD_WARNING,
    QualityState,
)

# ---------------------------------------------------------------------------
# Error types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContractFieldError:
    """A single structured validation failure within a source-contract document."""

    field: str
    reason: str
    value: object = None


class ContractValidationError(Exception):
    """
    Raised when a source-contract document fails validation.

    .errors contains all failures collected in one pass.
    Raising with an empty list is a programming error.
    """

    def __init__(self, errors: list[ContractFieldError]) -> None:
        if not errors:
            raise ValueError("ContractValidationError requires at least one error")
        self.errors = errors
        detail = "; ".join(f"{e.field}: {e.reason}" for e in errors)
        super().__init__(f"Contract validation failed [{len(errors)} error(s)]: {detail}")


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def load_source_contract(path: Path) -> SourceContractDocument:
    """
    Load and validate a versioned JSON source-contract document.

    Validation order:
    1. Read the file.
    2. Parse JSON (raises ContractValidationError on malformed input).
    3. Validate against SourceContractDocument via model_validate_json — extra keys
       are forbidden; unknown fields raise ContractValidationError.
    4. Check business-rule invariants (allowlist exactness, competência lock).

    Returns the validated, frozen SourceContractDocument on success.
    Raises ContractValidationError on any failure.
    """
    # 1. Read
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContractValidationError(
            [ContractFieldError("path", f"Cannot read file: {exc}", str(path))]
        ) from exc

    # 2. Sanity-check the outer JSON type before Pydantic sees it
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ContractValidationError(
            [
                ContractFieldError(
                    "json",
                    f"Invalid JSON at line {exc.lineno} col {exc.colno}: {exc.msg}",
                )
            ]
        ) from exc

    if not isinstance(raw, dict):
        raise ContractValidationError(
            [ContractFieldError("json", f"Expected JSON object, got {type(raw).__name__}")]
        )

    # 3. Pydantic model validation (JSON mode handles ISO string → date coercion)
    try:
        doc = SourceContractDocument.model_validate_json(text)
    except ValidationError as exc:
        errors = [
            ContractFieldError(
                field=".".join(str(p) for p in e["loc"]) if e["loc"] else "root",
                reason=e["msg"],
                value=e.get("input"),
            )
            for e in exc.errors()
        ]
        raise ContractValidationError(errors) from exc

    # 4. Business-rule invariants
    inv_errors = _check_invariants(doc)
    if inv_errors:
        raise ContractValidationError(inv_errors)

    return doc


def _check_invariants(doc: SourceContractDocument) -> list[ContractFieldError]:
    """Validate business-rule invariants beyond Pydantic type checking."""
    errors: list[ContractFieldError] = []

    # cnes_competencia: redundant with Literal[202606] but validated explicitly for clarity
    if doc.cnes_competencia != CNES_COMPETENCIA:
        errors.append(
            ContractFieldError(
                field="cnes_competencia",
                reason=f"Must be exactly {CNES_COMPETENCIA}; got {doc.cnes_competencia}",
                value=doc.cnes_competencia,
            )
        )

    # cnes_icu_allowlist: must be exactly the frozen canonical set
    declared = frozenset(doc.cnes_icu_allowlist)
    if declared != CNES_ICU_ALLOWLIST:
        extra = sorted(declared - CNES_ICU_ALLOWLIST)
        missing = sorted(CNES_ICU_ALLOWLIST - declared)
        errors.append(
            ContractFieldError(
                field="cnes_icu_allowlist",
                reason=(
                    f"Allowlist mismatch — codes not in spec: {extra}; "
                    f"codes missing from spec: {missing}"
                ),
                value=sorted(declared),
            )
        )

    return errors


# ---------------------------------------------------------------------------
# Quality evaluation
# ---------------------------------------------------------------------------


def evaluate_quality_state(completeness: float) -> QualityState:
    """
    Map a completeness fraction [0.0, 1.0] to a QualityState.

    Thresholds (PoC guardrails, not official epidemiological standards):
    - >= 90 % → AVAILABLE
    - >= 70 % → WARNING
    - <  70 % → UNAVAILABLE

    Structural blockers (critical column absent, hash mismatch, insufficient coverage)
    yield BLOCKED regardless of completeness.  The caller must evaluate and apply
    structural blockers AFTER calling this function — they override the returned state.
    """
    if not (0.0 <= completeness <= 1.0):
        raise ValueError(f"completeness must be in [0.0, 1.0], got {completeness!r}")
    if completeness >= QUALITY_THRESHOLD_AVAILABLE:
        return QualityState.AVAILABLE
    if completeness >= QUALITY_THRESHOLD_WARNING:
        return QualityState.WARNING
    return QualityState.UNAVAILABLE
