from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path

from ..metrics.enums import MetricState
from ..metrics.models import ChartResult
from ..metrics.query import MetricPackage
from .models import CommentaryClaim, EvidenceBundle, NewsItem, ReportRequest

_URL = re.compile(r"(?:https?://|www\.)", re.IGNORECASE)
_NUMBER = re.compile(r"(?<![A-Za-z])\d+(?:[.,]\d+)?")
_PROHIBITED = re.compile(
    r"\b(?:diagn[oó]stic|tratament|prescrev|recomenda(?:ç[aã]o|mos)?|"
    r"caus(?:a|ou|ado)|deve procurar|ignore previous|system prompt|instru[cç][aã]o)\b",
    re.IGNORECASE,
)


def build_evidence_bundle(
    *,
    request: ReportRequest,
    package: MetricPackage,
    charts: Sequence[ChartResult],
    news: Sequence[NewsItem],
    sources: Sequence[str],
    watermarks: Mapping[str, str],
) -> EvidenceBundle:
    if package.snapshot_id != request.snapshot_id or package.as_of != request.as_of:
        raise ValueError("metric package differs from request")
    series_ids = {series.series_id for series in package.series}
    normalized_charts: list[ChartResult] = []
    for chart in charts:
        if chart.series_id not in series_ids:
            raise ValueError(f"chart references unknown series: {chart.series_id}")
        path = Path(chart.path)
        if not path.is_file():
            raise ValueError(f"chart artifact is missing: {path}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != chart.sha256:
            raise ValueError(f"chart hash mismatch: {chart.chart_id}")
        normalized_charts.append(chart.model_copy(update={"path": f"charts/{path.name}"}))
    if len(news) > 5:
        raise ValueError("evidence bundle accepts at most five news items")
    return EvidenceBundle(
        request=request,
        metrics=package.metrics,
        series=package.series,
        charts=tuple(normalized_charts),
        news=tuple(news),
        sources=tuple(sources),
        watermarks=dict(watermarks),
        quality=tuple(
            [
                *(metric.quality for metric in package.metrics),
                *(series.quality for series in package.series),
            ]
        ),
    )


def _evidence_payloads(bundle: EvidenceBundle) -> dict[str, str]:
    payloads: dict[str, str] = {}
    for metric in bundle.metrics:
        payloads[f"metric:{metric.metric_id.value}"] = metric.model_dump_json()
    for series in bundle.series:
        payloads[f"series:{series.series_id}"] = series.model_dump_json()
    for chart in bundle.charts:
        payloads[f"chart:{chart.chart_id}"] = chart.model_dump_json()
    for item in bundle.news:
        payloads[f"news:{item.news_id}"] = item.model_dump_json()
    return payloads


def _numbers(text: str) -> set[str]:
    return {
        format(Decimal(match.replace(",", ".")).normalize(), "f") for match in _NUMBER.findall(text)
    }


def validate_commentary_claims(
    claims: Sequence[CommentaryClaim],
    bundle: EvidenceBundle,
) -> tuple[CommentaryClaim, ...]:
    payloads = _evidence_payloads(bundle)
    valid_ids = set(payloads)
    seen_claims: set[str] = set()
    validated: list[CommentaryClaim] = []
    for claim in claims:
        if claim.claim_id in seen_claims:
            raise ValueError(f"duplicate claim ID: {claim.claim_id}")
        seen_claims.add(claim.claim_id)
        unknown = set(claim.evidence_ids) - valid_ids
        if unknown:
            raise ValueError(f"claim cites unknown evidence IDs: {sorted(unknown)}")
        if _URL.search(claim.text):
            raise ValueError("commentary claims must not invent or repeat URLs")
        if _PROHIBITED.search(claim.text):
            raise ValueError("commentary contains prohibited causal/clinical/instruction language")
        claim_numbers = _numbers(claim.text)
        evidence_numbers = _numbers(
            "\n".join(payloads[evidence_id] for evidence_id in claim.evidence_ids)
        )
        if not claim_numbers <= evidence_numbers:
            missing_numbers = sorted(claim_numbers - evidence_numbers)
            raise ValueError(
                f"claim contains numbers absent from cited evidence: {missing_numbers}"
            )
        validated.append(claim)
    return tuple(validated)


def deterministic_fallback(bundle: EvidenceBundle) -> tuple[CommentaryClaim, ...]:
    claims: list[CommentaryClaim] = []
    for metric in bundle.metrics:
        evidence_id = f"metric:{metric.metric_id.value}"
        if metric.state is MetricState.UNAVAILABLE:
            assert metric.reason is not None
            text = f"{metric.label}: resultado indisponível ({metric.reason.value})."
        elif metric.state is MetricState.NEW_ACTIVITY:
            text = f"{metric.label}: nova atividade, sem percentual infinito publicado."
        else:
            text = f"{metric.label}: {metric.value:g} {metric.unit}."
        claims.append(
            CommentaryClaim(
                claim_id=f"fallback-{metric.metric_id.value}",
                text=text,
                evidence_ids=(evidence_id,),
            )
        )
    return tuple(claims)
