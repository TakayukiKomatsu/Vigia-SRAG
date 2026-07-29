from __future__ import annotations

import datetime as dt
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest

from srag_report.data.store import (
    SnapshotArtifact,
    assert_minimized_schema,
    logical_snapshot_sha256,
    materialize_snapshot,
    open_snapshot,
)
from srag_report.domain.models import (
    CnesCanonicalRow,
    IbgePopulationRow,
    PniObservation,
    SivepCanonicalRow,
)
from srag_report.domain.source import SivepEvolutionCode, SivepYesNoCode

_SHA = "0" * 64


def _sivep() -> SivepCanonicalRow:
    return SivepCanonicalRow(
        year=2026,
        notification_key="SYNTH-STORE-1",
        notification_date=dt.date(2026, 6, 3),
        symptom_onset=dt.date(2026, 6, 1),
        hospitalization_flag=SivepYesNoCode.YES,
        hospitalization_date=dt.date(2026, 6, 4),
        hospitalization_uf="SP",
        icu_flag=SivepYesNoCode.NO,
        icu_entry_date=None,
        icu_exit_date=None,
        evolution=SivepEvolutionCode.CURE,
        evolution_date=dt.date(2026, 6, 10),
        closure_date=dt.date(2026, 6, 11),
        digitization_date=dt.datetime(2026, 6, 3, 12, tzinfo=dt.UTC),
        residence_uf="SP",
        source_sha256=_SHA,
    )


def _cnes() -> CnesCanonicalRow:
    return CnesCanonicalRow(
        competencia=202606,
        uf="SP",
        cod_leito=61,
        qt_exist=10,
        source_sha256=_SHA,
    )


def _ibge() -> IbgePopulationRow:
    return IbgePopulationRow(
        year=2025,
        geography="BR",
        population_official=213_421_037,
        reference_date=dt.date(2025, 7, 1),
        source_sha256=_SHA,
    )


def _pni() -> PniObservation:
    return PniObservation(
        campaign_year=2026,
        immunobiological="INF3",
        population_scope=frozenset({"NE", "CO", "S", "SE"}),
        period_start=dt.date(2026, 3, 1),
        period_end=dt.date(2026, 5, 31),
        numerator=61_700,
        denominator=100_000,
        coverage_pct=Decimal("61.70"),
        published_at=dt.datetime(2026, 7, 25, 12, tzinfo=dt.UTC),
        source_label="synthetic-pni-observation",
        is_nationwide=False,
        is_golden=False,
    )


def _materialize(path: Path) -> SnapshotArtifact:
    return materialize_snapshot(
        path,
        sivep_rows=[_sivep()],
        cnes_rows=[_cnes()],
        ibge_rows=[_ibge()],
        pni_rows=[_pni()],
    )


def test_materialization_has_stable_logical_digest(tmp_path: Path) -> None:
    first = _materialize(tmp_path / "first.duckdb")
    second = _materialize(tmp_path / "second.duckdb")
    assert first.content_sha256 == second.content_sha256
    assert first.content_sha256 == logical_snapshot_sha256(first.path)
    assert first.table_counts == {
        "sivep_cases": 1,
        "cnes_icu_beds": 1,
        "ibge_population": 1,
        "pni_observations": 1,
        "source_contracts": 0,
    }
    assert len(first.file_sha256) == 64


def test_snapshot_consumer_is_database_read_only(tmp_path: Path) -> None:
    artifact = _materialize(tmp_path / "snapshot.duckdb")
    with open_snapshot(artifact.path) as connection:
        assert connection.execute("SELECT notification_key FROM sivep_cases").fetchone() == (
            "SYNTH-STORE-1",
        )
        with pytest.raises(duckdb.Error):
            connection.execute("DELETE FROM sivep_cases")


def test_snapshot_schema_is_minimized(tmp_path: Path) -> None:
    artifact = _materialize(tmp_path / "snapshot.duckdb")
    assert_minimized_schema(artifact.path)
    with open_snapshot(artifact.path) as connection:
        names = {
            row[0]
            for row in connection.execute(
                "SELECT lower(column_name) FROM information_schema.columns"
            ).fetchall()
        }
    assert names.isdisjoint({"nu_cpf", "paciente", "nome_mae", "endereco", "cep"})


def test_minimization_guard_rejects_forbidden_column(tmp_path: Path) -> None:
    path = tmp_path / "bad.duckdb"
    with duckdb.connect(path) as connection:
        connection.execute("CREATE TABLE bad_table (nome_mae VARCHAR)")
    with pytest.raises(ValueError, match="nome_mae"):
        assert_minimized_schema(path)
