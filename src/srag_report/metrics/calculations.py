from __future__ import annotations

import calendar
import datetime as dt
from collections.abc import Mapping

from ..domain.models import PniObservation
from ..domain.source import QualityState
from .enums import (
    MetricFormula,
    MetricId,
    MetricState,
    PointState,
    SeriesGranularity,
    UnavailableReason,
)
from .models import MetricResult, QualityResult, SeriesPoint, SeriesResult
from .time import (
    daily_30_day_period,
    last_four_stabilized_weeks,
    mature_cohort_end,
    mature_cohort_start,
    monthly_12_month_period,
    reference_week_end,
)


def quality_result(completeness: float, blocker: str | None = None) -> QualityResult:
    if blocker is not None:
        return QualityResult(
            completeness=completeness,
            state=QualityState.BLOCKED,
            blocker=blocker,
        )
    if completeness >= 0.9:
        state = QualityState.AVAILABLE
    elif completeness >= 0.7:
        state = QualityState.WARNING
    else:
        state = QualityState.UNAVAILABLE
    return QualityResult(completeness=completeness, state=state)


def _metric_gate(quality: QualityResult) -> tuple[MetricState, UnavailableReason | None]:
    if quality.state is QualityState.BLOCKED:
        return MetricState.UNAVAILABLE, UnavailableReason.STRUCTURAL_BLOCKER
    if quality.state is QualityState.UNAVAILABLE:
        return MetricState.UNAVAILABLE, UnavailableReason.COMPLETENESS_LOW
    if quality.state is QualityState.WARNING:
        return MetricState.WARNING, None
    return MetricState.AVAILABLE, None


def case_growth(
    *,
    previous_cases: int,
    current_cases: int,
    as_of: dt.date,
    snapshot_id: str,
    completeness: float,
    source_ids: tuple[str, ...] = ("sivep",),
    blocker: str | None = None,
) -> MetricResult:
    end = reference_week_end(as_of)
    start = end - dt.timedelta(days=6)
    quality = quality_result(completeness, blocker)
    state, reason = _metric_gate(quality)
    value: float | None
    if state is MetricState.UNAVAILABLE:
        value = None
    elif previous_cases == 0 and current_cases == 0:
        state = MetricState.STABLE_ZERO
        value = 0.0
    elif previous_cases == 0:
        state = MetricState.NEW_ACTIVITY
        value = None
    else:
        value = round((current_cases - previous_cases) / previous_cases * 100.0, 2)
    return MetricResult(
        metric_id=MetricId.CASE_GROWTH,
        label="Taxa de aumento de casos",
        value=value,
        state=state,
        reason=reason,
        unit="%",
        numerator=float(current_cases - previous_cases),
        denominator=float(previous_cases),
        period_start=start,
        period_end=end,
        snapshot_id=snapshot_id,
        formula_version=MetricFormula.CASE_GROWTH_V1,
        quality=quality,
        source_ids=source_ids,
        limitations=(
            f"Casos na semana de referência: {current_cases}; semana anterior: {previous_cases}.",
        ),
    )


def population_mortality(
    *,
    deaths: int,
    population: int,
    as_of: dt.date,
    snapshot_id: str,
    completeness: float,
    source_ids: tuple[str, ...] = ("sivep", "ibge"),
    blocker: str | None = None,
) -> MetricResult:
    start, end = last_four_stabilized_weeks(as_of)
    quality = quality_result(completeness, blocker)
    state, reason = _metric_gate(quality)
    if state is not MetricState.UNAVAILABLE and population == 0:
        state, reason = MetricState.UNAVAILABLE, UnavailableReason.ZERO_DENOMINATOR
    value = None if state is MetricState.UNAVAILABLE else round(deaths / population * 100_000, 2)
    return MetricResult(
        metric_id=MetricId.MORTALITY_PER_100K,
        label="Taxa de mortalidade por SRAG",
        value=value,
        state=state,
        reason=reason,
        unit="óbitos por 100 mil habitantes",
        numerator=float(deaths) if state is not MetricState.UNAVAILABLE else None,
        denominator=float(population) if state is not MetricState.UNAVAILABLE else None,
        period_start=start,
        period_end=end,
        snapshot_id=snapshot_id,
        formula_version=MetricFormula.MORTALITY_PER_100K_V1,
        quality=quality,
        source_ids=source_ids,
    )


