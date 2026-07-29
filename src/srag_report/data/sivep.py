from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import sqlite3
import tempfile
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from ..domain.models import SivepCanonicalRow
from ..domain.source import (
    SIVEP_CANONICAL_COMPLETENESS_FIELDS,
    SIVEP_EVOLUTION_CODE_MATRIX,
    SIVEP_YESNO_CODE_MATRIX,
    NullReason,
    QualityState,
    QuarantineReason,
    SivepEvolutionCode,
)
from .contracts import evaluate_quality_state
from .decoders import iter_csv_rows
from .normalization import FieldReasonCounts, NormalizationCounts, SivepNormalizationResult

_UFS = frozenset(
    {
        "AC",
        "AL",
        "AP",
        "AM",
        "BA",
        "CE",
        "DF",
        "ES",
        "GO",
        "MA",
        "MT",
        "MS",
        "MG",
        "PA",
        "PB",
        "PR",
        "PE",
        "PI",
        "RJ",
        "RN",
        "RS",
        "RO",
        "RR",
        "SC",
        "SP",
        "SE",
        "TO",
    }
)


@dataclass
class _IssueCounters:
    by_reason: Counter[str] = field(default_factory=Counter)
    by_field: Counter[str] = field(default_factory=Counter)

    def add(self, field_name: str, reason: str) -> None:
        self.by_reason[reason] += 1
        self.by_field[field_name] += 1

    def merge(self, other: _IssueCounters) -> None:
        self.by_reason.update(other.by_reason)
        self.by_field.update(other.by_field)

    def result(self) -> FieldReasonCounts:
        return FieldReasonCounts(
            by_reason=dict(sorted(self.by_reason.items())),
            by_field=dict(sorted(self.by_field.items())),
        )


@dataclass(frozen=True)
class _ParsedRow:
    row: SivepCanonicalRow
    completeness: int
    row_hash: str
    issues: _IssueCounters


def _text(value: object) -> str | None:
    if value is None:
        return None
    result = str(value).strip()
    return result or None


def _parse_date(
    raw: object,
    *,
    field_name: str,
    watermark: dt.date,
    issues: _IssueCounters,
) -> dt.date | None:
    value = _text(raw)
    if value is None:
        return None
    try:
        parsed = dt.date.fromisoformat(value[:10])
    except ValueError:
        issues.add(field_name, NullReason.IMPOSSIBLE_DATE)
        return None
    if parsed > watermark:
        issues.add(field_name, NullReason.FUTURE_DATE)
        return None
    return parsed


def _parse_datetime(raw: object, *, field_name: str, issues: _IssueCounters) -> dt.datetime | None:
    value = _text(raw)
    if value is None:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        issues.add(field_name, NullReason.IMPOSSIBLE_DATE)
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        issues.add(field_name, NullReason.IMPOSSIBLE_DATE)
        return None
    return parsed.astimezone(dt.UTC)


def _parse_code[T](
    raw: object,
    *,
    field_name: str,
    matrix: Mapping[int, T],
    issues: _IssueCounters,
) -> T | None:
    value = _text(raw)
    if value is None:
        return None
    try:
        code = int(value)
    except ValueError:
        issues.add(field_name, NullReason.UNKNOWN_CODE)
        return None
    result = matrix.get(code)
    if result is None:
        issues.add(field_name, NullReason.UNKNOWN_CODE)
    return result


def _parse_uf(raw: object, *, field_name: str, issues: _IssueCounters) -> str | None:
    value = _text(raw)
    if value is None:
        return None
    value = value.upper()
    if value not in _UFS:
        issues.add(field_name, NullReason.UNKNOWN_CODE)
        return None
    return value


def canonical_row_sha256(row: SivepCanonicalRow) -> str:
    payload = row.model_dump(mode="json")
    payload.pop("source_sha256", None)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def canonical_completeness(row: SivepCanonicalRow) -> int:
    return sum(
        getattr(row, field_name.value) is not None
        for field_name in SIVEP_CANONICAL_COMPLETENESS_FIELDS
    )


