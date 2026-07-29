from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from srag_report.data.decoders import iter_csv_rows
from srag_report.data.normalization import FieldReasonCounts, NormalizationCounts
from srag_report.data.sivep import (
    canonical_row_sha256,
    normalize_sivep_csv_to_jsonl,
    normalize_sivep_rows,
)
from srag_report.data.sources import (
    normalize_cnes_rows,
    normalize_ibge_rows,
    normalize_pni_observation,
)
from srag_report.domain.source import QualityState, SivepEvolutionCode, SivepYesNoCode

_SHA = "0" * 64
_WATERMARK = dt.date(2026, 7, 26)


def _sivep(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "NU_NOTIFIC": "SYNTH-0001",
        "DT_NOTIFIC": "2026-06-03T00:00:00.000Z",
        "DT_SIN_PRI": "2026-06-01T00:00:00.000Z",
        "HOSPITAL": "1",
        "DT_INTERNA": "2026-06-04T00:00:00.000Z",
        "SG_UF_INTE": "SP",
        "UTI": "2",
        "DT_ENTUTI": "",
        "DT_SAIDUTI": "",
        "EVOLUCAO": "1",
        "DT_EVOLUCA": "2026-06-10T00:00:00.000Z",
        "DT_ENCERRA": "2026-06-11T00:00:00.000Z",
        "DT_DIGITA": "2026-06-03T12:00:00.000Z",
        "SG_UF": "SP",
    }
    row.update(overrides)
    return row


def test_normalization_counts_reject_bad_arithmetic() -> None:
    with pytest.raises(ValidationError, match="total_input"):
        NormalizationCounts(total_input=2, accepted=1)


def test_reason_counts_reject_negative_values() -> None:
    with pytest.raises(ValidationError, match="negative"):
        FieldReasonCounts(by_reason={"bad": -1})


def test_sivep_unknown_is_not_no() -> None:
    rows, result = normalize_sivep_rows(
        [_sivep(HOSPITAL="9", UTI="9", EVOLUCAO="9")],
        source_sha256=_SHA,
        year=2026,
        watermark=_WATERMARK,
    )
    assert result.counts.accepted == 1
    assert rows[0].hospitalization_flag is SivepYesNoCode.UNKNOWN
    assert rows[0].hospitalization_flag is not SivepYesNoCode.NO
    assert rows[0].evolution is SivepEvolutionCode.UNKNOWN


def test_sivep_invalid_dates_and_uf_are_nullified() -> None:
    rows, result = normalize_sivep_rows(
        [_sivep(DT_INTERNA="2026-05-01", SG_UF="XX", DT_EVOLUCA="2026-99-99")],
        source_sha256=_SHA,
        year=2026,
        watermark=_WATERMARK,
    )
    assert rows[0].hospitalization_date is None
    assert rows[0].residence_uf is None
    assert rows[0].evolution_date is None
    assert result.reasons.by_reason["invalid_order"] == 1
    assert result.reasons.by_reason["impossible_date"] == 1
    assert result.reasons.by_reason["unknown_code"] == 1


def test_sivep_future_onset_and_missing_key_are_quarantined() -> None:
    rows, result = normalize_sivep_rows(
        [_sivep(DT_SIN_PRI="2026-07-27"), _sivep(NU_NOTIFIC="")],
        source_sha256=_SHA,
        year=2026,
        watermark=_WATERMARK,
    )
    assert rows == ()
    assert result.counts.quarantined == 2
    assert result.quality_state is QualityState.BLOCKED


def test_death_other_disables_evolution_date() -> None:
    rows, result = normalize_sivep_rows(
        [_sivep(EVOLUCAO="3", DT_EVOLUCA="2026-06-10")],
        source_sha256=_SHA,
        year=2026,
        watermark=_WATERMARK,
    )
    assert rows[0].evolution_date is None
    assert result.reasons.by_reason["field_disabled_by_evolution"] == 1


def test_duplicate_prefers_more_complete_then_stable_hash() -> None:
    sparse = _sivep(NU_NOTIFIC="SYNTH-DUP", SG_UF="", SG_UF_INTE="")
    complete = _sivep(NU_NOTIFIC="SYNTH-DUP", SG_UF="RJ")
    rows, result = normalize_sivep_rows(
        [sparse, complete], source_sha256=_SHA, year=2026, watermark=_WATERMARK
    )
    assert len(rows) == 1
    assert rows[0].residence_uf == "RJ"
    assert result.counts.deduplicated == 1

    left = _sivep(NU_NOTIFIC="SYNTH-HASH", SG_UF="SP")
    right = _sivep(NU_NOTIFIC="SYNTH-HASH", SG_UF="RJ")
    ordered, _ = normalize_sivep_rows(
        [left, right], source_sha256=_SHA, year=2026, watermark=_WATERMARK
    )
    candidates, _ = normalize_sivep_rows(
        [left, {**right, "NU_NOTIFIC": "SYNTH-HASH-2"}],
        source_sha256=_SHA,
        year=2026,
        watermark=_WATERMARK,
    )
    expected = min(candidates, key=canonical_row_sha256).residence_uf
    assert ordered[0].residence_uf == expected