def hospital_case_fatality(
    *,
    deaths: int,
    known_outcomes: int,
    unknown_outcomes: int,
    as_of: dt.date,
    snapshot_id: str,
    completeness: float,
    source_ids: tuple[str, ...] = ("sivep",),
    blocker: str | None = None,
) -> MetricResult:
    start, end = mature_cohort_start(as_of), mature_cohort_end(as_of)
    quality = quality_result(completeness, blocker)
    state, reason = _metric_gate(quality)
    if state is not MetricState.UNAVAILABLE and known_outcomes == 0:
        state, reason = MetricState.UNAVAILABLE, UnavailableReason.ZERO_DENOMINATOR
    value = None if state is MetricState.UNAVAILABLE else round(deaths / known_outcomes * 100.0, 2)
    return MetricResult(
        metric_id=MetricId.HOSPITAL_CFR,
        label="Letalidade hospitalar suplementar por SRAG",
        value=value,
        state=state,
        reason=reason,
        unit="%",
        numerator=float(deaths) if state is not MetricState.UNAVAILABLE else None,
        denominator=float(known_outcomes) if state is not MetricState.UNAVAILABLE else None,
        period_start=start,
        period_end=end,
        snapshot_id=snapshot_id,
        formula_version=MetricFormula.HOSPITAL_CFR_V1,
        quality=quality,
        source_ids=source_ids,
        limitations=(f"{unknown_outcomes} internações com evolução desconhecida foram excluídas.",),
    )


def icu_use(
    *,
    icu_admissions: int,
    known_icu_status: int,
    period_start: dt.date,
    period_end: dt.date,
    snapshot_id: str,
    completeness: float,
    source_ids: tuple[str, ...] = ("sivep",),
    blocker: str | None = None,
) -> MetricResult:
    quality = quality_result(completeness, blocker)
    state, reason = _metric_gate(quality)
    if state is not MetricState.UNAVAILABLE and known_icu_status == 0:
        state, reason = MetricState.UNAVAILABLE, UnavailableReason.ZERO_DENOMINATOR
    value = (
        None
        if state is MetricState.UNAVAILABLE
        else round(icu_admissions / known_icu_status * 100.0, 2)
    )
    return MetricResult(
        metric_id=MetricId.ICU_USE,
        label="Uso de UTI entre hospitalizações por SRAG — indicador suplementar",
        value=value,
        state=state,
        reason=reason,
        unit="%",
        numerator=float(icu_admissions) if state is not MetricState.UNAVAILABLE else None,
        denominator=float(known_icu_status) if state is not MetricState.UNAVAILABLE else None,
        period_start=period_start,
        period_end=period_end,
        snapshot_id=snapshot_id,
        formula_version=MetricFormula.ICU_USE_V1,
        quality=quality,
        source_ids=source_ids,
        limitations=("Indicador de uso entre casos SRAG; não representa ocupação de leitos.",),
    )


def icu_pressure(
    *,
    patient_days: int,
    bed_days: int,
    period_start: dt.date,
    period_end: dt.date,
    excluded_open_stays: int,
    snapshot_id: str,
    completeness: float,
    source_ids: tuple[str, ...] = ("sivep", "cnes"),
    blocker: str | None = None,
) -> MetricResult:
    quality = quality_result(completeness, blocker)
    state, reason = _metric_gate(quality)
    if state is not MetricState.UNAVAILABLE and bed_days == 0:
        state, reason = MetricState.UNAVAILABLE, UnavailableReason.ZERO_DENOMINATOR
    raw = None if state is MetricState.UNAVAILABLE else patient_days / bed_days * 100.0
    if raw is not None and raw > 100.0:
        state, reason, raw = (
            MetricState.UNAVAILABLE,
            UnavailableReason.RATIO_ABOVE_100_PCT,
            None,
        )
    return MetricResult(
        metric_id=MetricId.ICU_PRESSURE,
        label="Pressão estimada de SRAG sobre a capacidade registrada de UTI",
        value=None if raw is None else round(raw, 2),
        state=state,
        reason=reason,
        unit="%",
        numerator=float(patient_days) if raw is not None else None,
        denominator=float(bed_days) if raw is not None else None,
        period_start=period_start,
        period_end=period_end,
        snapshot_id=snapshot_id,
        formula_version=MetricFormula.ICU_PRESSURE_V1,
        quality=quality,
        source_ids=source_ids,
        limitations=(
            "Não é ocupação observada por todas as causas; usa capacidade CNES registrada.",
            f"{excluded_open_stays} permanências sem saída conhecida foram excluídas.",
        ),
    )


