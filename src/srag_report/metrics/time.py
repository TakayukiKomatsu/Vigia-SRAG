"""
Brazil epidemiological-week calendar helpers and SIVEP watermark contracts.

All functions operate on timezone-naive ``datetime.date`` values (calendar
dates, not instants).  Datetimes (``generated_at``) remain in UTC and are
handled by callers.

BR epi-week: Sunday (inclusive) through Saturday (inclusive).
  Reference week: last complete week whose Saturday ended >= 14 days before
                  ``as_of`` (stabilized window).
  Mature cohort: last complete week whose Saturday ended >= 28 days before
                 ``as_of`` (CFR cohort).

Spec anchor (AC-MT-1):
  as_of = 2026-07-28 → reference_week_end = 2026-07-11 (Saturday).
"""

from __future__ import annotations

import datetime
from typing import Final

# ---------------------------------------------------------------------------
# Weekday constants  (datetime.date.weekday(): 0=Mon … 5=Sat, 6=Sun)
# ---------------------------------------------------------------------------

_MON: Final[int] = 0
_SAT: Final[int] = 5
_SUN: Final[int] = 6

_STABILIZED_LAG_DAYS: Final[int] = 14  # reference-week cutoff
_MATURE_LAG_DAYS: Final[int] = 28  # CFR mature-cohort cutoff
_DAILY_SERIES_LENGTH: Final[int] = 30
_MONTHLY_SERIES_LENGTH: Final[int] = 12
_PROVISIONAL_DAYS: Final[int] = 14  # most-recent N daily points are provisional


# ---------------------------------------------------------------------------
# Error type
# ---------------------------------------------------------------------------


class WatermarkError(ValueError):
    """
    Raised when a requested ``as_of`` date is strictly after the SIVEP data
    watermark (maximum valid onset date in the current snapshot).

    Per spec: requests after the watermark are rejected before any metric
    calculation occurs; no silent date substitution.
    """


# ---------------------------------------------------------------------------
# Core epi-week helpers
# ---------------------------------------------------------------------------


def epi_week_start(d: datetime.date) -> datetime.date:
    """
    Return the Sunday that opens the BR epi-week containing *d*.

    >>> import datetime
    >>> epi_week_start(datetime.date(2026, 7, 28))  # Tuesday
    datetime.date(2026, 7, 26)
    >>> epi_week_start(datetime.date(2026, 7, 26))  # Sunday — returns itself
    datetime.date(2026, 7, 26)
    >>> epi_week_start(datetime.date(2026, 8, 1))   # Saturday
    datetime.date(2026, 7, 26)
    """
    # days_since_sunday: 0 for Sun, 1 for Mon, …, 6 for Sat
    days_since_sunday = (d.weekday() + 1) % 7
    return d - datetime.timedelta(days=days_since_sunday)


def epi_week_end(d: datetime.date) -> datetime.date:
    """
    Return the Saturday that closes the BR epi-week containing *d*.

    >>> import datetime
    >>> epi_week_end(datetime.date(2026, 7, 28))  # Tuesday → Sat 2026-08-01
    datetime.date(2026, 8, 1)
    """
    return epi_week_start(d) + datetime.timedelta(days=6)


# ---------------------------------------------------------------------------
# Internal: last Saturday at or before a date
# ---------------------------------------------------------------------------


def _last_saturday_on_or_before(d: datetime.date) -> datetime.date:
    """Return the Saturday (weekday 5) at or before *d*."""
    # (d.weekday() - 5) % 7 == days since last Saturday
    days_past = (d.weekday() - _SAT) % 7
    return d - datetime.timedelta(days=days_past)


# ---------------------------------------------------------------------------
# Stabilized reference week  (14-day lag)
# ---------------------------------------------------------------------------


def reference_week_end(as_of: datetime.date) -> datetime.date:
    """
    Last Saturday whose epi-week is fully stabilized relative to *as_of*.

    "Stabilized" means the Saturday fell at least ``_STABILIZED_LAG_DAYS``
    (14) days before *as_of*.

    Spec anchor (AC-MT-1):
      as_of = 2026-07-28 (Tuesday) → 2026-07-28 − 14 = 2026-07-14 (Tuesday)
      → last Saturday ≤ 2026-07-14 = **2026-07-11**
    """
    cutoff = as_of - datetime.timedelta(days=_STABILIZED_LAG_DAYS)
    return _last_saturday_on_or_before(cutoff)


def reference_week_start(as_of: datetime.date) -> datetime.date:
    """Sunday opening the stabilized reference epi-week for *as_of*."""
    return epi_week_start(reference_week_end(as_of))


