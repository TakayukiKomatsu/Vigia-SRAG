from __future__ import annotations

import datetime as dt
import json
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ..domain.models import CnesCanonicalRow, IbgePopulationRow, PniObservation
from ..domain.source import (
    CNES_COMPETENCIA,
    CNES_COMPLEMENTARY_BED_TYPE,
    CNES_ICU_ALLOWLIST,
    IBGE_BRAZIL_POPULATION,
    IBGE_REFERENCE_DATE,
    QualityState,
)
from .decoders import decode_dbc_to_rows, iter_ods_rows
from .normalization import (
    CnesNormalizationResult,
    FieldReasonCounts,
    IbgeNormalizationResult,
    NormalizationCounts,
    PniNormalizationResult,
)

_IBGE_STATE_TO_UF = {
    "11": "RO",
    "12": "AC",
    "13": "AM",
    "14": "RR",
    "15": "PA",
    "16": "AP",
    "17": "TO",
    "21": "MA",
    "22": "PI",
    "23": "CE",
    "24": "RN",
    "25": "PB",
    "26": "PE",
    "27": "AL",
    "28": "SE",
    "29": "BA",
    "31": "MG",
    "32": "ES",
    "33": "RJ",
    "35": "SP",
    "41": "PR",
    "42": "SC",
    "43": "RS",
    "50": "MS",
    "51": "MT",
    "52": "GO",
    "53": "DF",
}
_CNES_NAME = re.compile(r"^LT(?P<uf>[A-Z]{2})(?P<year>\d{2})(?P<month>\d{2})\.dbc$", re.IGNORECASE)


def _reasons(reason_counts: Counter[str], field_counts: Counter[str]) -> FieldReasonCounts:
    return FieldReasonCounts(
        by_reason=dict(sorted(reason_counts.items())),
        by_field=dict(sorted(field_counts.items())),
    )


def _quality_result_args(
    *, accepted: int, quarantined: int
) -> tuple[float, QualityState, bool, str | None]:
    denominator = accepted + quarantined
    completeness = accepted / denominator if denominator else 0.0
    if accepted == 0:
        return completeness, QualityState.BLOCKED, True, "no valid source rows"
    if completeness >= 0.9:
        state = QualityState.AVAILABLE
    elif completeness >= 0.7:
        state = QualityState.WARNING
    else:
        state = QualityState.UNAVAILABLE
    return completeness, state, False, None


def normalize_cnes_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    source_sha256: str,
    competencia: int = CNES_COMPETENCIA,
    expected_uf: str | None = None,
) -> tuple[tuple[CnesCanonicalRow, ...], CnesNormalizationResult]:
    if competencia != CNES_COMPETENCIA:
        raise ValueError(
            f"CNES competence must be {CNES_COMPETENCIA}; another competence reopens mapping"
        )
    accepted_rows: list[CnesCanonicalRow] = []
    reason_counts: Counter[str] = Counter()
    field_counts: Counter[str] = Counter()
    total = filtered = quarantined = 0

    for raw in rows:
        total += 1
        if str(raw.get("TP_LEITO", "")).strip().zfill(2) != CNES_COMPLEMENTARY_BED_TYPE:
            filtered += 1
            reason_counts["tp_leito_out_of_scope"] += 1
            continue
        try:
            cod_leito = int(str(raw.get("COD_LEITO", "")).strip())
        except ValueError:
            filtered += 1
            reason_counts["cod_leito_out_of_scope"] += 1
            field_counts["cod_leito"] += 1
            continue
        if cod_leito not in CNES_ICU_ALLOWLIST:
            filtered += 1
            reason_counts["cod_leito_out_of_scope"] += 1
            continue

        cod_ufmun = str(raw.get("CODUFMUN", "")).strip()
        uf = _IBGE_STATE_TO_UF.get(cod_ufmun[:2])
        try:
            qt_exist = int(str(raw.get("QT_EXIST", "")).strip())
        except ValueError:
            qt_exist = -1
        if uf is None or qt_exist < 0 or (expected_uf is not None and uf != expected_uf):
            quarantined += 1
            reason_counts["invalid_cnes_structure"] += 1
            if uf is None or (expected_uf is not None and uf != expected_uf):
                field_counts["uf"] += 1
            if qt_exist < 0:
                field_counts["qt_exist"] += 1
            continue
        accepted_rows.append(
            CnesCanonicalRow(
                competencia=202606,
                uf=uf,
                cod_leito=cod_leito,
                qt_exist=qt_exist,
                source_sha256=source_sha256,
            )
        )

    completeness, state, blocked, blocker_reason = _quality_result_args(
        accepted=len(accepted_rows), quarantined=quarantined
    )
    result = CnesNormalizationResult(
        counts=NormalizationCounts(
            total_input=total,
            accepted=len(accepted_rows),
            quarantined=quarantined,
            filtered=filtered,
        ),
        reasons=_reasons(reason_counts, field_counts),
        completeness=completeness,
        quality_state=state,
        blocked=blocked,
        blocker_reason=blocker_reason,
    )
    return tuple(accepted_rows), result


