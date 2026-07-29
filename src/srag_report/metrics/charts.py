from __future__ import annotations

import datetime as dt
import hashlib
import os
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from ..domain.source import QualityState
from .enums import PointState
from .models import ChartResult, SeriesResult

_SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", _SVG)


def _element(parent: ET.Element, tag: str, attributes: dict[str, str] | None = None) -> ET.Element:
    return ET.SubElement(parent, f"{{{_SVG}}}{tag}", attributes or {})


def render_series_svg(
    series: SeriesResult,
    output_path: Path,
    *,
    title: str,
    watermark: dt.date,
    unit: str = "casos",
) -> ChartResult:
    """Render a byte-stable SVG whose data-point metadata mirrors ``series`` exactly."""
    if series.quality.state in {QualityState.UNAVAILABLE, QualityState.BLOCKED}:
        raise ValueError("unavailable series must not be rendered")
    width, height = 960, 480
    left, top, right, bottom = 70, 50, 30, 80
    plot_width = width - left - right
    plot_height = height - top - bottom
    maximum = max((point.value for point in series.points), default=0) or 1
    period = f"{series.period_start.isoformat()} a {series.period_end.isoformat()}"
    source_text = ", ".join(series.source_ids)
    watermark_text = watermark.isoformat()
    alt_text = (
        f"Gráfico da série {title}, com {len(series.points)} pontos de {period}, "
        f"em {unit}. Fonte: {source_text}. Watermark: {watermark_text}."
    )

    root = ET.Element(
        f"{{{_SVG}}}svg",
        {
            "width": str(width),
            "height": str(height),
            "viewBox": f"0 0 {width} {height}",
            "role": "img",
            "aria-labelledby": "chart-title chart-description",
        },
    )
    title_node = _element(root, "title", {"id": "chart-title"})
    title_node.text = title
    description = _element(root, "desc", {"id": "chart-description"})
    description.text = alt_text
    metadata = _element(root, "metadata")
    metadata.text = (
        f"period={period};unit={unit};sources={source_text};watermark={watermark_text};"
        f"series_id={series.series_id}"
    )
    background = _element(
        root,
        "rect",
        {"x": "0", "y": "0", "width": str(width), "height": str(height), "fill": "#ffffff"},
    )
    background.tail = ""
    _element(
        root,
        "line",
        {
            "x1": str(left),
            "y1": str(top + plot_height),
            "x2": str(left + plot_width),
            "y2": str(top + plot_height),
            "stroke": "#333333",
        },
    )
    _element(
        root,
        "line",
        {
            "x1": str(left),
            "y1": str(top),
            "x2": str(left),
            "y2": str(top + plot_height),
            "stroke": "#333333",
        },
    )
    heading = _element(
        root,
        "text",
        {"x": str(left), "y": "28", "font-family": "sans-serif", "font-size": "18"},
    )
    heading.text = title
    subtitle = _element(
        root,
        "text",
        {"x": str(left), "y": "46", "font-family": "sans-serif", "font-size": "11"},
    )
    subtitle.text = f"{period} | {unit} | Fonte: {source_text} | Watermark: {watermark_text}"

    step = plot_width / len(series.points)
    bar_width = max(1.0, step * 0.78)
    points_group = _element(root, "g", {"id": "series-points"})
    for index, point in enumerate(series.points):
        bar_height = point.value / maximum * plot_height
        x = left + index * step + (step - bar_width) / 2
        y = top + plot_height - bar_height
        group = _element(
            points_group,
            "g",
            {
                "id": f"point-{index:02d}",
                "data-period": point.period.isoformat(),
                "data-value": str(point.value),
                "data-state": point.state.value,
            },
        )
        _element(
            group,
            "rect",
            {
                "x": f"{x:.3f}",
                "y": f"{y:.3f}",
                "width": f"{bar_width:.3f}",
                "height": f"{bar_height:.3f}",
                "fill": "#E69F00" if point.state is PointState.PROVISIONAL else "#0072B2",
                "opacity": "0.70" if point.state is PointState.PROVISIONAL else "1.00",
            },
        )
        point_title = _element(group, "title")
        point_title.text = f"{point.period.isoformat()}: {point.value} {unit} ({point.state.value})"

    footer = _element(
        root,
        "text",
        {
            "x": str(left),
            "y": str(height - 24),
            "font-family": "sans-serif",
            "font-size": "11",
        },
    )
    footer.text = "Azul: estável. Laranja: provisório nos 14 dias mais recentes."

    payload = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.", dir=output_path.parent
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        temporary_path.write_bytes(payload)
        os.replace(temporary_path, output_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    digest = hashlib.sha256(payload).hexdigest()
    return ChartResult(
        chart_id=f"{series.series_id}_svg",
        series_id=series.series_id,
        path=str(output_path),
        sha256=digest,
        title=title,
        period=period,
        unit=unit,
        source_ids=series.source_ids,
        watermark=watermark,
        alt_text=alt_text,
    )
