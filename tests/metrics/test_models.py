"""
T-MT-1 metric/series/chart model contract tests.

Defends:
- State/value consistency (AVAILABLE/WARNING need value; UNAVAILABLE/NEW_ACTIVITY
  require None; STABLE_ZERO requires 0.0 exactly).
- reason required when state=UNAVAILABLE.
- geography is always "BR".
- source_ids is non-empty on every result type.
- population_scope is None by default; set explicitly for influenza.
- period_end >= period_start.
- SeriesPoint.value >= 0.
- ChartResult.sha256 must be 64 lowercase hex characters.
- extra="forbid" rejects unknown fields on all models.
- QualityResult completeness is bounded [0, 1].
"""

from __future__ import annotations

import datetime

import pytest
from pydantic import ValidationError

from srag_report.domain.source import QualityState
from srag_report.metrics.enums import (
    MetricFormula,
    MetricId,
    MetricState,
    PointState,
    SeriesGranularity,
    UnavailableReason,
)
from srag_report.metrics.models import (
    ChartResult,
    MetricResult,
    QualityResult,
    SeriesPoint,
    SeriesResult,
)

# ---------------------------------------------------------------------------
# Shared builders
# ---------------------------------------------------------------------------

_GOOD_SHA256 = "a" * 64
_SNAP = "snap-2026-07-28"
_SRC = ("sivep",)
_START = datetime.date(2026, 6, 29)
_END = datetime.date(2026, 7, 28)
_WATERMARK = datetime.date(2026, 7, 28)


def _quality(
    completeness: float = 0.95, state: QualityState = QualityState.AVAILABLE
) -> QualityResult:
    return QualityResult(completeness=completeness, state=state)


def _metric(**overrides: object) -> MetricResult:
    """Build a minimal valid AVAILABLE MetricResult."""
    defaults: dict[str, object] = {
        "metric_id": MetricId.CASE_GROWTH,
        "label": "Case growth",
        "value": 25.0,
        "state": MetricState.AVAILABLE,
        "unit": "%",
        "period_start": _START,
        "period_end": _END,
        "snapshot_id": _SNAP,
        "formula_version": MetricFormula.CASE_GROWTH_V1,
        "quality": _quality(),
        "source_ids": _SRC,
    }
    defaults.update(overrides)
    return MetricResult(**defaults)  # type: ignore[arg-type]


def _point(
    period: datetime.date = _END, value: int = 10, state: PointState = PointState.STABLE
) -> SeriesPoint:
    return SeriesPoint(period=period, value=value, state=state)


# ---------------------------------------------------------------------------
# QualityResult
# ---------------------------------------------------------------------------


def test_quality_result_available() -> None:
    q = _quality(0.95, QualityState.AVAILABLE)
    assert q.completeness == 0.95
    assert q.state == QualityState.AVAILABLE
    assert q.blocker is None


def test_quality_result_warning() -> None:
    q = _quality(0.80, QualityState.WARNING)
    assert q.state == QualityState.WARNING


def test_quality_result_unavailable() -> None:
    q = _quality(0.60, QualityState.UNAVAILABLE)
    assert q.state == QualityState.UNAVAILABLE


def test_quality_result_blocked_with_blocker_text() -> None:
    q = QualityResult(
        completeness=0.0, state=QualityState.BLOCKED, blocker="missing critical column"
    )
    assert q.state == QualityState.BLOCKED
    assert q.blocker is not None


def test_quality_result_completeness_below_zero_rejected() -> None:
    with pytest.raises(ValidationError):
        QualityResult(completeness=-0.01, state=QualityState.UNAVAILABLE)


def test_quality_result_completeness_above_one_rejected() -> None:
    with pytest.raises(ValidationError):
        QualityResult(completeness=1.01, state=QualityState.AVAILABLE)


def test_quality_result_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        QualityResult(completeness=0.95, state=QualityState.AVAILABLE, extra_key="bad")  # type: ignore[call-arg]


