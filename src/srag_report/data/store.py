from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import json
import os
import tempfile
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import duckdb
from duckdb import DuckDBPyConnection

from ..domain.models import (
    CnesCanonicalRow,
    IbgePopulationRow,
    PniObservation,
    SivepCanonicalRow,
    SourceContractDocument,
)

_FORBIDDEN_COLUMNS = frozenset({"nu_cpf", "paciente", "nome_mae", "endereco", "cep"})
_TABLES = (
    "sivep_cases",
    "cnes_icu_beds",
    "ibge_population",
    "pni_observations",
    "source_contracts",
)
_SCHEMA = """
CREATE TABLE sivep_cases (
    notification_key VARCHAR PRIMARY KEY,
    notification_date DATE,
    symptom_onset DATE NOT NULL,
    hospitalization_flag UTINYINT,
    hospitalization_date DATE,
    hospitalization_uf VARCHAR,
    icu_flag UTINYINT,
    icu_entry_date DATE,
    icu_exit_date DATE,
    evolution UTINYINT,
    evolution_date DATE,
    closure_date DATE,
    digitization_date VARCHAR,
    residence_uf VARCHAR,
    year USMALLINT NOT NULL,
    source_sha256 VARCHAR NOT NULL
);
CREATE TABLE cnes_icu_beds (
    competencia INTEGER NOT NULL,
    uf VARCHAR NOT NULL,
    cod_leito USMALLINT NOT NULL,
    qt_exist INTEGER NOT NULL,
    source_sha256 VARCHAR NOT NULL
);
CREATE TABLE ibge_population (
    year USMALLINT NOT NULL,
    geography VARCHAR NOT NULL,
    population_official UBIGINT NOT NULL,
    reference_date DATE NOT NULL,
    source_sha256 VARCHAR NOT NULL
);
CREATE TABLE pni_observations (
    campaign_year USMALLINT NOT NULL,
    immunobiological VARCHAR NOT NULL,
    population_scope_json VARCHAR NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    numerator UBIGINT NOT NULL,
    denominator UBIGINT NOT NULL,
    coverage_pct DECIMAL(7, 2) NOT NULL,
    published_at VARCHAR NOT NULL,
    source_label VARCHAR NOT NULL,
    is_nationwide BOOLEAN NOT NULL,
    is_golden BOOLEAN NOT NULL
);
CREATE TABLE source_contracts (
    contract_version VARCHAR NOT NULL,
    contract_date DATE NOT NULL,
    contract_json VARCHAR NOT NULL
);
"""


@dataclass(frozen=True, slots=True)
class SnapshotArtifact:
    path: Path
    content_sha256: str
    file_sha256: str
    table_counts: Mapping[str, int]


def _sivep_values(row: SivepCanonicalRow) -> tuple[object, ...]:
    return (
        row.notification_key,
        row.notification_date,
        row.symptom_onset,
        int(row.hospitalization_flag) if row.hospitalization_flag is not None else None,
        row.hospitalization_date,
        row.hospitalization_uf,
        int(row.icu_flag) if row.icu_flag is not None else None,
        row.icu_entry_date,
        row.icu_exit_date,
        int(row.evolution) if row.evolution is not None else None,
        row.evolution_date,
        row.closure_date,
        row.digitization_date.isoformat() if row.digitization_date is not None else None,
        row.residence_uf,
        row.year,
        row.source_sha256,
    )


def _cnes_values(row: CnesCanonicalRow) -> tuple[object, ...]:
    return row.competencia, row.uf, row.cod_leito, row.qt_exist, row.source_sha256


def _ibge_values(row: IbgePopulationRow) -> tuple[object, ...]:
    return (
        row.year,
        row.geography,
        row.population_official,
        row.reference_date,
        row.source_sha256,
    )


def _pni_values(row: PniObservation) -> tuple[object, ...]:
    return (
        row.campaign_year,
        row.immunobiological,
        json.dumps(sorted(row.population_scope), separators=(",", ":")),
        row.period_start,
        row.period_end,
        row.numerator,
        row.denominator,
        row.coverage_pct,
        row.published_at.isoformat(),
        row.source_label,
        row.is_nationwide,
        row.is_golden,
    )


def _insert_many(
    connection: DuckDBPyConnection,
    sql: str,
    rows: list[tuple[object, ...]],
) -> None:
    if rows:
        connection.executemany(sql, rows)


