from __future__ import annotations

import datetime as dt
from decimal import Decimal
from pathlib import Path

import pytest

from srag_report.data.store import materialize_snapshot
from srag_report.domain.models import (
    CnesCanonicalRow,
    IbgePopulationRow,
    PniObservation,
    SivepCanonicalRow,
)
from srag_report.domain.source import SivepEvolutionCode, SivepYesNoCode
from srag_report.metrics.enums import MetricId, MetricState
from srag_report.metrics.query import compute_metric_package
from srag_report.metrics.time import WatermarkError

_SHA = "0" * 64
_AS_OF = dt.date(2026, 7, 28)


def _row(
    key: str,
    onset: dt.date,
    *,
    hospitalized: SivepYesNoCode = SivepYesNoCode.NO,
    icu: SivepYesNoCode = SivepYesNoCode.NO,
    evolution: SivepEvolutionCode = SivepEvolutionCode.CURE,
    evolution_date: dt.date | None = None,
    icu_entry: dt.date | None = None,
    icu_exit: dt.date | None = None,
) -> SivepCanonicalRow:
    return SivepCanonicalRow(
        year=2026 if onset.year == 2026 else 2025,
        source_sha256=_SHA,
        notification_key=key,
        notification_date=onset,
        symptom_onset=onset,
        hospitalization_flag=hospitalized,
        hospitalization_date=onset if hospitalized is SivepYesNoCode.YES else None,
        hospitalization_uf="SP" if hospitalized is SivepYesNoCode.YES else None,
        icu_flag=icu,
        icu_entry_date=icu_entry,
        icu_exit_date=icu_exit,
        evolution=evolution,
        evolution_date=evolution_date,
        closure_date=onset + dt.timedelta(days=10),
        digitization_date=dt.datetime.combine(onset, dt.time(12), tzinfo=dt.UTC),
        residence_uf="SP",
    )


def _snapshot(tmp_path: Path) -> Path:
    rows = [
        _row("coverage-start", dt.date(2025, 7, 1)),
        _row("coverage-end", _AS_OF),
        _row("previous-1", dt.date(2026, 6, 29)),
        _row("previous-2", dt.date(2026, 7, 1)),
        _row(
            "current-death",
            dt.date(2026, 7, 5),
            hospitalized=SivepYesNoCode.YES,
            icu=SivepYesNoCode.YES,
            evolution=SivepEvolutionCode.DEATH_SRAG,
            evolution_date=dt.date(2026, 7, 8),
        ),
        _row("current-2", dt.date(2026, 7, 7), hospitalized=SivepYesNoCode.YES),
        _row("current-3", dt.date(2026, 7, 10)),
        _row(
            "mature-death",
            dt.date(2026, 6, 10),
            hospitalized=SivepYesNoCode.YES,
            evolution=SivepEvolutionCode.DEATH_SRAG,
            evolution_date=dt.date(2026, 6, 20),
        ),
        _row("mature-cure", dt.date(2026, 6, 11), hospitalized=SivepYesNoCode.YES),
        _row(
            "mature-other",
            dt.date(2026, 6, 12),
            hospitalized=SivepYesNoCode.YES,
            evolution=SivepEvolutionCode.DEATH_OTHER,
        ),
        _row(
            "mature-unknown",
            dt.date(2026, 6, 13),
            hospitalized=SivepYesNoCode.YES,
            evolution=SivepEvolutionCode.UNKNOWN,
        ),
        _row(
            "icu-closed",
            dt.date(2026, 6, 15),
            hospitalized=SivepYesNoCode.YES,
            icu=SivepYesNoCode.YES,
            icu_entry=dt.date(2026, 6, 1),
            icu_exit=dt.date(2026, 6, 3),
        ),
        _row(
            "icu-open",
            dt.date(2026, 6, 16),
            hospitalized=SivepYesNoCode.YES,
            icu=SivepYesNoCode.YES,
            icu_entry=dt.date(2026, 6, 2),
        ),
    ]
    artifact = materialize_snapshot(
        tmp_path / "snapshot.duckdb",
        sivep_rows=rows,
        cnes_rows=[
            CnesCanonicalRow(
                competencia=202606,
                uf="SP",
                cod_leito=61,
                qt_exist=10,
                source_sha256=_SHA,
            )
        ],
        ibge_rows=[
            IbgePopulationRow(
                year=2025,
                geography="BR",
                population_official=213_421_037,
                reference_date=dt.date(2025, 7, 1),
                source_sha256=_SHA,
            )
        ],
        pni_rows=[
            PniObservation(
                campaign_year=2026,
                immunobiological="INF3",
                population_scope=frozenset({"NE", "CO", "S", "SE"}),
                period_start=dt.date(2026, 3, 1),
                period_end=dt.date(2026, 5, 31),
                numerator=61_700,
                denominator=100_000,
                coverage_pct=Decimal("61.70"),
                published_at=dt.datetime(2026, 7, 25, tzinfo=dt.UTC),
                source_label="synthetic-pni",
                is_nationwide=False,
                is_golden=False,
            )
        ],
    )
    return artifact.path


def test_compute_full_metric_package_from_read_only_duckdb(tmp_path: Path) -> None:
    package = compute_metric_package(
        _snapshot(tmp_path),
        snapshot_id="snapshot",
        watermark=_AS_OF,
        requested_as_of=_AS_OF,
    )
    metrics = {metric.metric_id: metric for metric in package.metrics}
    assert metrics[MetricId.CASE_GROWTH].value == 50.0
    assert metrics[MetricId.MORTALITY_PER_100K].numerator == 2.0
    assert metrics[MetricId.HOSPITAL_CFR].value == pytest.approx(20.0)
    assert metrics[MetricId.ICU_PRESSURE].numerator == 3.0
    assert metrics[MetricId.ICU_PRESSURE].denominator == 300.0
    assert "1 permanências" in metrics[MetricId.ICU_PRESSURE].limitations[1]
    assert metrics[MetricId.INFLUENZA_COVERAGE].value == 61.7
    assert len(package.series) == 2
    assert {len(series.points) for series in package.series} == {12, 30}


def test_query_rejects_as_of_after_watermark_before_calculation(tmp_path: Path) -> None:
    path = _snapshot(tmp_path)
    with pytest.raises(WatermarkError):
        compute_metric_package(
            path,
            snapshot_id="snapshot",
            watermark=_AS_OF,
            requested_as_of=_AS_OF + dt.timedelta(days=1),
        )


def test_structural_blocker_removes_metric_value(tmp_path: Path) -> None:
    package = compute_metric_package(
        _snapshot(tmp_path),
        snapshot_id="snapshot",
        watermark=_AS_OF,
        blockers={MetricId.CASE_GROWTH: "critical onset column missing"},
    )
    growth = next(metric for metric in package.metrics if metric.metric_id is MetricId.CASE_GROWTH)
    assert growth.state is MetricState.UNAVAILABLE
    assert growth.value is None