def test_quality_result_is_frozen() -> None:
    q = _quality()
    with pytest.raises(ValidationError):
        q.completeness = 0.5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# MetricResult — valid states
# ---------------------------------------------------------------------------


def test_metric_result_available_valid() -> None:
    m = _metric(value=25.0, state=MetricState.AVAILABLE)
    assert m.value == 25.0
    assert m.geography == "BR"
    assert m.population_scope is None
    assert m.limitations == ()


def test_metric_result_warning_valid() -> None:
    m = _metric(value=12.5, state=MetricState.WARNING, quality=_quality(0.80, QualityState.WARNING))
    assert m.value == 12.5
    assert m.state == MetricState.WARNING


def test_metric_result_stable_zero_value_zero() -> None:
    """state=stable_zero requires value==0.0 exactly."""
    m = _metric(value=0.0, state=MetricState.STABLE_ZERO)
    assert m.value == 0.0
    assert m.state == MetricState.STABLE_ZERO


def test_metric_result_unavailable_value_none_reason_set() -> None:
    """state=unavailable: value must be None, reason must be set."""
    m = _metric(
        value=None,
        state=MetricState.UNAVAILABLE,
        reason=UnavailableReason.COMPLETENESS_LOW,
        quality=_quality(0.60, QualityState.UNAVAILABLE),
    )
    assert m.value is None
    assert m.reason == UnavailableReason.COMPLETENESS_LOW


def test_metric_result_new_activity_value_none() -> None:
    """state=new_activity: value must be None (no infinite published)."""
    m = _metric(
        value=None,
        state=MetricState.NEW_ACTIVITY,
        numerator=4.0,
        denominator=0.0,
    )
    assert m.value is None
    assert m.state == MetricState.NEW_ACTIVITY


def test_metric_result_icu_pressure_above_100_unavailable() -> None:
    """Ratio > 100 % is state=unavailable with RATIO_ABOVE_100_PCT reason (AC-MT-5)."""
    m = _metric(
        metric_id=MetricId.ICU_PRESSURE,
        formula_version=MetricFormula.ICU_PRESSURE_V1,
        value=None,
        state=MetricState.UNAVAILABLE,
        reason=UnavailableReason.RATIO_ABOVE_100_PCT,
        unit="%",
        numerator=1100.0,
        denominator=1000.0,
        limitations=("ICU pressure exceeds 100%; not published as a valid percentage.",),
    )
    assert m.state == MetricState.UNAVAILABLE
    assert m.reason == UnavailableReason.RATIO_ABOVE_100_PCT
    assert m.value is None
    assert len(m.limitations) == 1


def test_metric_result_influenza_not_published_unavailable() -> None:
    """No eligible influenza observation is unavailable without counts (AC-MT-7)."""
    m = _metric(
        metric_id=MetricId.INFLUENZA_COVERAGE,
        formula_version=MetricFormula.INFLUENZA_COVERAGE_V1,
        value=None,
        state=MetricState.UNAVAILABLE,
        reason=UnavailableReason.NOT_PUBLISHED_BY_CUTOFF,
        unit="%",
        numerator=None,
        denominator=None,
        population_scope=None,
        source_ids=("pni",),
    )
    assert m.value is None
    assert m.population_scope is None


# ---------------------------------------------------------------------------
# MetricResult — invalid states (enforced by model_validator)
# ---------------------------------------------------------------------------


def test_metric_result_available_with_none_value_rejected() -> None:
    """state=available with value=None must be rejected."""
    with pytest.raises(ValidationError, match="non-None value"):
        _metric(value=None, state=MetricState.AVAILABLE)


def test_metric_result_warning_with_none_value_rejected() -> None:
    with pytest.raises(ValidationError, match="non-None value"):
        _metric(value=None, state=MetricState.WARNING)