def influenza_coverage(
    *,
    observation: PniObservation | None,
    as_of: dt.date,
    snapshot_id: str,
    completeness: float,
    source_ids: tuple[str, ...] = ("pni",),
    blocker: str | None = None,
) -> MetricResult:
    quality = quality_result(completeness, blocker)
    state, reason = _metric_gate(quality)
    if state is MetricState.UNAVAILABLE:
        period_start = observation.period_start if observation is not None else as_of
        period_end = observation.period_end if observation is not None else as_of
        numerator = denominator = value = None
        scope = None
        limitations = ("Indicador indisponível pelo estado de qualidade da fonte.",)
    elif observation is None or observation.published_at.date() > as_of:
        state = MetricState.UNAVAILABLE
        reason = UnavailableReason.NOT_PUBLISHED_BY_CUTOFF
        period_start = period_end = as_of
        numerator = denominator = value = None
        scope = None
        limitations = ("Observação não publicada até o cutoff solicitado.",)
    else:
        period_start, period_end = observation.period_start, observation.period_end
        numerator = float(observation.numerator)
        denominator = float(observation.denominator)
        value = float(observation.coverage_pct)
        scope = observation.population_scope
        limitations = (
            ("Cobertura de escopo regional; não representa cobertura nacional.",)
            if not observation.is_nationwide
            else ()
        )
    return MetricResult(
        metric_id=MetricId.INFLUENZA_COVERAGE,
        label="Cobertura vacinal contra influenza 2026",
        value=value,
        state=state,
        reason=reason,
        unit="%",
        numerator=numerator,
        denominator=denominator,
        period_start=period_start,
        period_end=period_end,
        snapshot_id=snapshot_id,
        formula_version=MetricFormula.INFLUENZA_COVERAGE_V1,
        quality=quality,
        source_ids=source_ids,
        limitations=limitations,
        population_scope=scope,
    )


def daily_case_series(
    counts: Mapping[dt.date, int],
    *,
    coverage_start: dt.date,
    coverage_end: dt.date,
    as_of: dt.date,
    snapshot_id: str,
    completeness: float,
    source_ids: tuple[str, ...] = ("sivep",),
) -> SeriesResult | None:
    periods = daily_30_day_period(as_of)
    if coverage_start > periods[0] or coverage_end < periods[-1]:
        return None
    points = tuple(
        SeriesPoint(
            period=period,
            value=counts.get(period, 0),
            state=PointState.STABLE if index < 16 else PointState.PROVISIONAL,
        )
        for index, period in enumerate(periods)
    )
    return SeriesResult(
        series_id="daily_srag_cases",
        granularity=SeriesGranularity.DAILY,
        points=points,
        period_start=periods[0],
        period_end=periods[-1],
        snapshot_id=snapshot_id,
        quality=quality_result(completeness),
        source_ids=source_ids,
    )


def monthly_case_series(
    counts: Mapping[dt.date, int],
    *,
    coverage_start: dt.date,
    coverage_end: dt.date,
    as_of: dt.date,
    snapshot_id: str,
    completeness: float,
    source_ids: tuple[str, ...] = ("sivep",),
) -> SeriesResult | None:
    periods = monthly_12_month_period(as_of)
    last_day = periods[-1].replace(day=calendar.monthrange(periods[-1].year, periods[-1].month)[1])
    if coverage_start > periods[0] or coverage_end < last_day:
        return None
    points = tuple(
        SeriesPoint(period=period, value=counts.get(period, 0), state=PointState.STABLE)
        for period in periods
    )
    return SeriesResult(
        series_id="monthly_srag_cases",
        granularity=SeriesGranularity.MONTHLY,
        points=points,
        period_start=periods[0],
        period_end=last_day,
        snapshot_id=snapshot_id,
        quality=quality_result(completeness),
        source_ids=source_ids,
    )