def _parse_row(
    raw: Mapping[str, object],
    *,
    source_sha256: str,
    year: Literal[2025, 2026],
    watermark: dt.date,
) -> tuple[_ParsedRow | None, _IssueCounters]:
    issues = _IssueCounters()
    notification_key = _text(raw.get("NU_NOTIFIC"))
    symptom_onset = _parse_date(
        raw.get("DT_SIN_PRI"),
        field_name="symptom_onset",
        watermark=watermark,
        issues=issues,
    )
    if notification_key is None or symptom_onset is None:
        if notification_key is None:
            issues.add("notification_key", QuarantineReason.MISSING_MINIMUM_STRUCTURE)
        if symptom_onset is None:
            issues.add("symptom_onset", QuarantineReason.MISSING_MINIMUM_STRUCTURE)
        return None, issues

    notification_date = _parse_date(
        raw.get("DT_NOTIFIC"), field_name="notification_date", watermark=watermark, issues=issues
    )
    if notification_date is not None and notification_date < symptom_onset:
        notification_date = None
        issues.add("notification_date", NullReason.INVALID_ORDER)

    hospitalization_flag = _parse_code(
        raw.get("HOSPITAL"),
        field_name="hospitalization_flag",
        matrix=SIVEP_YESNO_CODE_MATRIX,
        issues=issues,
    )
    hospitalization_date = _parse_date(
        raw.get("DT_INTERNA"), field_name="hospitalization_date", watermark=watermark, issues=issues
    )
    if hospitalization_date is not None and hospitalization_date < symptom_onset:
        hospitalization_date = None
        issues.add("hospitalization_date", NullReason.INVALID_ORDER)

    icu_flag = _parse_code(
        raw.get("UTI"), field_name="icu_flag", matrix=SIVEP_YESNO_CODE_MATRIX, issues=issues
    )
    icu_entry_date = _parse_date(
        raw.get("DT_ENTUTI"), field_name="icu_entry_date", watermark=watermark, issues=issues
    )
    if icu_entry_date is not None and icu_entry_date < symptom_onset:
        icu_entry_date = None
        issues.add("icu_entry_date", NullReason.INVALID_ORDER)
    icu_exit_date = _parse_date(
        raw.get("DT_SAIDUTI"), field_name="icu_exit_date", watermark=watermark, issues=issues
    )
    if icu_exit_date is not None and (icu_entry_date is None or icu_exit_date < icu_entry_date):
        icu_exit_date = None
        issues.add("icu_exit_date", NullReason.INVALID_ORDER)

    evolution = _parse_code(
        raw.get("EVOLUCAO"),
        field_name="evolution",
        matrix=SIVEP_EVOLUTION_CODE_MATRIX,
        issues=issues,
    )
    evolution_date = _parse_date(
        raw.get("DT_EVOLUCA"), field_name="evolution_date", watermark=watermark, issues=issues
    )
    if evolution == SivepEvolutionCode.DEATH_OTHER and evolution_date is not None:
        evolution_date = None
        issues.add("evolution_date", NullReason.FIELD_DISABLED_BY_EVOLUTION)
    elif evolution_date is not None and evolution_date < symptom_onset:
        evolution_date = None
        issues.add("evolution_date", NullReason.INVALID_ORDER)

    closure_date = _parse_date(
        raw.get("DT_ENCERRA"), field_name="closure_date", watermark=watermark, issues=issues
    )
    if closure_date is not None and closure_date < symptom_onset:
        closure_date = None
        issues.add("closure_date", NullReason.INVALID_ORDER)
    digitization_date = _parse_datetime(
        raw.get("DT_DIGITA"), field_name="digitization_date", issues=issues
    )
    if (
        digitization_date is not None
        and notification_date is not None
        and digitization_date.date() < notification_date
    ):
        digitization_date = None
        issues.add("digitization_date", NullReason.INVALID_ORDER)

    row = SivepCanonicalRow(
        year=year,
        source_sha256=source_sha256,
        notification_key=notification_key,
        notification_date=notification_date,
        symptom_onset=symptom_onset,
        hospitalization_flag=hospitalization_flag,
        hospitalization_date=hospitalization_date,
        hospitalization_uf=_parse_uf(
            raw.get("SG_UF_INTE"), field_name="hospitalization_uf", issues=issues
        ),
        icu_flag=icu_flag,
        icu_entry_date=icu_entry_date,
        icu_exit_date=icu_exit_date,
        evolution=evolution,
        evolution_date=evolution_date,
        closure_date=closure_date,
        digitization_date=digitization_date,
        residence_uf=_parse_uf(raw.get("SG_UF"), field_name="residence_uf", issues=issues),
    )
    completeness = canonical_completeness(row)
    return _ParsedRow(row, completeness, canonical_row_sha256(row), issues), issues


def _make_result(
    *,
    total: int,
    accepted: int,
    quarantined: int,
    deduplicated: int,
    issues: _IssueCounters,
    completeness: float,
    output_path: Path | None = None,
    output_sha256: str | None = None,
) -> SivepNormalizationResult:
    blocked = accepted == 0
    quality_state = QualityState.BLOCKED if blocked else evaluate_quality_state(completeness)
    return SivepNormalizationResult(
        counts=NormalizationCounts(
            total_input=total,
            accepted=accepted,
            quarantined=quarantined,
            deduplicated=deduplicated,
        ),
        reasons=issues.result(),
        completeness=completeness,
        quality_state=quality_state,
        blocked=blocked,
        blocker_reason="no valid SIVEP rows" if blocked else None,
        output_path=str(output_path) if output_path is not None else None,
        output_sha256=output_sha256,
    )