def test_metric_result_unavailable_with_value_rejected() -> None:
    """state=unavailable with a non-None value must be rejected."""
    with pytest.raises(ValidationError, match="unavailable"):
        _metric(
            value=50.0,
            state=MetricState.UNAVAILABLE,
            reason=UnavailableReason.COMPLETENESS_LOW,
        )


def test_metric_result_unavailable_missing_reason_rejected() -> None:
    """state=unavailable without reason must be rejected."""
    with pytest.raises(ValidationError, match="reason"):
        _metric(value=None, state=MetricState.UNAVAILABLE)


def test_metric_result_stable_zero_nonzero_value_rejected() -> None:
    """state=stable_zero with non-zero value must be rejected."""
    with pytest.raises(ValidationError, match="stable_zero"):
        _metric(value=1.0, state=MetricState.STABLE_ZERO)


def test_metric_result_stable_zero_none_value_rejected() -> None:
    with pytest.raises(ValidationError, match="stable_zero"):
        _metric(value=None, state=MetricState.STABLE_ZERO)


def test_metric_result_new_activity_with_value_rejected() -> None:
    with pytest.raises(ValidationError, match="new_activity"):
        _metric(value=10.0, state=MetricState.NEW_ACTIVITY)


def test_metric_result_period_end_before_start_rejected() -> None:
    with pytest.raises(ValidationError, match="period_end"):
        _metric(period_start=_END, period_end=_START)


def test_metric_result_empty_source_ids_rejected() -> None:
    with pytest.raises(ValidationError, match="source_ids"):
        _metric(source_ids=())


def test_metric_result_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        MetricResult(
            metric_id=MetricId.CASE_GROWTH,
            label="x",
            value=1.0,
            state=MetricState.AVAILABLE,
            unit="%",
            period_start=_START,
            period_end=_END,
            snapshot_id=_SNAP,
            formula_version=MetricFormula.CASE_GROWTH_V1,
            quality=_quality(),
            source_ids=_SRC,
            unknown_field="bad",  # type: ignore[call-arg]
        )


def test_metric_result_is_frozen() -> None:
    m = _metric()
    with pytest.raises(ValidationError):
        m.value = 99.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# MetricResult — geography and population_scope
# ---------------------------------------------------------------------------


def test_metric_result_geography_always_br() -> None:
    m = _metric()
    assert m.geography == "BR"


def test_metric_result_geography_literal_enforced() -> None:
    """Only 'BR' is accepted for geography."""
    with pytest.raises(ValidationError):
        _metric(geography="US")  # type: ignore[arg-type]


def test_metric_result_population_scope_none_by_default() -> None:
    m = _metric()
    assert m.population_scope is None


def test_metric_result_population_scope_set_for_influenza() -> None:
    """Influenza metric carries explicit population_scope (AC-MT-7)."""
    scope = frozenset({"NE", "CO", "S", "SE"})
    m = _metric(
        metric_id=MetricId.INFLUENZA_COVERAGE,
        formula_version=MetricFormula.INFLUENZA_COVERAGE_V1,
        value=72.3,
        state=MetricState.AVAILABLE,
        population_scope=scope,
        source_ids=("pni",),
    )
    assert m.population_scope == scope
    assert "BR" not in m.population_scope  # never nationwide label


def test_metric_result_population_scope_not_nationwide() -> None:
    """A scoped observation must never carry nationwide scope labeling — no 'BR' in scope."""
    scope = frozenset({"NE", "CO", "S", "SE"})
    m = _metric(
        metric_id=MetricId.INFLUENZA_COVERAGE,
        formula_version=MetricFormula.INFLUENZA_COVERAGE_V1,
        value=68.0,
        state=MetricState.AVAILABLE,
        population_scope=scope,
        source_ids=("pni",),
    )
    # population_scope is the set of covered regions, not a geography code
    assert "BR" not in m.population_scope


# ---------------------------------------------------------------------------
# MetricResult — provenance fields
# ---------------------------------------------------------------------------


def test_metric_result_snapshot_id_present() -> None:
    m = _metric()
    assert m.snapshot_id == _SNAP


