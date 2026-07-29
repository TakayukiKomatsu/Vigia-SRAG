from __future__ import annotations

import datetime as dt
import json
from collections.abc import Mapping
from decimal import Decimal
from pathlib import Path

from duckdb import DuckDBPyConnection
from pydantic import BaseModel, ConfigDict, model_validator

from ..data.store import open_snapshot
from ..domain.models import PniObservation
from .calculations import (
    case_growth,
    daily_case_series,
    hospital_case_fatality,
    icu_pressure,
    icu_use,
    influenza_coverage,
    monthly_case_series,
    population_mortality,
)
from .enums import MetricId
from .models import MetricResult, SeriesResult
from .time import (
    last_four_stabilized_weeks,
    mature_cohort_end,
    mature_cohort_start,
    monthly_12_month_period,
    prior_complete_month,
    reference_week_end,
    resolve_as_of,
)


class MetricPackage(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    snapshot_id: str
    as_of: dt.date
    watermark: dt.date
    metrics: tuple[MetricResult, ...]
    series: tuple[SeriesResult, ...]

    @model_validator(mode="after")
    def _required_metrics_present(self) -> MetricPackage:
        actual = {metric.metric_id for metric in self.metrics}
        expected = set(MetricId)
        if actual != expected or len(self.metrics) != len(expected):
            raise ValueError("metric package must contain each metric exactly once")
        return self


def _scalar_int(connection: DuckDBPyConnection, query: str, parameters: list[object]) -> int:
    row = connection.execute(query, parameters).fetchone()
    if row is None:
        raise RuntimeError("aggregate query returned no row")
    return int(row[0] or 0)


def _completeness(values: Mapping[MetricId | str, float], metric_id: MetricId) -> float:
    return float(values.get(metric_id, values.get(metric_id.value, 1.0)))


def _blocker(values: Mapping[MetricId | str, str], metric_id: MetricId) -> str | None:
    value = values.get(metric_id, values.get(metric_id.value))
    return str(value) if value is not None else None


def _load_pni(connection: DuckDBPyConnection, as_of: dt.date) -> PniObservation | None:
    row = connection.execute(
        """
        SELECT campaign_year, immunobiological, population_scope_json,
               period_start, period_end, numerator, denominator, coverage_pct,
               published_at, source_label, is_nationwide, is_golden
        FROM pni_observations
        WHERE CAST(published_at AS TIMESTAMPTZ) <= ?
        ORDER BY CAST(published_at AS TIMESTAMPTZ) DESC, source_label
        LIMIT 1
        """,
        [dt.datetime.combine(as_of, dt.time.max, tzinfo=dt.UTC)],
    ).fetchone()
    if row is None:
        return None
    if int(row[0]) != 2026 or str(row[1]) != "INF3" or bool(row[10]) or bool(row[11]):
        raise ValueError("stored PNI observation violates the fixed 2026 INF3 scoped contract")
    return PniObservation(
        campaign_year=2026,
        immunobiological="INF3",
        population_scope=frozenset(json.loads(str(row[2]))),
        period_start=row[3],
        period_end=row[4],
        numerator=int(row[5]),
        denominator=int(row[6]),
        coverage_pct=Decimal(str(row[7])),
        published_at=dt.datetime.fromisoformat(str(row[8])),
        source_label=str(row[9]),
        is_nationwide=False,
        is_golden=False,
    )


def compute_metric_package(
    path: Path,
    *,
    snapshot_id: str,
    watermark: dt.date,
    requested_as_of: dt.date | None = None,
    completeness: Mapping[MetricId | str, float] | None = None,
    blockers: Mapping[MetricId | str, str] | None = None,
) -> MetricPackage:
    """Compute every metric through fixed, parameterized SQL on a read-only snapshot."""
    as_of = resolve_as_of(watermark, requested_as_of)
    completeness = completeness or {}
    blockers = blockers or {}
    reference_end = reference_week_end(as_of)
    reference_start = reference_end - dt.timedelta(days=6)
    previous_start = reference_start - dt.timedelta(days=7)
    previous_end = reference_start - dt.timedelta(days=1)
    mortality_start, mortality_end = last_four_stabilized_weeks(as_of)
    mature_start, mature_end = mature_cohort_start(as_of), mature_cohort_end(as_of)
    month_start, month_end = prior_complete_month(as_of)

    with open_snapshot(path) as connection:
        growth_row = connection.execute(
            """
            SELECT
              count(*) FILTER (WHERE symptom_onset BETWEEN ? AND ?),
              count(*) FILTER (WHERE symptom_onset BETWEEN ? AND ?)
            FROM sivep_cases
            """,
            [previous_start, previous_end, reference_start, reference_end],
        ).fetchone()
        if growth_row is None:
            raise RuntimeError("case growth aggregate returned no row")
        previous_cases, current_cases = int(growth_row[0]), int(growth_row[1])

        deaths = _scalar_int(
            connection,
            "SELECT count(*) FROM sivep_cases "
            "WHERE evolution = 2 AND evolution_date BETWEEN ? AND ?",
            [mortality_start, mortality_end],
        )
        population = _scalar_int(
            connection,
            "SELECT coalesce(max(population_official), 0) FROM ibge_population WHERE geography = ?",
            ["BR"],
        )
        outcome_row = connection.execute(
            """
            SELECT
              count(*) FILTER (WHERE evolution = 2),
              count(*) FILTER (WHERE evolution IN (1, 2, 3)),
              count(*) FILTER (WHERE evolution IS NULL OR evolution = 9)
            FROM sivep_cases
            WHERE hospitalization_flag = 1 AND symptom_onset BETWEEN ? AND ?
            """,
            [mature_start, mature_end],
        ).fetchone()
        if outcome_row is None:
            raise RuntimeError("fatality aggregate returned no row")
        fatal_deaths, known_outcomes, unknown_outcomes = map(int, outcome_row)

        icu_use_row = connection.execute(
            """
            SELECT
              count(*) FILTER (WHERE icu_flag = 1),
              count(*) FILTER (WHERE icu_flag IN (1, 2))
            FROM sivep_cases
            WHERE hospitalization_flag = 1 AND symptom_onset BETWEEN ? AND ?
            """,
            [mortality_start, mortality_end],
        ).fetchone()
        if icu_use_row is None:
            raise RuntimeError("ICU-use aggregate returned no row")
        icu_admissions, known_icu_status = map(int, icu_use_row)

        patient_days = _scalar_int(
            connection,
            """
            SELECT coalesce(
              sum(date_diff('day', greatest(icu_entry_date, ?), least(icu_exit_date, ?)) + 1),
              0
            )
            FROM sivep_cases
            WHERE icu_flag = 1
              AND icu_entry_date IS NOT NULL
              AND icu_exit_date IS NOT NULL
              AND icu_exit_date >= ?
              AND icu_entry_date <= ?
            """,
            [month_start, month_end, month_start, month_end],
        )
        excluded_open_stays = _scalar_int(
            connection,
            """
            SELECT count(*)
            FROM sivep_cases
            WHERE icu_flag = 1
              AND icu_entry_date IS NOT NULL
              AND icu_entry_date <= ?
              AND icu_exit_date IS NULL
            """,
            [month_end],
        )
        days_in_month = (month_end - month_start).days + 1
        beds = _scalar_int(
            connection,
            "SELECT coalesce(sum(qt_exist), 0) FROM cnes_icu_beds WHERE competencia = ?",
            [month_start.year * 100 + month_start.month],
        )
        bed_days = beds * days_in_month
        pni_observation = _load_pni(connection, as_of)

        coverage_row = connection.execute(
            "SELECT min(symptom_onset), max(symptom_onset) FROM sivep_cases"
        ).fetchone()
        coverage_start = coverage_row[0] if coverage_row and coverage_row[0] is not None else None
        coverage_end = coverage_row[1] if coverage_row and coverage_row[1] is not None else None

        daily_counts: dict[dt.date, int] = {}
        monthly_counts: dict[dt.date, int] = {}
        if coverage_start is not None and coverage_end is not None:
            daily_start = as_of - dt.timedelta(days=29)
            daily_counts = {
                row[0]: int(row[1])
                for row in connection.execute(
                    """
                    SELECT symptom_onset, count(*)
                    FROM sivep_cases
                    WHERE symptom_onset BETWEEN ? AND ?
                    GROUP BY symptom_onset
                    ORDER BY symptom_onset
                    """,
                    [daily_start, as_of],
                ).fetchall()
            }
            monthly_start = monthly_12_month_period(as_of)[0]
            monthly_counts = {
                row[0]: int(row[1])
                for row in connection.execute(
                    """
                    SELECT CAST(date_trunc('month', symptom_onset) AS DATE), count(*)
                    FROM sivep_cases
                    WHERE symptom_onset >= ? AND symptom_onset < ?
                    GROUP BY 1
                    ORDER BY 1
                    """,
                    [monthly_start, as_of.replace(day=1)],
                ).fetchall()
            }

    metrics = (
        case_growth(
            previous_cases=previous_cases,
            current_cases=current_cases,
            as_of=as_of,
            snapshot_id=snapshot_id,
            completeness=_completeness(completeness, MetricId.CASE_GROWTH),
            blocker=_blocker(blockers, MetricId.CASE_GROWTH),
        ),
        population_mortality(
            deaths=deaths,
            population=population,
            as_of=as_of,
            snapshot_id=snapshot_id,
            completeness=_completeness(completeness, MetricId.MORTALITY_PER_100K),
            blocker=_blocker(blockers, MetricId.MORTALITY_PER_100K),
        ),
        hospital_case_fatality(
            deaths=fatal_deaths,
            known_outcomes=known_outcomes,
            unknown_outcomes=unknown_outcomes,
            as_of=as_of,
            snapshot_id=snapshot_id,
            completeness=_completeness(completeness, MetricId.HOSPITAL_CFR),
            blocker=_blocker(blockers, MetricId.HOSPITAL_CFR),
        ),
        icu_pressure(
            patient_days=patient_days,
            bed_days=bed_days,
            period_start=month_start,
            period_end=month_end,
            excluded_open_stays=excluded_open_stays,
            snapshot_id=snapshot_id,
            completeness=_completeness(completeness, MetricId.ICU_PRESSURE),
            blocker=_blocker(blockers, MetricId.ICU_PRESSURE),
        ),
        icu_use(
            icu_admissions=icu_admissions,
            known_icu_status=known_icu_status,
            period_start=mortality_start,
            period_end=mortality_end,
            snapshot_id=snapshot_id,
            completeness=_completeness(completeness, MetricId.ICU_USE),
            blocker=_blocker(blockers, MetricId.ICU_USE),
        ),
        influenza_coverage(
            observation=pni_observation,
            as_of=as_of,
            snapshot_id=snapshot_id,
            completeness=_completeness(completeness, MetricId.INFLUENZA_COVERAGE),
            blocker=_blocker(blockers, MetricId.INFLUENZA_COVERAGE),
        ),
    )
    series: list[SeriesResult] = []
    if coverage_start is not None and coverage_end is not None:
        daily = daily_case_series(
            daily_counts,
            coverage_start=coverage_start,
            coverage_end=coverage_end,
            as_of=as_of,
            snapshot_id=snapshot_id,
            completeness=_completeness(completeness, MetricId.CASE_GROWTH),
        )
        monthly = monthly_case_series(
            monthly_counts,
            coverage_start=coverage_start,
            coverage_end=coverage_end,
            as_of=as_of,
            snapshot_id=snapshot_id,
            completeness=_completeness(completeness, MetricId.CASE_GROWTH),
        )
        if daily is not None:
            series.append(daily)
        if monthly is not None:
            series.append(monthly)
    return MetricPackage(
        snapshot_id=snapshot_id,
        as_of=as_of,
        watermark=watermark,
        metrics=metrics,
        series=tuple(series),
    )
