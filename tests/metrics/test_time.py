"""
T-MT-1 time helper tests.

All boundary dates are pinned to values from the spec (AC-MT-1):
  as_of = 2026-07-28 (Tuesday) -> reference_week_end = 2026-07-11 (Saturday)

Watermark rejection (AC-MT-1): requesting as_of > watermark raises WatermarkError
before any metric calculation; no silent substitution.
"""

from __future__ import annotations

import datetime

import pytest

from srag_report.metrics.time import (
    WatermarkError,
    daily_30_day_period,
    epi_week_end,
    epi_week_start,
    last_four_stabilized_weeks,
    mature_cohort_end,
    mature_cohort_start,
    monthly_12_month_period,
    prior_complete_month,
    reference_week_end,
    reference_week_start,
    resolve_as_of,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

AS_OF = datetime.date(2026, 7, 28)  # Tuesday — spec anchor date
WATERMARK = datetime.date(2026, 7, 28)


# ---------------------------------------------------------------------------
# epi_week_start
# ---------------------------------------------------------------------------


def test_epi_week_start_on_sunday_returns_itself() -> None:
    sunday = datetime.date(2026, 7, 26)
    assert epi_week_start(sunday) == sunday


def test_epi_week_start_on_monday() -> None:
    # Monday 2026-07-27 -> Sunday 2026-07-26
    assert epi_week_start(datetime.date(2026, 7, 27)) == datetime.date(2026, 7, 26)


def test_epi_week_start_on_saturday() -> None:
    # Saturday 2026-08-01 -> Sunday 2026-07-26
    assert epi_week_start(datetime.date(2026, 8, 1)) == datetime.date(2026, 7, 26)


def test_epi_week_start_on_tuesday_spec_anchor() -> None:
    # Tuesday 2026-07-28 -> Sunday 2026-07-26
    assert epi_week_start(AS_OF) == datetime.date(2026, 7, 26)


# ---------------------------------------------------------------------------
# epi_week_end
# ---------------------------------------------------------------------------


def test_epi_week_end_is_saturday() -> None:
    # Any date in week 2026-07-26..2026-08-01 ends on Saturday 2026-08-01
    for day in range(26, 32):
        d = datetime.date(2026, 7, day) if day <= 31 else datetime.date(2026, 8, day - 31)
        end = epi_week_end(d)
        assert end.weekday() == 5, f"{d} -> {end} is not Saturday"


def test_epi_week_end_on_tuesday_spec_anchor() -> None:
    assert epi_week_end(AS_OF) == datetime.date(2026, 8, 1)


def test_epi_week_end_on_sunday() -> None:
    # Sunday is the first day of its week; end = +6 days = Saturday
    sunday = datetime.date(2026, 7, 26)
    assert epi_week_end(sunday) == datetime.date(2026, 8, 1)


def test_epi_week_start_end_span_7_days() -> None:
    start = epi_week_start(AS_OF)
    end = epi_week_end(AS_OF)
    assert (end - start).days == 6


# ---------------------------------------------------------------------------
# reference_week_end  — SPEC BOUNDARY TEST (AC-MT-1)
# ---------------------------------------------------------------------------


def test_reference_week_end_spec_anchor() -> None:
    """AC-MT-1: as_of=2026-07-28 -> reference_week_end=2026-07-11."""
    assert reference_week_end(AS_OF) == datetime.date(2026, 7, 11)


def test_reference_week_end_is_saturday() -> None:
    result = reference_week_end(AS_OF)
    assert result.weekday() == 5  # Saturday


def test_reference_week_end_at_least_14_days_before_as_of() -> None:
    end = reference_week_end(AS_OF)
    assert (AS_OF - end).days >= 14


def test_reference_week_end_is_latest_possible() -> None:
    """No Saturday between reference_week_end+1 and as_of-14 exists."""
    end = reference_week_end(AS_OF)
    next_sat = end + datetime.timedelta(days=7)
    # next Saturday must be within the 14-day restricted zone
    assert (AS_OF - next_sat).days < 14


def test_reference_week_start_is_sunday() -> None:
    start = reference_week_start(AS_OF)
    assert start.weekday() == 6  # Sunday


def test_reference_week_start_to_end_is_7_days() -> None:
    start = reference_week_start(AS_OF)
    end = reference_week_end(AS_OF)
    assert (end - start).days == 6


# ---------------------------------------------------------------------------
# mature_cohort_end  (28-day lag)
# ---------------------------------------------------------------------------


def test_mature_cohort_end_is_saturday() -> None:
    result = mature_cohort_end(AS_OF)
    assert result.weekday() == 5


def test_mature_cohort_end_at_least_28_days_before_as_of() -> None:
    end = mature_cohort_end(AS_OF)
    assert (AS_OF - end).days >= 28


def test_mature_cohort_end_is_latest_possible() -> None:
    end = mature_cohort_end(AS_OF)
    next_sat = end + datetime.timedelta(days=7)
    assert (AS_OF - next_sat).days < 28


def test_mature_cohort_start_is_sunday() -> None:
    start = mature_cohort_start(AS_OF)
    assert start.weekday() == 6


def test_mature_cohort_start_before_end() -> None:
    start = mature_cohort_start(AS_OF)
    end = mature_cohort_end(AS_OF)
    assert start < end
    assert (end - start).days == 27


# ---------------------------------------------------------------------------
# last_four_stabilized_weeks
# ---------------------------------------------------------------------------


def test_last_four_stabilized_weeks_end_matches_reference() -> None:
    start, end = last_four_stabilized_weeks(AS_OF)
    assert end == reference_week_end(AS_OF)


def test_last_four_stabilized_weeks_span_28_days() -> None:
    start, end = last_four_stabilized_weeks(AS_OF)
    assert (end - start).days == 27  # 4 complete epi-weeks = 28 days, end-start = 27


def test_last_four_stabilized_weeks_start_is_sunday() -> None:
    start, _ = last_four_stabilized_weeks(AS_OF)
    assert start.weekday() == 6


# ---------------------------------------------------------------------------
# prior_complete_month
# ---------------------------------------------------------------------------


def test_prior_complete_month_from_july() -> None:
    start, end = prior_complete_month(AS_OF)
    assert start == datetime.date(2026, 6, 1)
    assert end == datetime.date(2026, 6, 30)


def test_prior_complete_month_from_january_crosses_year() -> None:
    as_of_jan = datetime.date(2026, 1, 15)
    start, end = prior_complete_month(as_of_jan)
    assert start == datetime.date(2025, 12, 1)
    assert end == datetime.date(2025, 12, 31)


def test_prior_complete_month_end_is_last_day_of_month() -> None:
    # March 2026 has 31 days
    start, end = prior_complete_month(datetime.date(2026, 4, 1))
    assert start == datetime.date(2026, 3, 1)
    assert end == datetime.date(2026, 3, 31)


def test_prior_complete_month_february() -> None:
    # Feb 2026 has 28 days (not a leap year)
    start, end = prior_complete_month(datetime.date(2026, 3, 10))
    assert start == datetime.date(2026, 2, 1)
    assert end == datetime.date(2026, 2, 28)


# ---------------------------------------------------------------------------
# daily_30_day_period
# ---------------------------------------------------------------------------


def test_daily_30_day_period_length() -> None:
    dates = daily_30_day_period(AS_OF)
    assert len(dates) == 30


def test_daily_30_day_period_ends_at_as_of() -> None:
    dates = daily_30_day_period(AS_OF)
    assert dates[-1] == AS_OF


def test_daily_30_day_period_starts_29_days_before() -> None:
    dates = daily_30_day_period(AS_OF)
    assert dates[0] == AS_OF - datetime.timedelta(days=29)


def test_daily_30_day_period_consecutive() -> None:
    dates = daily_30_day_period(AS_OF)
    for i in range(1, len(dates)):
        assert (dates[i] - dates[i - 1]).days == 1


def test_daily_30_day_period_oldest_first() -> None:
    dates = daily_30_day_period(AS_OF)
    assert dates[0] < dates[-1]


# ---------------------------------------------------------------------------
# monthly_12_month_period
# ---------------------------------------------------------------------------


def test_monthly_12_month_period_length() -> None:
    months = monthly_12_month_period(AS_OF)
    assert len(months) == 12


def test_monthly_12_month_period_all_before_as_of_month() -> None:
    months = monthly_12_month_period(AS_OF)
    as_of_month_start = AS_OF.replace(day=1)
    for m in months:
        assert m < as_of_month_start


def test_monthly_12_month_period_oldest_first() -> None:
    months = monthly_12_month_period(AS_OF)
    assert months[0] < months[-1]


def test_monthly_12_month_period_all_first_of_month() -> None:
    months = monthly_12_month_period(AS_OF)
    for m in months:
        assert m.day == 1


def test_monthly_12_month_period_spec_anchor_bounds() -> None:
    """as_of=2026-07-28 -> months Jul 2025 through Jun 2026."""
    months = monthly_12_month_period(AS_OF)
    assert months[0] == datetime.date(2025, 7, 1)
    assert months[-1] == datetime.date(2026, 6, 1)


def test_monthly_12_month_period_consecutive_months() -> None:
    months = monthly_12_month_period(AS_OF)
    for i in range(1, len(months)):
        prev, curr = months[i - 1], months[i]
        # curr is exactly one month after prev
        expected = (prev.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
        assert curr == expected


def test_monthly_12_month_period_january_as_of() -> None:
    """as_of=2026-01-15 -> 12 months entirely in 2025 (Jan–Dec)."""
    months = monthly_12_month_period(datetime.date(2026, 1, 15))
    assert months[0] == datetime.date(2025, 1, 1)
    assert months[-1] == datetime.date(2025, 12, 1)
    assert len(months) == 12


# ---------------------------------------------------------------------------
# resolve_as_of / WatermarkError  — SPEC BOUNDARY TEST (AC-MT-1)
# ---------------------------------------------------------------------------


def test_resolve_as_of_no_request_returns_watermark() -> None:
    result = resolve_as_of(WATERMARK)
    assert result == WATERMARK


def test_resolve_as_of_at_watermark_accepted() -> None:
    result = resolve_as_of(WATERMARK, requested=WATERMARK)
    assert result == WATERMARK


def test_resolve_as_of_before_watermark_accepted() -> None:
    earlier = WATERMARK - datetime.timedelta(days=1)
    result = resolve_as_of(WATERMARK, requested=earlier)
    assert result == earlier


def test_resolve_as_of_after_watermark_raises() -> None:
    """AC-MT-1: request after watermark is rejected; no silent substitution."""
    after = WATERMARK + datetime.timedelta(days=1)  # 2026-07-29
    with pytest.raises(WatermarkError):
        resolve_as_of(WATERMARK, requested=after)


def test_resolve_as_of_watermark_error_message_contains_dates() -> None:
    after = datetime.date(2026, 7, 29)
    with pytest.raises(WatermarkError, match="2026-07-29"):
        resolve_as_of(WATERMARK, requested=after)


def test_watermark_error_is_value_error_subclass() -> None:
    """WatermarkError must be catchable as ValueError."""
    after = WATERMARK + datetime.timedelta(days=1)
    with pytest.raises(ValueError):
        resolve_as_of(WATERMARK, requested=after)