def test_metric_result_formula_version_present() -> None:
    m = _metric()
    assert m.formula_version == MetricFormula.CASE_GROWTH_V1


def test_metric_result_quality_present() -> None:
    m = _metric()
    assert isinstance(m.quality, QualityResult)


def test_metric_result_limitations_tuple() -> None:
    m = _metric(limitations=("CFR excludes 20 unknown outcomes.",))
    assert len(m.limitations) == 1


# ---------------------------------------------------------------------------
# SeriesPoint
# ---------------------------------------------------------------------------


def test_series_point_valid_stable() -> None:
    p = _point(state=PointState.STABLE)
    assert p.value == 10
    assert p.state == PointState.STABLE


def test_series_point_valid_provisional() -> None:
    p = _point(state=PointState.PROVISIONAL, value=3)
    assert p.state == PointState.PROVISIONAL


def test_series_point_zero_value_valid() -> None:
    p = _point(value=0)
    assert p.value == 0


def test_series_point_negative_value_rejected() -> None:
    with pytest.raises(ValidationError):
        SeriesPoint(period=_END, value=-1, state=PointState.STABLE)


def test_series_point_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        SeriesPoint(period=_END, value=5, state=PointState.STABLE, bad_field="x")  # type: ignore[call-arg]


def test_series_point_is_frozen() -> None:
    p = _point()
    with pytest.raises(ValidationError):
        p.value = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# SeriesResult
# ---------------------------------------------------------------------------


def _series(**overrides: object) -> SeriesResult:
    daily_start = _END - datetime.timedelta(days=29)
    points = tuple(
        _point(
            period=daily_start + datetime.timedelta(days=i),
            state=PointState.STABLE if i < 16 else PointState.PROVISIONAL,
        )
        for i in range(30)
    )
    defaults: dict[str, object] = {
        "series_id": "daily-cases-br",
        "granularity": SeriesGranularity.DAILY,
        "points": points,
        "period_start": daily_start,
        "period_end": _END,
        "snapshot_id": _SNAP,
        "quality": _quality(),
        "source_ids": _SRC,
    }
    defaults.update(overrides)
    return SeriesResult(**defaults)  # type: ignore[arg-type]


def test_series_result_daily_valid() -> None:
    s = _series()
    assert s.granularity == SeriesGranularity.DAILY
    assert len(s.points) == 30
    assert s.geography == "BR"


