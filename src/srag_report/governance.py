from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from .agent.commentary import DEFAULT_OPENAI_MODEL
from .agent.evidence import validate_commentary_claims
from .agent.models import EvidenceBundle
from .domain.source import QualityState
from .metrics.enums import MetricId, MetricState, SeriesGranularity
from .reporting.bundle import RunManifest

_REQUIRED_METRICS = frozenset(
    {
        MetricId.CASE_GROWTH,
        MetricId.MORTALITY_PER_100K,
        MetricId.ICU_PRESSURE,
        MetricId.INFLUENZA_COVERAGE,
        MetricId.HOSPITAL_CFR,
        MetricId.ICU_USE,
    }
)
_REQUIRED_ARTIFACTS = frozenset(
    {
        "request.json",
        "evidence.json",
        "audit.jsonl",
        "charts/daily-cases.svg",
        "charts/monthly-cases.svg",
        "report.html",
    }
)
_PROHIBITED_TEXT = (
    "authorization: bearer",
    "openai_api_key",
    "api_key",
    "notification_key",
    "dt_sin_pri",
    "nu_notific",
)


class GoldenGateResult(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    run_id: str
    eligible: bool
    failures: tuple[str, ...]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate_golden_run(run_path: Path) -> GoldenGateResult:
    failures: list[str] = []
    manifest_path = run_path / "manifest.json"
    evidence_path = run_path / "evidence.json"
    if not manifest_path.is_file() or not evidence_path.is_file():
        return GoldenGateResult(
            run_id=run_path.name,
            eligible=False,
            failures=("missing_manifest_or_evidence",),
        )

    try:
        manifest = RunManifest.model_validate_json(manifest_path.read_text())
        evidence = EvidenceBundle.model_validate_json(evidence_path.read_text())
    except (OSError, ValueError):
        return GoldenGateResult(
            run_id=run_path.name,
            eligible=False,
            failures=("invalid_manifest_or_evidence",),
        )

    if manifest.run_id != run_path.name or evidence.request.run_id != manifest.run_id:
        failures.append("run_id_mismatch")
    if evidence.request.snapshot_id != manifest.snapshot_id:
        failures.append("snapshot_id_mismatch")
    if manifest.execution_mode != "live":
        failures.append("not_live")
    if manifest.degraded_reasons or manifest.fallback_used:
        failures.append("degraded_or_fallback")
    if manifest.requested_model != DEFAULT_OPENAI_MODEL or manifest.served_model == "fallback":
        failures.append("unapproved_or_unserved_model")

    artifact_names = frozenset(manifest.artifact_hashes)
    if artifact_names != _REQUIRED_ARTIFACTS:
        failures.append("incomplete_artifact_set")
    for relative_path, expected_hash in manifest.artifact_hashes.items():
        artifact = run_path / relative_path
        if not artifact.resolve().is_relative_to(run_path.resolve()):
            failures.append(f"artifact_path_escapes_run:{relative_path}")
            continue
        if not artifact.is_file() or _digest(artifact) != expected_hash:
            failures.append(f"artifact_hash_invalid:{relative_path}")

    metrics = {metric.metric_id: metric for metric in evidence.metrics}
    if frozenset(metrics) != _REQUIRED_METRICS:
        failures.append("metric_set_incomplete")
    for metric_id in _REQUIRED_METRICS:
        metric = metrics.get(metric_id)
        if metric is None:
            continue
        if metric.value is None or metric.state not in {
            MetricState.AVAILABLE,
            MetricState.STABLE_ZERO,
        }:
            failures.append(f"metric_unavailable:{metric_id.value}")
        if metric.quality.state is not QualityState.AVAILABLE:
            failures.append(f"metric_quality_not_available:{metric_id.value}")
        if metric.population_scope is not None:
            failures.append(f"metric_scoped:{metric_id.value}")

    series = {item.granularity: item for item in evidence.series}
    daily = series.get(SeriesGranularity.DAILY)
    monthly = series.get(SeriesGranularity.MONTHLY)
    if daily is None or len(daily.points) != 30:
        failures.append("daily_series_incomplete")
    if monthly is None or len(monthly.points) != 12:
        failures.append("monthly_series_incomplete")
    if len(evidence.charts) != 2:
        failures.append("chart_set_incomplete")

    if not evidence.news:
        failures.append("live_news_absent")
    else:
        for item in evidence.news:
            age = manifest.generated_at - item.published_at
            if age < dt.timedelta(0) or age > dt.timedelta(days=14):
                failures.append(f"news_outside_window:{item.news_id}")

    try:
        validate_commentary_claims(manifest.commentary_claims, evidence)
    except ValueError:
        failures.append("commentary_invalid")
    if not manifest.commentary_claims:
        failures.append("commentary_absent")

    audit_path = run_path / "audit.jsonl"
    try:
        events = [json.loads(line) for line in audit_path.read_text().splitlines()]
    except (OSError, ValueError):
        events = []
    if not events or events[-1].get("event_type") != "publication":
        failures.append("critical_publication_event_absent")

    for relative_path in (*manifest.artifact_hashes, "manifest.json"):
        path = run_path / relative_path
        if not path.is_file():
            continue
        text = path.read_text(errors="ignore").casefold()
        if any(marker in text for marker in _PROHIBITED_TEXT):
            failures.append(f"sensitive_content:{relative_path}")

    return GoldenGateResult(
        run_id=manifest.run_id,
        eligible=not failures,
        failures=tuple(dict.fromkeys(failures)),
    )
