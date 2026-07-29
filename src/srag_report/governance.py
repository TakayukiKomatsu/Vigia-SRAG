from __future__ import annotations

import datetime as dt
import hashlib
import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from .agent.commentary import DEFAULT_OPENAI_MODEL, DEFAULT_OPENROUTER_MODEL
from .agent.evidence import validate_commentary_claims
from .agent.graph import NODE_ORDER
from .agent.models import AuditEvent, EventStatus, EvidenceBundle
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
_APPROVED_REQUESTED_MODELS = frozenset({DEFAULT_OPENAI_MODEL, DEFAULT_OPENROUTER_MODEL})
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
_MODEL_SUMMARY = re.compile(
    r"requested_model=(?P<requested>.*); served_model=(?P<served>.*); fallback=(?P<fallback>True|False)"
)


class GoldenGateResult(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    run_id: str
    eligible: bool
    failures: tuple[str, ...]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _audit_failures(events: tuple[AuditEvent, ...], manifest: RunManifest) -> tuple[str, ...]:
    """Validate the complete execution trace required for a golden live run."""
    failures: list[str] = []
    if any(event.run_id != manifest.run_id for event in events):
        failures.append("audit_invalid")
    if [event.sequence for event in events] != list(range(1, len(events) + 1)):
        failures.append("audit_sequence_invalid")
    if any(later.occurred_at < earlier.occurred_at for earlier, later in zip(events, events[1:])):
        failures.append("audit_invalid")

    expected_events: list[tuple[str, str, EventStatus]] = []
    for node in NODE_ORDER:
        expected_events.append(("transition", node, EventStatus.STARTED))
        if node == "generate_commentary":
            expected_events.append(("model", node, EventStatus.SUCCEEDED))
        expected_events.append(
            (
                "publication" if node == NODE_ORDER[-1] else "transition",
                node,
                EventStatus.SUCCEEDED,
            )
        )
    observed_events = tuple(
        (event.event_type, event.component, event.status)
        for event in events
    )
    if tuple(expected_events) != observed_events:
        failures.append("audit_node_order_invalid")

    news_events = tuple(
        event
        for event in events
        if event.event_type == "transition"
        and event.component == "search_news"
        and event.status is EventStatus.SUCCEEDED
    )
    if len(news_events) != 1:
        failures.append("live_news_event_absent")

    model_events = tuple(
        event
        for event in events
        if event.event_type == "model"
        and event.component == "generate_commentary"
        and event.status is EventStatus.SUCCEEDED
    )
    if len(model_events) != 1:
        failures.append("model_event_absent")
    else:
        match = _MODEL_SUMMARY.fullmatch(model_events[0].summary)
        if (
            match is None
            or match["requested"] != manifest.requested_model
            or match["served"] != manifest.served_model
            or (match["fallback"] == "True") != manifest.fallback_used
        ):
            failures.append("model_event_absent")

    publication_events = tuple(event for event in events if event.event_type == "publication")
    if len(publication_events) != 1 or publication_events[0].artifact_hashes != {
        "report.html": manifest.artifact_hashes.get("report.html", "")
    }:
        failures.append("audit_invalid")
    if any(
        manifest.artifact_hashes.get(path) != digest
        for event in events
        for path, digest in event.artifact_hashes.items()
    ):
        failures.append("audit_invalid")
    return tuple(dict.fromkeys(failures))


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
    served_model = manifest.served_model.strip()
    if (
        not manifest.requested_model
        or manifest.requested_model not in _APPROVED_REQUESTED_MODELS
        or not served_model
        or served_model.casefold() == "fallback"
    ):
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
        if (
            metric_id is MetricId.INFLUENZA_COVERAGE
            and metric.state in {MetricState.AVAILABLE, MetricState.STABLE_ZERO}
            and not metric.population_scope
        ):
            failures.append("influenza_scope_missing")

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
        lines = audit_path.read_text().splitlines()
        events = tuple(AuditEvent.model_validate_json(line) for line in lines)
    except (OSError, ValueError):
        failures.append("audit_invalid")
    else:
        if not events:
            failures.append("audit_invalid")
        else:
            failures.extend(_audit_failures(events, manifest))

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