def test_series_result_monthly_valid() -> None:
    monthly_start = datetime.date(2025, 7, 1)
    points = tuple(
        SeriesPoint(
            period=datetime.date(2025 + (i + 6) // 12, (6 + i) % 12 + 1, 1),
            value=100 + i,
            state=PointState.STABLE,
        )
        for i in range(12)
    )
    s = SeriesResult(
        series_id="monthly-cases-br",
        granularity=SeriesGranularity.MONTHLY,
        points=points,
        period_start=monthly_start,
        period_end=datetime.date(2026, 6, 30),
        snapshot_id=_SNAP,
        quality=_quality(),
        source_ids=_SRC,
    )
    assert len(s.points) == 12
    assert s.granularity == SeriesGranularity.MONTHLY


def test_series_result_empty_source_ids_rejected() -> None:
    with pytest.raises(ValidationError, match="source_ids"):
        _series(source_ids=())


def test_series_result_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        SeriesResult(
            series_id="x",
            granularity=SeriesGranularity.DAILY,
            points=(_point(),),
            period_start=_START,
            period_end=_END,
            snapshot_id=_SNAP,
            quality=_quality(),
            source_ids=_SRC,
            bad_extra="oops",  # type: ignore[call-arg]
        )


def test_series_result_geography_is_br() -> None:
    s = _series()
    assert s.geography == "BR"


def test_series_result_30_points_for_daily_contract() -> None:
    """Daily series must carry exactly 30 points (FR-MT-8 / AC-MT-8)."""
    s = _series()
    assert len(s.points) == 30


def test_series_result_provisional_count_14_for_daily() -> None:
    """Most recent 14 daily points must be PROVISIONAL (FR-MT-8)."""
    s = _series()
    assert all(point.state == PointState.STABLE for point in s.points[:16])
    assert all(point.state == PointState.PROVISIONAL for point in s.points[16:])


def test_series_result_12_points_for_monthly_contract() -> None:
    """Monthly series must carry 12 contiguous complete months (FR-MT-9 / AC-MT-9)."""
    monthly_start = datetime.date(2025, 7, 1)
    points = tuple(
        SeriesPoint(
            period=datetime.date(2025 + (i + 6) // 12, (6 + i) % 12 + 1, 1),
            value=0,
            state=PointState.STABLE,
        )
        for i in range(12)
    )
    s = SeriesResult(
        series_id="monthly-cases-br",
        granularity=SeriesGranularity.MONTHLY,
        points=points,
        period_start=monthly_start,
        period_end=datetime.date(2026, 6, 30),
        snapshot_id=_SNAP,
        quality=_quality(),
        source_ids=_SRC,
    )
    assert len(s.points) == 12


# ---------------------------------------------------------------------------
# ChartResult
# ---------------------------------------------------------------------------


def test_chart_result_valid() -> None:
    c = ChartResult(
        chart_id="chart-daily-cases-br",
        series_id="daily-cases-br",
        path="/tmp/chart_daily.svg",
        sha256=_GOOD_SHA256,
        title="SRAG daily cases — Brazil",
        period="2026-05-29 to 2026-07-28",
        unit="cases",
        source_ids=_SRC,
        watermark=_WATERMARK,
        alt_text="Bar chart of daily SRAG cases in Brazil from 2026-05-29 to 2026-07-28.",
    )
    assert c.sha256 == _GOOD_SHA256
    assert c.watermark == _WATERMARK
    assert c.alt_text.startswith("Bar chart")


def test_chart_result_bad_sha256_rejected() -> None:
    with pytest.raises(ValidationError, match="sha256"):
        ChartResult(
            chart_id="x",
            series_id="y",
            path="/tmp/x.svg",
            sha256="tooshort",
            title="t",
            period="p",
            unit="cases",
            source_ids=_SRC,
            watermark=_WATERMARK,
            alt_text="a",
        )


def test_chart_result_uppercase_sha256_rejected() -> None:
    with pytest.raises(ValidationError, match="sha256"):
        ChartResult(
            chart_id="x",
            series_id="y",
            path="/tmp/x.svg",
            sha256="A" * 64,
            title="t",
            period="p",
            unit="cases",
            source_ids=_SRC,
            watermark=_WATERMARK,
            alt_text="a",
        )


def test_chart_result_empty_source_ids_rejected() -> None:
    with pytest.raises(ValidationError, match="source_ids"):
        ChartResult(
            chart_id="x",
            series_id="y",
            path="/tmp/x.svg",
            sha256=_GOOD_SHA256,
            title="t",
            period="p",
            unit="cases",
            source_ids=(),
            watermark=_WATERMARK,
            alt_text="a",
        )


def test_chart_result_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        ChartResult(
            chart_id="x",
            series_id="y",
            path="/tmp/x.svg",
            sha256=_GOOD_SHA256,
            title="t",
            period="p",
            unit="cases",
            source_ids=_SRC,
            watermark=_WATERMARK,
            alt_text="a",
            not_a_field="bad",  # type: ignore[call-arg]
        )


def test_chart_result_is_frozen() -> None:
    c = ChartResult(
        chart_id="x",
        series_id="y",
        path="/tmp/x.svg",
        sha256=_GOOD_SHA256,
        title="t",
        period="p",
        unit="cases",
        source_ids=_SRC,
        watermark=_WATERMARK,
        alt_text="a",
    )
    with pytest.raises(ValidationError):
        c.title = "new"  # type: ignore[misc]