def test_sivep_csv_normalization_is_deterministic(tmp_path: Path) -> None:
    csv_path = tmp_path / "sivep.csv"
    columns = list(_sivep())
    rows = [_sivep(), _sivep(NU_NOTIFIC="SYNTH-0002", UTI="9")]
    csv_path.write_text(
        ";".join(columns)
        + "\n"
        + "\n".join(";".join(str(row[key]) for key in columns) for row in rows)
        + "\n",
        encoding="utf-8",
    )
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    result_a = normalize_sivep_csv_to_jsonl(
        csv_path, first, source_sha256=_SHA, year=2026, watermark=_WATERMARK
    )
    result_b = normalize_sivep_csv_to_jsonl(
        csv_path, second, source_sha256=_SHA, year=2026, watermark=_WATERMARK
    )
    assert result_a.output_sha256 == result_b.output_sha256
    assert first.read_bytes() == second.read_bytes()
    assert all("update" not in line.casefold() for line in first.read_text().splitlines())


def test_csv_decoder_defaults_to_utf8_semicolon(tmp_path: Path) -> None:
    source = tmp_path / "dados.csv"
    source.write_text("nome;valor\nSão Paulo;1\n", encoding="utf-8")
    assert list(iter_csv_rows(source)) == [{"nome": "São Paulo", "valor": "1"}]


def test_cnes_filters_exact_codes_and_injects_competence() -> None:
    rows, result = normalize_cnes_rows(
        [
            {"TP_LEITO": "03", "COD_LEITO": "61", "CODUFMUN": "355030", "QT_EXIST": "10"},
            {"TP_LEITO": "03", "COD_LEITO": "74", "CODUFMUN": "355030", "QT_EXIST": "2"},
            {"TP_LEITO": "02", "COD_LEITO": "61", "CODUFMUN": "355030", "QT_EXIST": "2"},
            {"TP_LEITO": "03", "COD_LEITO": "75", "CODUFMUN": "355030", "QT_EXIST": "-1"},
        ],
        source_sha256=_SHA,
        expected_uf="SP",
    )
    assert [(row.competencia, row.uf, row.cod_leito, row.qt_exist) for row in rows] == [
        (202606, "SP", 61, 10)
    ]
    assert result.counts.filtered == 2
    assert result.counts.quarantined == 1


def test_ibge_selects_only_verified_brazil_total() -> None:
    population, result = normalize_ibge_rows(
        [
            {"localidade": "Acre", "populacao": "880.000"},
            {"localidade": "BRASIL", "populacao": "213.421.037"},
        ],
        source_sha256=_SHA,
    )
    assert population is not None
    assert population.population_official == 213_421_037
    assert result.counts.accepted == 1
    assert result.counts.filtered == 1


def _pni(published_at: str) -> str:
    return json.dumps(
        {
            "campaign_year": 2026,
            "immunobiological": "INF3",
            "population_scope": ["NE", "CO", "S", "SE"],
            "period_start": "2026-03-01",
            "period_end": "2026-05-31",
            "numerator": 61700,
            "denominator": 100000,
            "coverage_pct": "61.70",
            "published_at": published_at,
            "source_label": "synthetic-pni-observation",
            "is_nationwide": False,
            "is_golden": False,
        }
    )


def test_pni_cutoff_hides_ineligible_numeric_observation() -> None:
    observation, result = normalize_pni_observation(
        _pni("2026-07-27T12:00:00Z"), as_of=dt.date(2026, 7, 26)
    )
    assert observation is None
    assert not result.eligible
    assert result.counts.filtered == 1
    assert result.quality_state is QualityState.UNAVAILABLE


def test_pni_eligible_synthetic_observation() -> None:
    observation, result = normalize_pni_observation(
        _pni("2026-07-25T12:00:00Z"), as_of=dt.date(2026, 7, 26)
    )
    assert observation is not None
    assert result.eligible
    assert observation.population_scope == frozenset({"NE", "CO", "S", "SE"})
