from __future__ import annotations

import datetime as dt
from collections.abc import Mapping, Sequence
from pathlib import Path

from ..agent.models import ReportRequest
from ..data.store import snapshot_table_counts
from ..metrics.charts import render_series_svg
from ..metrics.enums import MetricId, SeriesGranularity
from ..metrics.models import ChartResult, SeriesResult
from ..metrics.query import MetricPackage, compute_metric_package


class MetricsTool:
    """Fixed aggregate-only DuckDB tool; no SQL, table, column, or row interface."""

    def __init__(
        self,
        snapshot_path: Path,
        *,
        watermark: dt.date,
        completeness: Mapping[MetricId | str, float] | None = None,
        blockers: Mapping[MetricId | str, str] | None = None,
    ) -> None:
        self._snapshot_path = snapshot_path
        self._watermark = watermark
        self._completeness = completeness
        self._blockers = blockers

    @property
    def watermark(self) -> dt.date:
        return self._watermark

    def validate_snapshot(self, request: ReportRequest) -> None:
        if not self._snapshot_path.is_file():
            raise FileNotFoundError(f"snapshot not found: {request.snapshot_id}")
        snapshot_table_counts(self._snapshot_path)

    def collect(self, request: ReportRequest) -> MetricPackage:
        return compute_metric_package(
            self._snapshot_path,
            snapshot_id=request.snapshot_id,
            watermark=self._watermark,
            requested_as_of=request.as_of,
            completeness=self._completeness,
            blockers=self._blockers,
        )


class ChartsTool:
    """Render only validated series through the fixed SVG renderer."""

    def render(
        self,
        series: Sequence[SeriesResult],
        *,
        output_dir: Path,
        watermark: dt.date,
    ) -> tuple[ChartResult, ...]:
        charts: list[ChartResult] = []
        for item in series:
            if item.granularity is SeriesGranularity.DAILY:
                filename = "daily-cases.svg"
                title = "Casos diários de SRAG — Brasil"
            else:
                filename = "monthly-cases.svg"
                title = "Casos mensais de SRAG — Brasil"
            charts.append(
                render_series_svg(
                    item,
                    output_dir / filename,
                    title=title,
                    watermark=watermark,
                )
            )
        return tuple(charts)