def materialize_snapshot(
    path: Path,
    *,
    sivep_rows: Iterable[SivepCanonicalRow],
    cnes_rows: Iterable[CnesCanonicalRow],
    ibge_rows: Iterable[IbgePopulationRow],
    pni_rows: Iterable[PniObservation] = (),
    source_contracts: Iterable[SourceContractDocument] = (),
) -> SnapshotArtifact:
    """Create a minimized DuckDB snapshot and atomically publish it at ``path``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    temporary_path.unlink()

    try:
        with duckdb.connect(
            temporary_path,
            config={"threads": 1, "storage_compatibility_version": "v1.0.0"},
        ) as connection:
            connection.execute("BEGIN TRANSACTION")
            connection.execute(_SCHEMA)
            _insert_many(
                connection,
                "INSERT INTO sivep_cases VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                sorted((_sivep_values(row) for row in sivep_rows), key=lambda item: str(item[0])),
            )
            _insert_many(
                connection,
                "INSERT INTO cnes_icu_beds VALUES (?, ?, ?, ?, ?)",
                sorted((_cnes_values(row) for row in cnes_rows), key=lambda item: item[:3]),
            )
            _insert_many(
                connection,
                "INSERT INTO ibge_population VALUES (?, ?, ?, ?, ?)",
                sorted((_ibge_values(row) for row in ibge_rows), key=lambda item: item[:2]),
            )
            _insert_many(
                connection,
                "INSERT INTO pni_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                sorted((_pni_values(row) for row in pni_rows), key=lambda item: item[:5]),
            )
            _insert_many(
                connection,
                "INSERT INTO source_contracts VALUES (?, ?, ?)",
                sorted(
                    (
                        (
                            contract.contract_version,
                            contract.contract_date,
                            contract.model_dump_json(),
                        )
                        for contract in source_contracts
                    ),
                    key=lambda item: item[:2],
                ),
            )
            connection.execute("COMMIT")
            connection.execute("CHECKPOINT")
        os.replace(temporary_path, path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise

    content_sha256 = logical_snapshot_sha256(path)
    with path.open("rb") as handle:
        file_sha256 = hashlib.file_digest(handle, "sha256").hexdigest()
    return SnapshotArtifact(
        path=path,
        content_sha256=content_sha256,
        file_sha256=file_sha256,
        table_counts=snapshot_table_counts(path),
    )


@contextlib.contextmanager
def open_snapshot(path: Path) -> Iterator[DuckDBPyConnection]:
    """Open an existing snapshot in DuckDB's database-level read-only mode."""
    with duckdb.connect(path, read_only=True) as connection:
        yield connection


def _table_count(connection: DuckDBPyConnection, table: str) -> int:
    row = connection.execute(f"SELECT count(*) FROM {table}").fetchone()
    if row is None:
        raise RuntimeError(f"count query returned no row for {table}")
    return int(row[0])


def snapshot_table_counts(path: Path) -> dict[str, int]:
    with open_snapshot(path) as connection:
        return {table: _table_count(connection, table) for table in _TABLES}


def _json_value(value: object) -> object:
    if isinstance(value, dt.date | dt.datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def logical_snapshot_sha256(path: Path) -> str:
    """Hash fixed-schema contents with explicit ordering and canonical JSON encoding."""
    digest = hashlib.sha256()
    with open_snapshot(path) as connection:
        for table in _TABLES:
            digest.update(table.encode())
            digest.update(b"\n")
            rows = connection.execute(f"SELECT * FROM {table} ORDER BY ALL").fetchall()
            for row in rows:
                payload = json.dumps(
                    [_json_value(value) for value in row],
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                digest.update(payload.encode())
                digest.update(b"\n")
    return digest.hexdigest()


def assert_minimized_schema(path: Path) -> None:
    """Fail if a published table exposes a prohibited raw clinical identifier column."""
    with open_snapshot(path) as connection:
        columns = connection.execute(
            "SELECT lower(column_name) FROM information_schema.columns"
        ).fetchall()
    forbidden = sorted({column[0] for column in columns} & _FORBIDDEN_COLUMNS)
    if forbidden:
        raise ValueError(f"snapshot contains forbidden columns: {', '.join(forbidden)}")
