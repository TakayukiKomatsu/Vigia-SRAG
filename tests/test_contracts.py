"""T-DF-2 contract tests: frozen constants, load/validate, quality state."""

from __future__ import annotations

import pathlib

import pytest

from srag_report.data.contracts import (
    ContractValidationError,
    evaluate_quality_state,
    load_source_contract,
)
from srag_report.domain.source import (
    CNES_COMPETENCIA,
    CNES_ICU_ALLOWLIST,
    QUALITY_THRESHOLD_AVAILABLE,
    QUALITY_THRESHOLD_WARNING,
    SIVEP_AGENT_FACING_FORBIDDEN,
    SIVEP_CANONICAL_COMPLETENESS_FIELDS,
    SIVEP_MINIMIZATION_ALLOWLIST,
    SIVEP_REQUIRED_SOURCE_COLUMNS,
    QualityState,
    SivepCanonicalField,
)

SYNTH = pathlib.Path(__file__).parent / "fixtures" / "synthetic"


def test_cnes_allowlist_exact() -> None:
    assert CNES_ICU_ALLOWLIST == frozenset({61, 62, 63, 75, 76, 79, 80, 81, 82})


def test_cnes_allowlist_excludes_ambiguous() -> None:
    assert CNES_ICU_ALLOWLIST.isdisjoint({74, 78, 51, 52, 96})


def test_cnes_competencia_locked() -> None:
    assert CNES_COMPETENCIA == 202606


def test_cnes_allowlist_cardinality() -> None:
    assert len(CNES_ICU_ALLOWLIST) == 9


def test_notification_key_forbidden() -> None:
    assert SivepCanonicalField.NOTIFICATION_KEY in SIVEP_AGENT_FACING_FORBIDDEN


def test_digitization_date_forbidden() -> None:
    assert SivepCanonicalField.DIGITIZATION_DATE in SIVEP_AGENT_FACING_FORBIDDEN


def test_forbidden_not_in_minimization_allowlist() -> None:
    assert SIVEP_AGENT_FACING_FORBIDDEN.isdisjoint(SIVEP_MINIMIZATION_ALLOWLIST)


def test_completeness_excludes_technical_keys() -> None:
    assert SivepCanonicalField.NOTIFICATION_KEY not in SIVEP_CANONICAL_COMPLETENESS_FIELDS
    assert SivepCanonicalField.DIGITIZATION_DATE not in SIVEP_CANONICAL_COMPLETENESS_FIELDS


def test_sivep_required_columns_contains_mvp() -> None:
    expected = {
        "NU_NOTIFIC",
        "DT_NOTIFIC",
        "DT_SIN_PRI",
        "HOSPITAL",
        "DT_INTERNA",
        "SG_UF_INTE",
        "UTI",
        "DT_ENTUTI",
        "DT_SAIDUTI",
        "EVOLUCAO",
        "DT_EVOLUCA",
        "DT_ENCERRA",
        "DT_DIGITA",
        "SG_UF",
    }
    assert expected.issubset(SIVEP_REQUIRED_SOURCE_COLUMNS)


def test_quality_thresholds() -> None:
    assert QUALITY_THRESHOLD_AVAILABLE == pytest.approx(0.90)
    assert QUALITY_THRESHOLD_WARNING == pytest.approx(0.70)
    assert QUALITY_THRESHOLD_AVAILABLE > QUALITY_THRESHOLD_WARNING


def test_load_valid_contract() -> None:
    doc = load_source_contract(SYNTH / "source_contract_valid.json")
    assert doc.schema_version == "1.0"
    assert doc.cnes_competencia == 202606
    assert frozenset(doc.cnes_icu_allowlist) == CNES_ICU_ALLOWLIST


def test_load_bad_allowlist_raises() -> None:
    with pytest.raises(ContractValidationError) as exc_info:
        load_source_contract(SYNTH / "source_contract_bad_allowlist.json")
    assert any("cnes_icu_allowlist" in e.field for e in exc_info.value.errors)


def test_load_extra_key_raises() -> None:
    with pytest.raises(ContractValidationError):
        load_source_contract(SYNTH / "source_contract_extra_key.json")


def test_load_missing_file_raises(tmp_path: pathlib.Path) -> None:
    with pytest.raises(ContractValidationError) as exc_info:
        load_source_contract(tmp_path / "nope.json")
    assert exc_info.value.errors[0].field == "path"


def test_load_malformed_json_raises(tmp_path: pathlib.Path) -> None:
    (tmp_path / "bad.json").write_text("{bad", encoding="utf-8")
    with pytest.raises(ContractValidationError) as exc_info:
        load_source_contract(tmp_path / "bad.json")
    assert exc_info.value.errors[0].field == "json"


def test_contract_error_requires_errors() -> None:
    with pytest.raises(ValueError):
        raise ContractValidationError([])


@pytest.mark.parametrize(
    "completeness,expected",
    [
        (1.00, QualityState.AVAILABLE),
        (0.95, QualityState.AVAILABLE),
        (0.90, QualityState.AVAILABLE),
        (0.89, QualityState.WARNING),
        (0.80, QualityState.WARNING),
        (0.70, QualityState.WARNING),
        (0.69, QualityState.UNAVAILABLE),
        (0.65, QualityState.UNAVAILABLE),
        (0.00, QualityState.UNAVAILABLE),
    ],
)
def test_evaluate_quality_state(completeness: float, expected: QualityState) -> None:
    assert evaluate_quality_state(completeness) == expected


def test_evaluate_quality_state_rejects_out_of_range() -> None:
    with pytest.raises(ValueError):
        evaluate_quality_state(1.01)
    with pytest.raises(ValueError):
        evaluate_quality_state(-0.01)
