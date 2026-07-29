"""Metrics layer: typed contracts, epi-week time helpers, and quality models."""

from .calculations import (
    case_growth,
    daily_case_series,
    hospital_case_fatality,
    icu_pressure,
    icu_use,
    influenza_coverage,
    monthly_case_series,
    population_mortality,
    quality_result,
)
from .charts import render_series_svg
from .enums import (
    MetricFormula,
    MetricId,
    MetricState,
    PointState,
    SeriesGranularity,
    UnavailableReason,
)
from .models import (
    ChartResult,
    MetricResult,
    QualityResult,
    SeriesPoint,
    SeriesResult,
)
from .query import MetricPackage, compute_metric_package
from .time import (
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

__all__ = [
    "case_growth",
    "daily_case_series",
    "hospital_case_fatality",
    "icu_pressure",
    "icu_use",
    "influenza_coverage",
    "monthly_case_series",
    "population_mortality",
    "quality_result",
    "render_series_svg",
    "MetricPackage",
    "compute_metric_package",
    # Enums
    "MetricFormula",
    "MetricId",
    "MetricState",
    "PointState",
    "SeriesGranularity",
    "UnavailableReason",
    # Models
    "ChartResult",
    "MetricResult",
    "QualityResult",
    "SeriesPoint",
    "SeriesResult",
    # Time helpers
    "WatermarkError",
    "daily_30_day_period",
    "epi_week_end",
    "epi_week_start",
    "last_four_stabilized_weeks",
    "mature_cohort_end",
    "mature_cohort_start",
    "monthly_12_month_period",
    "prior_complete_month",
    "reference_week_end",
    "reference_week_start",
    "resolve_as_of",
]
