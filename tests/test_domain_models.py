"""
T-DF-2 domain model tests using synthetic fixtures only.

All positive validations use model_validate_json (JSON mode handles enum/date coercions).
Negative modifications encode to JSON and call model_validate_json — production models
are not loosened.
"""

from __future__ import annotations

import datetime
import json
import pathlib

import pytest
from pydantic import TypeAdapter, ValidationError

from srag_report.domain.models import (
    CnesCanonicalRow,
    IbgePopulationRow,
    PniObservation,
    SivepCanonicalRow,
    SourceContractDocument,
)
from srag_report.domain.source import (
    CNES_ICU_ALLOWLIST,
    PNI_ELIGIBLE_SCOPE,
    SivepEvolutionCode,
    SivepYesNoCode,
)

SYNTH = pathlib.Path(__file__).parent / "fixtures" / "synthetic"

_sivep_ta = TypeAdapter(list[SivepCanonicalRow])
_cnes_ta = TypeAdapter(list[CnesCanonicalRow])


def _sivep_rows() -> list[SivepCanonicalRow]:
    return _sivep_ta.validate_json((SYNTH / "sivep_rows.json").read_text())


def _sivep_raw() -> list[dict]:  # type: ignore[type-arg]
    return json.loads((SYNTH / "sivep_rows.json").read_text())


def _cnes_rows() -> list[CnesCanonicalRow]:
    return _cnes_ta.validate_json((SYNTH / "cnes_rows.json").read_text())


def _cnes_raw() -> list[dict]:  # type: ignore[type-arg]
    return json.loads((SYNTH / "cnes_rows.json").read_text())


# ---------------------------------------------------------------------------
# SIVEP — positive
# ---------------------------------------------------------------------------


def test_sivep_rows_all_valid() -> None:
    rows = _sivep_rows()
    assert len(rows) == 4
    for row in rows:
        assert row.year in (2025, 2026)


def test_sivep_cure_has_evolution_date() -> None:
    rows = _sivep_rows()
    row = next(r for r in rows if r.evolution == SivepEvolutionCode.CURE)
    assert row.evolution_date is not None


def test_sivep_death_srag_has_evolution_date() -> None:
    rows = _sivep_rows()
    row = next(r for r in rows if r.evolution == SivepEvolutionCode.DEATH_SRAG)
    assert row.evolution_date is not None


def test_sivep_death_other_evolution_date_none() -> None:
    """DEATH_OTHER (3): DT_EVOLUCA is disabled in source — evolution_date must be None."""
    rows = _sivep_rows()
    row = next(r for r in rows if r.evolution == SivepEvolutionCode.DEATH_OTHER)
    assert row.evolution == SivepEvolutionCode.DEATH_OTHER
    assert row.evolution_date is None


def test_sivep_unknown_codes_distinct_from_no() -> None:
    rows = _sivep_rows()
    row = next(r for r in rows if r.hospitalization_flag == SivepYesNoCode.UNKNOWN)
    assert row.hospitalization_flag == SivepYesNoCode.UNKNOWN
    assert row.icu_flag == SivepYesNoCode.UNKNOWN
    assert row.hospitalization_flag != SivepYesNoCode.NO


# ---------------------------------------------------------------------------
# SIVEP — negative
# ---------------------------------------------------------------------------


def test_sivep_death_other_with_date_rejected() -> None:
    raw = next(r for r in _sivep_raw() if r["evolution"] == 3)
    bad = {**raw, "evolution_date": "2025-04-10"}
    with pytest.raises(ValidationError) as exc_info:
        SivepCanonicalRow.model_validate_json(json.dumps(bad))
    assert "DEATH_OTHER" in str(exc_info.value)


def test_sivep_extra_field_rejected() -> None:
    bad = {**_sivep_raw()[0], "dt_atualiza": "2026-01-20"}
    with pytest.raises(ValidationError):
        SivepCanonicalRow.model_validate_json(json.dumps(bad))