def normalize_sivep_rows(
    rows: Iterable[Mapping[str, object]],
    *,
    source_sha256: str,
    year: Literal[2025, 2026],
    watermark: dt.date,
) -> tuple[tuple[SivepCanonicalRow, ...], SivepNormalizationResult]:
    winners: dict[str, _ParsedRow] = {}
    issues = _IssueCounters()
    total = quarantined = deduplicated = 0
    for raw in rows:
        total += 1
        parsed, row_issues = _parse_row(
            raw, source_sha256=source_sha256, year=year, watermark=watermark
        )
        issues.merge(row_issues)
        if parsed is None:
            quarantined += 1
            continue
        previous = winners.get(parsed.row.notification_key)
        if previous is None:
            winners[parsed.row.notification_key] = parsed
            continue
        deduplicated += 1
        if parsed.completeness > previous.completeness or (
            parsed.completeness == previous.completeness and parsed.row_hash < previous.row_hash
        ):
            winners[parsed.row.notification_key] = parsed

    ordered = tuple(winners[key].row for key in sorted(winners))
    max_fields = len(SIVEP_CANONICAL_COMPLETENESS_FIELDS) * len(winners)
    completeness = (
        sum(item.completeness for item in winners.values()) / max_fields if max_fields else 0.0
    )
    return ordered, _make_result(
        total=total,
        accepted=len(winners),
        quarantined=quarantined,
        deduplicated=deduplicated,
        issues=issues,
        completeness=completeness,
    )


def normalize_sivep_csv_to_jsonl(
    input_path: Path,
    output_path: Path,
    *,
    source_sha256: str,
    year: Literal[2025, 2026],
    watermark: dt.date,
) -> SivepNormalizationResult:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    issues = _IssueCounters()
    total = quarantined = deduplicated = 0
    with tempfile.TemporaryDirectory(prefix="srag-normalize-") as directory:
        connection = sqlite3.connect(Path(directory) / "dedup.sqlite3")
        try:
            connection.execute(
                "CREATE TABLE winners (notification_key TEXT PRIMARY KEY, "
                "completeness INTEGER NOT NULL, row_hash TEXT NOT NULL, "
                "row_json TEXT NOT NULL)"
            )
            for raw in iter_csv_rows(input_path):
                total += 1
                parsed, row_issues = _parse_row(
                    raw, source_sha256=source_sha256, year=year, watermark=watermark
                )
                issues.merge(row_issues)
                if parsed is None:
                    quarantined += 1
                    continue
                row_json = parsed.row.model_dump_json()
                cursor = connection.execute(
                    "INSERT OR IGNORE INTO winners VALUES (?, ?, ?, ?)",
                    (parsed.row.notification_key, parsed.completeness, parsed.row_hash, row_json),
                )
                if cursor.rowcount == 0:
                    deduplicated += 1
                    connection.execute(
                        "UPDATE winners SET completeness=?, row_hash=?, row_json=? "
                        "WHERE notification_key=? AND (completeness < ? OR "
                        "(completeness = ? AND row_hash > ?))",
                        (
                            parsed.completeness,
                            parsed.row_hash,
                            row_json,
                            parsed.row.notification_key,
                            parsed.completeness,
                            parsed.completeness,
                            parsed.row_hash,
                        ),
                    )
            connection.commit()
            accepted, completeness_sum = connection.execute(
                "SELECT COUNT(*), COALESCE(SUM(completeness), 0) FROM winners"
            ).fetchone()
            temporary_output = output_path.with_name(f".{output_path.name}.tmp")
            digest = hashlib.sha256()
            with temporary_output.open("wb") as handle:
                for (row_json,) in connection.execute(
                    "SELECT row_json FROM winners ORDER BY notification_key, row_hash"
                ):
                    line = row_json.encode("utf-8") + b"\n"
                    handle.write(line)
                    digest.update(line)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_output, output_path)
        finally:
            connection.close()

    max_fields = len(SIVEP_CANONICAL_COMPLETENESS_FIELDS) * accepted
    completeness = completeness_sum / max_fields if max_fields else 0.0
    return _make_result(
        total=total,
        accepted=accepted,
        quarantined=quarantined,
        deduplicated=deduplicated,
        issues=issues,
        completeness=completeness,
        output_path=output_path,
        output_sha256=digest.hexdigest(),
    )
