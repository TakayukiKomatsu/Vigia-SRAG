"""
Strict frozen Pydantic models for metric results, series, and charts.

State/value consistency invariants (enforced by model_validator):
  AVAILABLE / WARNING  → value is not None
  STABLE_ZERO          → value == 0.0 exactly
  UNAVAILABLE          → value is None AND reason is not None
  NEW_ACTIVITY         → value is None (state is self-explanatory; no infinity)

``geography`` is always "BR" — the entire package is Brazil-only.
``source_ids`` must be non-empty on every result.

population_scope rules:
  Non-INFLUENZA_COVERAGE metrics: population_scope must be None.
  INFLUENZA_COVERAGE: None means nationally eligible; a non-empty set means scoped.

QualityResult blocker rules:
  BLOCKED state: blocker must be a non-empty string.
  Non-BLOCKED states: blocker must be None.

SeriesResult invariants:
  DAILY:   exactly 30 strictly contiguous daily points; points[0].period == period_start,
           points[-1].period == period_end; first 16 STABLE, last 14 PROVISIONAL.
  MONTHLY: exactly 12 strictly contiguous first-of-month points, all STABLE;
           points[0].period == period_start,
           period_end == last calendar day of points[-1].period's month.
"""

from __future__ import annotations

import calendar
import datetime
import re
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from ..domain.source import QualityState
from .enums import (
    MetricFormula,
    MetricId,
    MetricState,
    PointState,
    SeriesGranularity,
    UnavailableReason,
)

# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

_SHA256_RE: re.Pattern[str] = re.compile(r"[0-9a-f]{64}")

_DAILY_POINT_COUNT = 30
_MONTHLY_POINT_COUNT = 12
_DAILY_STABLE_COUNT = 16  # first N points stable
_DAILY_PROVISIONAL_COUNT = 14  # last N points provisional


def _require_nonempty_source_ids(v: tuple[str, ...]) -> tuple[str, ...]:
    if not v:
        raise ValueError("source_ids must contain at least one entry")
    return v


def _last_day_of_month(d: datetime.date) -> datetime.date:
    _, last = calendar.monthrange(d.year, d.month)
    return d.replace(day=last)


# ---------------------------------------------------------------------------
# Quality result
# ---------------------------------------------------------------------------