# ---------------------------------------------------------------------------
# Mature 28-day cohort  (CFR)
# ---------------------------------------------------------------------------


def mature_cohort_end(as_of: datetime.date) -> datetime.date:
    """
    Last Saturday of the most recent mature epi-week for the CFR cohort.

    "Mature" means the Saturday fell at least ``_MATURE_LAG_DAYS`` (28) days
    before *as_of*; outcomes are considered stable at that age.
    """
    cutoff = as_of - datetime.timedelta(days=_MATURE_LAG_DAYS)
    return _last_saturday_on_or_before(cutoff)


def mature_cohort_start(as_of: datetime.date) -> datetime.date:
    """Sunday opening the 4-week mature cohort window for *as_of*."""
    return epi_week_start(mature_cohort_end(as_of)) - datetime.timedelta(weeks=3)


# ---------------------------------------------------------------------------
# Four-week windows
# ---------------------------------------------------------------------------


def last_four_stabilized_weeks(as_of: datetime.date) -> tuple[datetime.date, datetime.date]:
    """
    (start, end) of the four most recent complete stabilized epi-weeks.

    *end* is ``reference_week_end(as_of)`` (most recent stabilized Saturday).
    *start* is the Sunday three weeks earlier, giving a 28-day span.

    Used for: population mortality rate (FR-MT-3).
    """
    end = reference_week_end(as_of)
    start = epi_week_start(end) - datetime.timedelta(weeks=3)
    return (start, end)


# ---------------------------------------------------------------------------
# Prior complete calendar month  (ICU pressure)
# ---------------------------------------------------------------------------


def prior_complete_month(as_of: datetime.date) -> tuple[datetime.date, datetime.date]:
    """
    (first_day, last_day) of the calendar month immediately before *as_of*'s month.

    Used for: ICU pressure (FR-MT-5) — latest complete SIVEP/CNES overlap month.

    Example: as_of = 2026-07-28 → (2026-06-01, 2026-06-30).
    """
    first_of_this = as_of.replace(day=1)
    last_of_prior = first_of_this - datetime.timedelta(days=1)
    first_of_prior = last_of_prior.replace(day=1)
    return (first_of_prior, last_of_prior)


# ---------------------------------------------------------------------------
# Period builders for series
# ---------------------------------------------------------------------------


def daily_30_day_period(as_of: datetime.date) -> tuple[datetime.date, ...]:
    """
    30 consecutive dates ending at (and including) *as_of*, oldest first.

    The most recent ``_PROVISIONAL_DAYS`` (14) dates are marked provisional
    by callers; coverage-aware callers must zero-fill covered days with no
    cases and omit days outside snapshot coverage.

    Length guarantee: always exactly 30 elements.
    """
    return tuple(
        as_of - datetime.timedelta(days=i) for i in range(_DAILY_SERIES_LENGTH - 1, -1, -1)
    )


def monthly_12_month_period(as_of: datetime.date) -> tuple[datetime.date, ...]:
    """
    First days of the 12 complete calendar months preceding *as_of*'s month,
    returned in chronological order (oldest first).

    Example: as_of = 2026-07-28 →
      [date(2025,7,1), date(2025,8,1), …, date(2026,6,1)]  (12 elements)

    Length guarantee: always exactly 12 elements.
    """
    year, month = as_of.year, as_of.month
    months: list[datetime.date] = []
    for _ in range(_MONTHLY_SERIES_LENGTH):
        month -= 1
        if month == 0:
            month = 12
            year -= 1
        months.append(datetime.date(year, month, 1))
    months.reverse()  # oldest first
    return tuple(months)


# ---------------------------------------------------------------------------
# Watermark / as_of resolution
# ---------------------------------------------------------------------------


def resolve_as_of(
    watermark: datetime.date,
    requested: datetime.date | None = None,
) -> datetime.date:
    """
    Resolve the effective ``as_of`` date.

    - If *requested* is ``None``, return *watermark* (default: latest valid
      onset date in the SIVEP snapshot).
    - If *requested* <= *watermark*, return *requested*.
    - If *requested* > *watermark*, raise :exc:`WatermarkError`.

    No silent date substitution occurs (AC-MT-1).
    """
    if requested is None:
        return watermark
    if requested > watermark:
        raise WatermarkError(
            f"Requested as_of {requested.isoformat()} is after the SIVEP "
            f"watermark {watermark.isoformat()}; request rejected before any "
            f"metric calculation."
        )
    return requested
