from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from srag_report.domain.models import PniObservation
from srag_report.domain.source import QualityState
from srag_report.metrics.calculations import (
    case_growth,
    daily_case_series,
    hospital_case_fatality,
    icu_pressure,
    icu_use,
    influenza_coverage,
    monthly_case_series,
    population_mortality,
)
from srag_report.metrics.enums import MetricState, PointState, UnavailableReason

_AS_OF = dt.date(2026, 7, 28)


@pytest.mark.parametrize(
    ("previous", "current", "expected", "state"),
    [
        (100, 125, 25.0, MetricState.AVAILABLE),
        (100, 75, -25.0, MetricState.AVAILABLE),
        (0, 0, 0.0, MetricState.STABLE_ZERO),
        (0, 10, None, MetricState.NEW_ACTIVITY),
    ],
)
def test_case_growth_states(
    previous: int, current: int, expected: float | None, state: MetricState
) -> None:
    result = case_growth(
        previous_cases=previous,
        current_cases=current,
        as_of=_AS_OF,
        snapshot_id="snapshot",
        completeness=1.0,
    )
    assert result.value == expected
    assert result.state is state
    assert result.period_end == dt.date(2026, 7, 11)


def test_low_completeness_blocks_numeric_growth() -> None:
    result = case_growth(
        previous_cases=100,
        current_cases=125,
        as_of=_AS_OF,
        snapshot_id="snapshot",
        completeness=0.69,
    )
    assert result.value is None
    assert result.state is MetricState.UNAVAILABLE
    assert result.reason is UnavailableReason.COMPLETENESS_LOW
    assert result.quality.state is QualityState.UNAVAILABLE


def test_population_mortality_per_100k() -> None:
    result = population_mortality(
        deaths=213,
        population=213_000_000,
        as_of=_AS_OF,
        snapshot_id="snapshot",
        completeness=1.0,
    )
    assert result.value == 0.1
    assert result.period_start == dt.date(2026, 6, 14)
    assert result.period_end == dt.date(2026, 7, 11)


def test_fatality_uses_four_week_mature_cohort_and_known_outcomes() -> None:
    result = hospital_case_fatality(
        deaths=20,
        known_outcomes=100,
        unknown_outcomes=7,
        as_of=_AS_OF,
        snapshot_id="snapshot",
        completeness=1.0,
    )
    assert result.value == 20.0
    assert (result.period_end - result.period_start).days == 27
    assert "7" in result.limitations[0]
    assert "suplementar" in result.label.casefold()


def test_icu_use_is_supplementary_not_occupancy() -> None:
    result = icu_use(
        icu_admissions=30,
        known_icu_status=120,
        period_start=dt.date(2026, 6, 1),
        period_end=dt.date(2026, 6, 30),
        snapshot_id="snapshot",
        completeness=1.0,
    )
    assert result.value == 25.0
    assert "suplementar" in result.label.casefold()
    assert "ocupação" not in result.label.casefold()


def test_icu_pressure_uses_patient_days_and_bed_days() -> None:
    result = icu_pressure(
        patient_days=900,
        bed_days=3000,
        period_start=dt.date(2026, 6, 1),
        period_end=dt.date(2026, 6, 30),
        excluded_open_stays=2,
        snapshot_id="snapshot",
        completeness=1.0,
    )
    assert result.value == 30.0
    assert result.numerator == 900.0
    assert result.denominator == 3000.0
    assert "Pressão estimada" in result.label
    assert "Não é ocupação" in result.limitations[0]


def test_icu_pressure_above_100_is_unavailable_not_truncated() -> None:
    result = icu_pressure(
        patient_days=1001,
        bed_days=1000,
        period_start=dt.date(2026, 6, 1),
        period_end=dt.date(2026, 6, 30),
        excluded_open_stays=0,
        snapshot_id="snapshot",
        completeness=1.0,
    )
    assert result.value is None
    assert result.state is MetricState.UNAVAILABLE
    assert result.reason is UnavailableReason.RATIO_ABOVE_100_PCT


def _pni(published: dt.datetime) -> PniObservation:
    return PniObservation(
        campaign_year=2026,
        immunobiological="INF3",
        population_scope=frozenset({"NE", "CO", "S", "SE"}),
        period_start=dt.date(2026, 3, 1),
        period_end=dt.date(2026, 5, 31),
        numerator=61_700,
        denominator=100_000,
        coverage_pct=Decimal("61.70"),
        published_at=published,
        source_label="synthetic-pni",
        is_nationwide=False,
        is_golden=False,
    )


def test_influenza_scoped_observation_never_claims_nationwide() -> None:
    result = influenza_coverage(
        observation=_pni(dt.datetime(2026, 7, 25, tzinfo=dt.UTC)),
        as_of=dt.date(2026, 7, 26),
        snapshot_id="snapshot",
        completeness=1.0,
    )
    assert result.value == 61.7
    assert result.population_scope == frozenset({"NE", "CO", "S", "SE"})
    assert "regional" in result.limitations[0].casefold()


def test_influenza_after_cutoff_exposes_no_numbers() -> None:
    result = influenza_coverage(
        observation=_pni(dt.datetime(2026, 7, 27, tzinfo=dt.UTC)),
        as_of=dt.date(2026, 7, 26),
        snapshot_id="snapshot",
        completeness=1.0,
    )
    assert result.value is None
    assert result.numerator is None
    assert result.denominator is None
    assert result.reason is UnavailableReason.NOT_PUBLISHED_BY_CUTOFF


def test_daily_series_zero_fills_only_covered_period() -> None:
    result = daily_case_series(
        {_AS_OF: 3},
        coverage_start=_AS_OF - dt.timedelta(days=40),
        coverage_end=_AS_OF,
        as_of=_AS_OF,
        snapshot_id="snapshot",
        completeness=1.0,
    )
    assert result is not None
    assert len(result.points) == 30
    assert result.points[-1].value == 3
    assert result.points[0].value == 0
    assert all(point.state is PointState.PROVISIONAL for point in result.points[-14:])


def test_daily_series_outside_coverage_is_unavailable() -> None:
    assert (
        daily_case_series(
            {},
            coverage_start=_AS_OF - dt.timedelta(days=20),
            coverage_end=_AS_OF,
            as_of=_AS_OF,
            snapshot_id="snapshot",
            completeness=1.0,
        )
        is None
    )


def test_monthly_series_has_12_complete_prior_months() -> None:
    result = monthly_case_series(
        {dt.date(2026, 6, 1): 10},
        coverage_start=dt.date(2025, 1, 1),
        coverage_end=dt.date(2026, 6, 30),
        as_of=_AS_OF,
        snapshot_id="snapshot",
        completeness=1.0,
    )
    assert result is not None
    assert len(result.points) == 12
    assert result.points[0].period == dt.date(2025, 7, 1)
    assert result.points[-1].period == dt.date(2026, 6, 1)
    assert result.period_end == dt.date(2026, 6, 30)
