from __future__ import annotations

import datetime as dt
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from srag_report.domain.source import QualityState
from srag_report.metrics.calculations import daily_case_series
from srag_report.metrics.charts import render_series_svg
from srag_report.metrics.models import QualityResult, SeriesResult

_AS_OF = dt.date(2026, 7, 28)
_SVG = {"svg": "http://www.w3.org/2000/svg"}


def _series() -> SeriesResult:
    result = daily_case_series(
        {_AS_OF - dt.timedelta(days=1): 4, _AS_OF: 7},
        coverage_start=_AS_OF - dt.timedelta(days=60),
        coverage_end=_AS_OF,
        as_of=_AS_OF,
        snapshot_id="snapshot",
        completeness=1.0,
    )
    assert result is not None
    return result


def test_svg_points_match_series_exactly(tmp_path: Path) -> None:
    series = _series()
    chart = render_series_svg(
        series,
        tmp_path / "daily.svg",
        title="Casos diários de SRAG — Brasil",
        watermark=_AS_OF,
    )
    root = ET.parse(chart.path).getroot()
    groups = root.findall(".//svg:g[@id='series-points']/svg:g", _SVG)
    assert len(groups) == 30
    assert [group.attrib["data-period"] for group in groups] == [
        point.period.isoformat() for point in series.points
    ]
    assert [int(group.attrib["data-value"]) for group in groups] == [
        point.value for point in series.points
    ]
    assert [group.attrib["data-state"] for group in groups] == [
        point.state.value for point in series.points
    ]


def test_svg_contains_accessible_metadata(tmp_path: Path) -> None:
    chart = render_series_svg(
        _series(),
        tmp_path / "daily.svg",
        title="Casos diários de SRAG — Brasil",
        watermark=_AS_OF,
    )
    text = Path(chart.path).read_text(encoding="utf-8")
    assert '<title id="chart-title">' in text
    assert '<desc id="chart-description">' in text
    assert "Fonte: sivep" in text
    assert "Watermark: 2026-07-28" in text
    assert "2026-06-29 a 2026-07-28" in text
    assert chart.alt_text


def test_svg_bytes_are_deterministic(tmp_path: Path) -> None:
    series = _series()
    first = render_series_svg(
        series, tmp_path / "first.svg", title="Casos diários", watermark=_AS_OF
    )
    second = render_series_svg(
        series, tmp_path / "second.svg", title="Casos diários", watermark=_AS_OF
    )
    assert Path(first.path).read_bytes() == Path(second.path).read_bytes()
    assert first.sha256 == second.sha256


def test_unavailable_series_is_not_rendered(tmp_path: Path) -> None:
    unavailable = _series().model_copy(
        update={
            "quality": QualityResult(
                completeness=0.5,
                state=QualityState.UNAVAILABLE,
            )
        }
    )
    with pytest.raises(ValueError, match="must not be rendered"):
        render_series_svg(
            unavailable,
            tmp_path / "unavailable.svg",
            title="Indisponível",
            watermark=_AS_OF,
        )
    assert not (tmp_path / "unavailable.svg").exists()