class QualityResult(BaseModel):
    """
    Quality assessment attached to every metric, series, and chart result.

    ``completeness`` is a ratio in [0.0, 1.0].
    ``state`` follows the same thresholds as the data-foundation layer:
      >= 0.90 -> AVAILABLE, >= 0.70 -> WARNING, < 0.70 -> UNAVAILABLE.
      BLOCKED overrides the percentage for structural failures.
    ``blocker`` carries a non-empty human-readable description when state is BLOCKED,
    and must be None for all other states.
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    completeness: float = Field(ge=0.0, le=1.0)
    state: QualityState
    blocker: str | None = None

    @model_validator(mode="after")
    def _check_blocker_consistency(self) -> QualityResult:
        if self.state == QualityState.BLOCKED:
            if not self.blocker:
                raise ValueError("state='blocked' requires a non-empty blocker description")
        else:
            if self.blocker is not None:
                raise ValueError(
                    f"state={self.state!r} must not carry a blocker; "
                    "blocker is reserved for state='blocked'"
                )
        return self


# ---------------------------------------------------------------------------
# Metric result
# ---------------------------------------------------------------------------


class MetricResult(BaseModel):
    """
    Single computed metric or indicator.

    State/value consistency is enforced by ``_check_state_value_consistency``.
    population_scope rules are enforced by ``_check_population_scope``.
    See module docstring for the full invariant tables.

    ``limitations`` is an ordered tuple of human-readable caveats (e.g.
    unknown-outcome count for CFR, ICU-pressure not-all-causes disclaimer).

    ``population_scope`` carries an explicit limited PNI coverage scope (for
    example, frozenset({"NE","CO","S","SE"})) for INFLUENZA_COVERAGE. It is
    None for national coverage and every other metric.
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    metric_id: MetricId
    label: str
    value: float | None
    state: MetricState
    reason: UnavailableReason | None = None
    unit: str
    numerator: float | None = None
    denominator: float | None = None
    period_start: datetime.date
    period_end: datetime.date
    geography: Literal["BR"] = "BR"
    snapshot_id: str
    formula_version: MetricFormula
    quality: QualityResult
    source_ids: tuple[str, ...]
    limitations: tuple[str, ...] = ()
    population_scope: frozenset[str] | None = None

    @field_validator("source_ids")
    @classmethod
    def _source_ids_nonempty(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        return _require_nonempty_source_ids(v)

    @field_serializer("population_scope")
    def _serialize_population_scope(self, value: frozenset[str] | None) -> list[str] | None:
        return sorted(value) if value is not None else None

    @field_validator("period_end")
    @classmethod
    def _period_order(cls, v: datetime.date, info: object) -> datetime.date:
        data = getattr(info, "data", {})
        period_start = data.get("period_start")
        if period_start is not None and v < period_start:
            raise ValueError(f"period_end {v} must be >= period_start {period_start}")
        return v

    @model_validator(mode="after")
    def _check_state_value_consistency(self) -> MetricResult:
        """Enforce the state/value invariants described in the module docstring."""
        state = self.state
        value = self.value
        reason = self.reason

        if state in (MetricState.AVAILABLE, MetricState.WARNING):
            if value is None:
                raise ValueError(
                    f"state={state!r} requires a non-None value; "
                    "use state='unavailable' when the metric cannot be computed"
                )

        elif state == MetricState.STABLE_ZERO:
            if value != 0.0:
                raise ValueError(
                    f"state='stable_zero' requires value=0.0, got {value!r}; "
                    "both current and previous are zero"
                )

        elif state == MetricState.UNAVAILABLE:
            if value is not None:
                raise ValueError(
                    f"state='unavailable' requires value=None, got {value!r}; "
                    "do not publish incompatible or uncalculable values"
                )
            if reason is None:
                raise ValueError(
                    "state='unavailable' requires reason to be set; "
                    "use UnavailableReason to describe why"
                )

        elif state == MetricState.NEW_ACTIVITY:
            if value is not None:
                raise ValueError(
                    f"state='new_activity' requires value=None, got {value!r}; "
                    "no infinite percentage is published when previous_cases=0"
                )

        return self

    @model_validator(mode="after")
    def _check_population_scope(self) -> MetricResult:
        """
        Enforce population_scope rules.

        Non-INFLUENZA_COVERAGE: must be None.
        INFLUENZA_COVERAGE: None means national; a non-empty set means scoped.
        """
        if self.metric_id != MetricId.INFLUENZA_COVERAGE:
            if self.population_scope is not None:
                raise ValueError(
                    f"population_scope is only allowed for metric_id='influenza_coverage', "
                    f"not {self.metric_id!r}"
                )
        elif self.population_scope is not None and not self.population_scope:
            raise ValueError("population_scope must be non-empty when provided")
        return self


# ---------------------------------------------------------------------------
# Series contracts
# ---------------------------------------------------------------------------


class SeriesPoint(BaseModel):
    """
    Single data point in a time series.

    ``period`` is the onset-date bucket (daily: a calendar date;
    monthly: the first day of the month).
    ``value`` is the non-negative integer case count.  Zero is valid for
    covered dates/months with no reported cases.
    ``state`` marks the most-recent 14 daily points as PROVISIONAL.
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    period: datetime.date
    value: int = Field(ge=0)
    state: PointState


class SeriesResult(BaseModel):
    """
    Time series of case counts (daily 30-point or monthly 12-point).

    ``points`` is ordered chronologically, oldest first.

    DAILY invariants (enforced):
    - Exactly 30 strictly contiguous daily points.
    - points[0].period == period_start; points[-1].period == period_end.
    - First 16 points STABLE; last 14 PROVISIONAL.

    MONTHLY invariants (enforced):
    - Exactly 12 strictly contiguous first-of-month points, all STABLE.
    - points[0].period == period_start.
    - period_end == last calendar day of points[-1].period's month.

    Series completeness and availability are reflected in ``quality``;
    an insufficient series has quality.state=UNAVAILABLE and its chart is
    not rendered.
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    series_id: str
    granularity: SeriesGranularity
    points: tuple[SeriesPoint, ...]
    period_start: datetime.date
    period_end: datetime.date
    geography: Literal["BR"] = "BR"
    snapshot_id: str
    quality: QualityResult
    source_ids: tuple[str, ...]

    @field_validator("source_ids")
    @classmethod
    def _source_ids_nonempty(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        return _require_nonempty_source_ids(v)

    @model_validator(mode="after")
    def _check_series_invariants(self) -> SeriesResult:
        """Enforce granularity-specific structural invariants on ``points``."""
        points = self.points
        granularity = self.granularity

        if granularity == SeriesGranularity.DAILY:
            # 1. Exactly 30 points
            if len(points) != _DAILY_POINT_COUNT:
                raise ValueError(
                    f"daily series requires exactly {_DAILY_POINT_COUNT} points, "
                    f"got {len(points)}"
                )
            # 2. Strictly contiguous daily dates
            for i in range(1, len(points)):
                expected = points[i - 1].period + datetime.timedelta(days=1)
                if points[i].period != expected:
                    raise ValueError(
                        f"daily points must be strictly contiguous; "
                        f"expected {expected} at index {i}, got {points[i].period}"
                    )
            # 3. Period bounds match
            if points[0].period != self.period_start:
                raise ValueError(
                    f"points[0].period {points[0].period} != period_start {self.period_start}"
                )
            if points[-1].period != self.period_end:
                raise ValueError(
                    f"points[-1].period {points[-1].period} != period_end {self.period_end}"
                )
            # 4. First 16 stable, last 14 provisional
            for i, p in enumerate(points):
                expected_state = (
                    PointState.STABLE if i < _DAILY_STABLE_COUNT else PointState.PROVISIONAL
                )
                if p.state != expected_state:
                    raise ValueError(
                        f"daily points[{i}].state must be {expected_state!r}, got {p.state!r}; "
                        f"first {_DAILY_STABLE_COUNT} must be STABLE, "
                        f"last {_DAILY_PROVISIONAL_COUNT} must be PROVISIONAL"
                    )

        elif granularity == SeriesGranularity.MONTHLY:
            # 1. Exactly 12 points
            if len(points) != _MONTHLY_POINT_COUNT:
                raise ValueError(
                    f"monthly series requires exactly {_MONTHLY_POINT_COUNT} points, "
                    f"got {len(points)}"
                )
            for i, p in enumerate(points):
                # 2. All first-of-month
                if p.period.day != 1:
                    raise ValueError(
                        f"monthly points[{i}].period {p.period} is not the first day of a month"
                    )
                # 3. All STABLE
                if p.state != PointState.STABLE:
                    raise ValueError(f"monthly points[{i}].state must be STABLE, got {p.state!r}")
            # 4. Strictly contiguous months
            for i in range(1, len(points)):
                prev = points[i - 1].period
                if prev.month == 12:
                    expected = prev.replace(year=prev.year + 1, month=1)
                else:
                    expected = prev.replace(month=prev.month + 1)
                if points[i].period != expected:
                    raise ValueError(
                        f"monthly points must be strictly contiguous; "
                        f"expected {expected} at index {i}, got {points[i].period}"
                    )
            # 5. Period bounds
            if points[0].period != self.period_start:
                raise ValueError(
                    f"points[0].period {points[0].period} != period_start {self.period_start}"
                )
            expected_end = _last_day_of_month(points[-1].period)
            if self.period_end != expected_end:
                raise ValueError(
                    f"period_end {self.period_end} != last day of last month {expected_end}"
                )

        return self


# ---------------------------------------------------------------------------
# Chart result
# ---------------------------------------------------------------------------


class ChartResult(BaseModel):
    """
    Rendered chart artifact.

    ``path`` is an absolute or relative filesystem path to the SVG/PNG.
    ``sha256`` is the 64-character lowercase hex digest of the rendered file.
    ``watermark`` is the SIVEP data watermark date used during rendering.
    ``alt_text`` is the mandatory accessible description (NFR-MT-5).
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    chart_id: str
    series_id: str
    path: str
    sha256: str
    title: str
    period: str
    unit: str
    source_ids: tuple[str, ...]
    watermark: datetime.date
    alt_text: str

    @field_validator("sha256")
    @classmethod
    def _validate_sha256(cls, v: str) -> str:
        if _SHA256_RE.fullmatch(v) is None:
            raise ValueError(f"sha256 must be 64 lowercase hexadecimal characters, got {v!r}")
        return v

    @field_validator("source_ids")
    @classmethod
    def _source_ids_nonempty(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        return _require_nonempty_source_ids(v)