def test_sivep_no_update_field_in_model() -> None:
    fields = SivepCanonicalRow.model_fields
    forbidden = {"dt_atualiza", "dt_alteracao", "update_date", "update_timestamp"}
    assert forbidden.isdisjoint(fields.keys())


def test_sivep_bad_sha256_rejected() -> None:
    bad = {**_sivep_raw()[0], "source_sha256": "tooshort"}
    with pytest.raises(ValidationError) as exc_info:
        SivepCanonicalRow.model_validate_json(json.dumps(bad))
    assert "sha256" in str(exc_info.value).lower() or "64" in str(exc_info.value)


def test_sivep_uppercase_sha256_rejected() -> None:
    """SHA-256 must be lowercase."""
    bad = {**_sivep_raw()[0], "source_sha256": "A" * 64}
    with pytest.raises(ValidationError):
        SivepCanonicalRow.model_validate_json(json.dumps(bad))


# ---------------------------------------------------------------------------
# CNES — positive
# ---------------------------------------------------------------------------


def test_cnes_rows_all_valid() -> None:
    rows = _cnes_rows()
    for row in rows:
        assert row.cod_leito in CNES_ICU_ALLOWLIST
        assert row.competencia == 202606
        assert row.qt_exist >= 0


def test_cnes_all_allowlist_codes_accepted() -> None:
    base = _cnes_raw()[0]
    for code in sorted(CNES_ICU_ALLOWLIST):
        row = CnesCanonicalRow.model_validate_json(json.dumps({**base, "cod_leito": code}))
        assert row.cod_leito == code


# ---------------------------------------------------------------------------
# CNES — negative
# ---------------------------------------------------------------------------


def test_cnes_code_74_rejected() -> None:
    bad = {**_cnes_raw()[0], "cod_leito": 74}
    with pytest.raises(ValidationError) as exc_info:
        CnesCanonicalRow.model_validate_json(json.dumps(bad))
    assert "74" in str(exc_info.value)


def test_cnes_excluded_codes_rejected() -> None:
    base = _cnes_raw()[0]
    for code in (51, 52, 74, 78, 96):
        with pytest.raises(ValidationError):
            CnesCanonicalRow.model_validate_json(json.dumps({**base, "cod_leito": code}))


def test_cnes_negative_qt_exist_rejected() -> None:
    bad = {**_cnes_raw()[0], "qt_exist": -1}
    with pytest.raises(ValidationError):
        CnesCanonicalRow.model_validate_json(json.dumps(bad))


def test_cnes_bad_sha256_rejected() -> None:
    bad = {**_cnes_raw()[0], "source_sha256": "notahex"}
    with pytest.raises(ValidationError):
        CnesCanonicalRow.model_validate_json(json.dumps(bad))


# ---------------------------------------------------------------------------
# IBGE
# ---------------------------------------------------------------------------


def test_ibge_row_valid() -> None:
    raw_text = (SYNTH / "ibge_row.json").read_text()
    row = IbgePopulationRow.model_validate_json(raw_text)
    assert row.year == 2025
    assert row.geography == "BR"
    assert row.population_official == 213_421_037
    assert row.reference_date == datetime.date(2025, 7, 1)


def test_ibge_wrong_reference_date_rejected() -> None:
    raw = json.loads((SYNTH / "ibge_row.json").read_text())
    with pytest.raises(ValidationError) as exc_info:
        IbgePopulationRow.model_validate_json(json.dumps({**raw, "reference_date": "2025-01-01"}))
    assert "2025-07-01" in str(exc_info.value)


def test_ibge_wrong_population_rejected() -> None:
    raw = json.loads((SYNTH / "ibge_row.json").read_text())
    with pytest.raises(ValidationError):
        IbgePopulationRow.model_validate_json(
            json.dumps({**raw, "population_official": 200_000_000})
        )