def normalize_cnes_dbc(
    path: Path,
    *,
    source_sha256: str,
) -> tuple[tuple[CnesCanonicalRow, ...], CnesNormalizationResult]:
    match = _CNES_NAME.fullmatch(path.name)
    if match is None:
        raise ValueError("CNES file name must match LT{UF}{YY}{MM}.dbc")
    competencia = 200000 + int(match.group("year")) * 100 + int(match.group("month"))
    return normalize_cnes_rows(
        decode_dbc_to_rows(path),
        source_sha256=source_sha256,
        competencia=competencia,
        expected_uf=match.group("uf").upper(),
    )


def _normalized_integer(value: object) -> int | None:
    text = str(value).strip().replace(".", "").replace(" ", "")
    if not text.isdigit():
        return None
    return int(text)


def normalize_ibge_rows(
    rows: Iterable[Mapping[str, object]],
    *,
    source_sha256: str,
) -> tuple[IbgePopulationRow | None, IbgeNormalizationResult]:
    total = 0
    matched = False
    for row in rows:
        total += 1
        values = tuple(row.values())
        has_brazil = any(str(value).strip().casefold() == "brasil" for value in values)
        has_population = any(
            _normalized_integer(value) == IBGE_BRAZIL_POPULATION for value in values
        )
        if has_brazil and has_population:
            matched = True

    population = (
        IbgePopulationRow(
            year=2025,
            geography="BR",
            population_official=213_421_037,
            reference_date=IBGE_REFERENCE_DATE,
            source_sha256=source_sha256,
        )
        if matched
        else None
    )
    accepted = int(matched)
    filtered = total - accepted
    state = QualityState.AVAILABLE if matched else QualityState.BLOCKED
    return population, IbgeNormalizationResult(
        counts=NormalizationCounts(
            total_input=total,
            accepted=accepted,
            filtered=filtered,
        ),
        reasons=FieldReasonCounts(
            by_reason={} if matched else {"verified_brazil_row_not_found": 1},
            by_field={} if matched else {"population_official": 1},
        ),
        completeness=1.0 if matched else 0.0,
        quality_state=state,
        blocked=not matched,
        blocker_reason=None if matched else "verified IBGE Brazil row not found",
    )


def normalize_ibge_ods(
    path: Path,
    *,
    source_sha256: str,
    sheet_index: int = 0,
    header_row_index: int = 0,
) -> tuple[IbgePopulationRow | None, IbgeNormalizationResult]:
    return normalize_ibge_rows(
        iter_ods_rows(path, sheet_index, header_row_index=header_row_index),
        source_sha256=source_sha256,
    )


def normalize_pni_observation(
    data: str | bytes | Mapping[str, object],
    *,
    as_of: dt.date,
) -> tuple[PniObservation | None, PniNormalizationResult]:
    try:
        if isinstance(data, str | bytes):
            observation = PniObservation.model_validate_json(data)
        else:
            observation = PniObservation.model_validate_json(json.dumps(data))
    except ValidationError:
        return None, PniNormalizationResult(
            counts=NormalizationCounts(total_input=1, accepted=0, quarantined=1),
            reasons=FieldReasonCounts(
                by_reason={"invalid_pni_observation": 1}, by_field={"observation": 1}
            ),
            completeness=0.0,
            quality_state=QualityState.BLOCKED,
            blocked=True,
            blocker_reason="invalid PNI observation",
            eligible=False,
        )

    calculated = (
        Decimal(observation.numerator) / Decimal(observation.denominator) * Decimal(100)
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if calculated != observation.coverage_pct:
        return None, PniNormalizationResult(
            counts=NormalizationCounts(total_input=1, accepted=0, quarantined=1),
            reasons=FieldReasonCounts(
                by_reason={"coverage_mismatch": 1}, by_field={"coverage_pct": 1}
            ),
            completeness=0.0,
            quality_state=QualityState.BLOCKED,
            blocked=True,
            blocker_reason="PNI coverage does not match numerator/denominator",
            eligible=False,
        )

    eligible = observation.published_at.date() <= as_of
    counts = NormalizationCounts(
        total_input=1,
        accepted=1 if eligible else 0,
        filtered=0 if eligible else 1,
    )
    result = PniNormalizationResult(
        counts=counts,
        reasons=FieldReasonCounts(
            by_reason={} if eligible else {"not_published_by_cutoff": 1}, by_field={}
        ),
        completeness=1.0,
        quality_state=QualityState.AVAILABLE if eligible else QualityState.UNAVAILABLE,
        blocked=False,
        blocker_reason=None,
        eligible=eligible,
    )
    return (observation if eligible else None), result
