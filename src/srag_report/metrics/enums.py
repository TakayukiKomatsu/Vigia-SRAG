"""
Versioned enumerations for the epidemiological metrics layer.

All enums are StrEnum so values serialize to/from plain strings in JSON.
Bump formula version suffixes (e.g. _V1 → _V2) on any calculation change.
"""

from __future__ import annotations

from enum import StrEnum

# ---------------------------------------------------------------------------
# Metric identity
# ---------------------------------------------------------------------------


class MetricId(StrEnum):
    """Stable identifiers for each metric/indicator produced by the pipeline."""

    CASE_GROWTH = "case_growth"
    MORTALITY_PER_100K = "mortality_per_100k"
    HOSPITAL_CFR = "hospital_cfr"  # supplementary — hospital case fatality rate
    ICU_PRESSURE = "icu_pressure"  # mandatory — estimated SRAG pressure on ICU capacity
    ICU_USE = "icu_use"  # supplementary — proportion with ICU use
    INFLUENZA_COVERAGE = "influenza_coverage"


class MetricFormula(StrEnum):
    """
    Versioned formula identifiers — every MetricResult carries one.

    Changing any formula constant in this module MUST bump the corresponding suffix.
    """

    CASE_GROWTH_V1 = "case_growth_v1"
    MORTALITY_PER_100K_V1 = "mortality_per_100k_v1"
    HOSPITAL_CFR_V1 = "hospital_cfr_v1"
    ICU_PRESSURE_V1 = "icu_pressure_v1"
    ICU_USE_V1 = "icu_use_v1"
    INFLUENZA_COVERAGE_V1 = "influenza_coverage_v1"


# ---------------------------------------------------------------------------
# Metric result state
# ---------------------------------------------------------------------------


class MetricState(StrEnum):
    """
    State of a computed metric value.

    - AVAILABLE: value computed normally, completeness >= 90 %.
    - WARNING: value computed with quality caveat, completeness in [70 %, 90 %).
    - UNAVAILABLE: value absent due to structural blocker or low completeness.
    - STABLE_ZERO: both reference and previous week are zero (case growth);
                   value is 0 — never omitted.
    - NEW_ACTIVITY: previous week zero, current week positive;
                   value is None — no infinite published.
    """

    AVAILABLE = "available"
    WARNING = "warning"
    UNAVAILABLE = "unavailable"
    STABLE_ZERO = "stable_zero"
    NEW_ACTIVITY = "new_activity"


# ---------------------------------------------------------------------------
# Series state
# ---------------------------------------------------------------------------


class SeriesGranularity(StrEnum):
    """Temporal resolution of a series."""

    DAILY = "daily"
    MONTHLY = "monthly"


class PointState(StrEnum):
    """
    Stability flag for a single series point.

    - STABLE: onset date >= 14 days before as_of; data presumed stable.
    - PROVISIONAL: onset date within 14 days of as_of; under-reported.
    """

    STABLE = "stable"
    PROVISIONAL = "provisional"


# ---------------------------------------------------------------------------
# Unavailability reasons
# ---------------------------------------------------------------------------


class UnavailableReason(StrEnum):
    """
    Structured reason why a numeric value is absent.

    Carried by MetricResult.reason when state is UNAVAILABLE.
    """

    COMPLETENESS_LOW = "completeness_low"  # < 70 % completeness
    STRUCTURAL_BLOCKER = "structural_blocker"  # critical-column / hash / source failure
    ZERO_DENOMINATOR = "zero_denominator"  # denominator is zero (non-growth metrics)
    RATIO_ABOVE_100_PCT = "ratio_above_100_pct"  # ICU pressure > 100 % — incompatible
    NOT_PUBLISHED_BY_CUTOFF = "not_published_by_cutoff"  # influenza obs not available by as_of
    PERIOD_NOT_COVERED = "period_not_covered"  # no source data for the required window
    INSUFFICIENT_SERIES = "insufficient_series"  # fewer points than required (30 or 12)