def test_ibge_bad_sha256_rejected() -> None:
    raw = json.loads((SYNTH / "ibge_row.json").read_text())
    with pytest.raises(ValidationError):
        IbgePopulationRow.model_validate_json(json.dumps({**raw, "source_sha256": "bad"}))


# ---------------------------------------------------------------------------
# PNI
# ---------------------------------------------------------------------------


def test_pni_valid() -> None:
    raw_text = (SYNTH / "pni_observation.json").read_text()
    obs = PniObservation.model_validate_json(raw_text)
    assert obs.campaign_year == 2026
    assert obs.immunobiological == "INF3"
    assert obs.population_scope == frozenset({"NE", "CO", "S", "SE"})
    assert obs.is_nationwide is False
    assert obs.is_golden is False
    assert obs.published_at.tzinfo is not None
    assert obs.published_at.utcoffset() == datetime.timedelta(0)


def test_pni_scope_subset_of_eligible() -> None:
    raw_text = (SYNTH / "pni_observation.json").read_text()
    obs = PniObservation.model_validate_json(raw_text)
    assert obs.population_scope.issubset(PNI_ELIGIBLE_SCOPE)


def test_pni_nationwide_true_rejected() -> None:
    raw = json.loads((SYNTH / "pni_observation.json").read_text())
    with pytest.raises(ValidationError):
        PniObservation.model_validate_json(json.dumps({**raw, "is_nationwide": True}))


def test_pni_golden_true_rejected() -> None:
    raw = json.loads((SYNTH / "pni_observation.json").read_text())
    with pytest.raises(ValidationError):
        PniObservation.model_validate_json(json.dumps({**raw, "is_golden": True}))


def test_pni_invalid_scope_rejected() -> None:
    raw = json.loads((SYNTH / "pni_observation.json").read_text())
    with pytest.raises(ValidationError):
        PniObservation.model_validate_json(json.dumps({**raw, "population_scope": ["NE", "N"]}))


def test_pni_empty_scope_rejected() -> None:
    raw = json.loads((SYNTH / "pni_observation.json").read_text())
    with pytest.raises(ValidationError):
        PniObservation.model_validate_json(json.dumps({**raw, "population_scope": []}))


def test_pni_naive_published_at_rejected() -> None:
    """published_at without timezone must be rejected."""
    raw = json.loads((SYNTH / "pni_observation.json").read_text())
    with pytest.raises(ValidationError):
        PniObservation.model_validate_json(
            json.dumps({**raw, "published_at": "2026-07-27T12:00:00"})
        )


def test_pni_nonzero_offset_published_at_rejected() -> None:
    """published_at with non-UTC offset must be rejected."""
    raw = json.loads((SYNTH / "pni_observation.json").read_text())
    with pytest.raises(ValidationError):
        PniObservation.model_validate_json(
            json.dumps({**raw, "published_at": "2026-07-27T12:00:00+03:00"})
        )


def test_pni_eligibility_caller_responsibility() -> None:
    """The fixture is post-cutoff; the model accepts it and the caller enforces as_of."""
    raw_text = (SYNTH / "pni_observation.json").read_text()
    obs = PniObservation.model_validate_json(raw_text)
    assert obs.published_at > datetime.datetime(2026, 7, 26, tzinfo=datetime.UTC)


# ---------------------------------------------------------------------------
# SourceContractDocument extra-key rejection
# ---------------------------------------------------------------------------


def test_source_contract_extra_key_rejected() -> None:
    payload = json.dumps(
        {
            "schema_version": "1.0",
            "contract_version": "t",
            "contract_date": "2026-07-29",
            "cnes_competencia": 202606,
            "cnes_icu_allowlist": [61, 62, 63, 75, 76, 79, 80, 81, 82],
            "sources": [],
            "extra": "bad",
        }
    )
    with pytest.raises(ValidationError):
        SourceContractDocument.model_validate_json(payload)
