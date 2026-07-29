from __future__ import annotations

import datetime as dt
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, TypedDict, cast

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from ..audit.sink import AuditSink
from ..metrics.models import ChartResult
from ..metrics.query import MetricPackage
from ..metrics.time import resolve_as_of
from ..reporting.bundle import RunWorkspace
from ..reporting.html import render_report_html
from ..tools.analytics import ChartsTool, MetricsTool
from .commentary import CommentaryAdapter, commentary_evidence_ids, generate_or_fallback
from .evidence import build_evidence_bundle, deterministic_fallback, validate_commentary_claims
from .models import (
    CommentaryFailureCode,
    CommentaryResult,
    EventStatus,
    EvidenceBundle,
    NewsItem,
    ReportRequest,
)

NODE_ORDER = (
    "validate_request",
    "select_snapshot",
    "collect_metrics",
    "render_charts",
    "search_news",
    "validate_evidence",
    "generate_commentary",
    "validate_commentary",
    "render_report",
    "finalize_run",
)


class NewsTool(Protocol):
    def collect(self, *, generated_at: dt.datetime) -> tuple[NewsItem, ...]: ...


@dataclass(frozen=True, slots=True)
class GraphDependencies:
    metrics: MetricsTool
    charts: ChartsTool
    news: NewsTool
    commentary: CommentaryAdapter
    workspace: RunWorkspace
    audit: AuditSink
    generated_at: dt.datetime
    sources: tuple[str, ...]
    watermarks: Mapping[str, str]
    execution_mode: Literal["deterministic", "live"] = "deterministic"
    timeout_seconds: float = 120.0


class ReportState(TypedDict, total=False):
    request: ReportRequest
    package: MetricPackage
    charts: tuple[ChartResult, ...]
    news: tuple[NewsItem, ...]
    evidence: EvidenceBundle
    commentary: CommentaryResult
    report_sha256: str
    run_path: Path
    degraded_reasons: tuple[str, ...]
    trace: tuple[str, ...]


def _trace(state: ReportState, node: str) -> tuple[str, ...]:
    return (*state.get("trace", ()), node)


def _degraded(state: ReportState, reason: str) -> tuple[str, ...]:
    return (*state.get("degraded_reasons", ()), reason)


def build_report_graph(
    dependencies: GraphDependencies,
) -> CompiledStateGraph[ReportState, None, ReportState, ReportState]:
    started_at = time.monotonic()

    def ensure_deadline() -> None:
        if time.monotonic() - started_at > dependencies.timeout_seconds:
            raise TimeoutError("global report timeout exceeded")

    def duration_ms(node_started: float) -> int:
        if dependencies.execution_mode == "deterministic":
            return 0
        return int((time.monotonic() - node_started) * 1000)

    def run_node(
        node_name: str,
        action: Callable[[ReportState], ReportState],
    ) -> Callable[[ReportState], ReportState]:
        def node(state: ReportState) -> ReportState:
            ensure_deadline()
            node_started = time.monotonic()
            dependencies.audit.emit(
                event_type="transition",
                component=node_name,
                status=EventStatus.STARTED,
                summary=f"{node_name} started",
            )
            try:
                update = action(state).copy()
                status = (
                    EventStatus.DEGRADED
                    if len(update.get("degraded_reasons", ()))
                    > len(state.get("degraded_reasons", ()))
                    else EventStatus.SUCCEEDED
                )
                dependencies.audit.emit(
                    event_type="transition",
                    component=node_name,
                    status=status,
                    summary=f"{node_name} completed",
                    duration_ms=duration_ms(node_started),
                )
                update["trace"] = _trace(state, node_name)
                return update
            except Exception as exc:
                dependencies.audit.emit(
                    event_type="failure",
                    component=node_name,
                    status=EventStatus.FAILED,
                    summary=f"{node_name} failed: {type(exc).__name__}",
                    duration_ms=duration_ms(node_started),
                )
                raise

        return node

    def validate_request(state: ReportState) -> ReportState:
        request = state["request"]
        if request.geography != "BR":
            raise ValueError("only geography BR is supported")
        resolve_as_of(dependencies.metrics.watermark, request.as_of)
        return {}

    def select_snapshot(state: ReportState) -> ReportState:
        dependencies.metrics.validate_snapshot(state["request"])
        return {}

    def collect_metrics(state: ReportState) -> ReportState:
        return {"package": dependencies.metrics.collect(state["request"])}

    def render_charts(state: ReportState) -> ReportState:
        package = state["package"]
        charts = dependencies.charts.render(
            package.series,
            output_dir=dependencies.workspace.charts_dir,
            watermark=package.watermark,
        )
        update: ReportState = {"charts": charts}
        if len(charts) < 2:
            update["degraded_reasons"] = _degraded(state, "insufficient_series")
        return update

    def search_news(state: ReportState) -> ReportState:
        try:
            news = dependencies.news.collect(generated_at=dependencies.generated_at)
        except Exception:
            news = ()
        update: ReportState = {"news": news}
        if not news:
            update["degraded_reasons"] = _degraded(state, "news_unavailable")
        return update

    def validate_evidence(state: ReportState) -> ReportState:
        evidence = build_evidence_bundle(
            request=state["request"],
            package=state["package"],
            charts=state["charts"],
            news=state["news"],
            sources=dependencies.sources,
            watermarks=dependencies.watermarks,
        )
        dependencies.workspace.write_evidence(evidence)
        return {"evidence": evidence}

    def generate_commentary(state: ReportState) -> ReportState:
        commentary = generate_or_fallback(dependencies.commentary, state["evidence"])
        dependencies.audit.emit(
            event_type="model",
            component="generate_commentary",
            status=(EventStatus.DEGRADED if commentary.fallback_used else EventStatus.SUCCEEDED),
            summary=(
                f"requested_model={commentary.requested_model}; "
                f"served_model={commentary.served_model}; "
                f"fallback={commentary.fallback_used}"
            ),
        )
        update: ReportState = {"commentary": commentary}
        if commentary.fallback_used:
            assert commentary.failure_code is not None
            update["degraded_reasons"] = _degraded(state, commentary.failure_code.value)
        return update

    def validate_commentary(state: ReportState) -> ReportState:
        commentary = state["commentary"]
        try:
            claims = validate_commentary_claims(commentary.claims, state["evidence"])
            return {"commentary": commentary.model_copy(update={"claims": claims})}
        except ValueError:
            dependencies.audit.emit(
                event_type="guardrail",
                component="validate_commentary",
                status=EventStatus.DEGRADED,
                summary=CommentaryFailureCode.COMMENTARY_REJECTED.value,
                evidence_ids=commentary_evidence_ids(state["evidence"]),
            )
            fallback = CommentaryResult(
                claims=deterministic_fallback(state["evidence"]),
                requested_model=commentary.requested_model,
                served_model=commentary.served_model,
                fallback_used=True,
                failure_code=CommentaryFailureCode.COMMENTARY_REJECTED,
            )
            validate_commentary_claims(fallback.claims, state["evidence"])
            return {
                "commentary": fallback,
                "degraded_reasons": _degraded(
                    state, CommentaryFailureCode.COMMENTARY_REJECTED.value
                ),
            }

    def render_report(state: ReportState) -> ReportState:
        digest = render_report_html(
            state["evidence"],
            state["commentary"],
            generated_at=dependencies.generated_at,
            output_path=dependencies.workspace.report_path,
            execution_mode=dependencies.execution_mode,
        )
        return {"report_sha256": digest}

    def finalize_run(state: ReportState) -> ReportState:
        ensure_deadline()
        dependencies.audit.emit(
            event_type="transition",
            component="finalize_run",
            status=EventStatus.STARTED,
            summary="finalize_run started",
        )
        dependencies.audit.emit(
            event_type="publication",
            component="finalize_run",
            status=EventStatus.SUCCEEDED,
            summary="complete run bundle validated for atomic publication",
            artifact_hashes={"report.html": state["report_sha256"]},
        )
        run_path = dependencies.workspace.finalize(
            generated_at=dependencies.generated_at,
            commentary=state["commentary"],
            degraded_reasons=state.get("degraded_reasons", ()),
            execution_mode=dependencies.execution_mode,
        )
        return {"run_path": run_path, "trace": _trace(state, "finalize_run")}

    builder = StateGraph(ReportState)
    actions = {
        "validate_request": validate_request,
        "select_snapshot": select_snapshot,
        "collect_metrics": collect_metrics,
        "render_charts": render_charts,
        "search_news": search_news,
        "validate_evidence": validate_evidence,
        "generate_commentary": generate_commentary,
        "validate_commentary": validate_commentary,
        "render_report": render_report,
    }
    for name in NODE_ORDER[:-1]:
        builder.add_node(name, run_node(name, actions[name]))  # type: ignore[call-overload]
    builder.add_node("finalize_run", finalize_run)
    builder.add_edge(START, NODE_ORDER[0])
    for source, target in zip(NODE_ORDER, NODE_ORDER[1:], strict=False):
        builder.add_edge(source, target)
    builder.add_edge(NODE_ORDER[-1], END)
    return cast(
        CompiledStateGraph[ReportState, None, ReportState, ReportState],
        builder.compile(),
    )


def run_report(request: ReportRequest, dependencies: GraphDependencies) -> ReportState:
    graph = build_report_graph(dependencies)
    result = graph.invoke(
        ReportState(
            request=request,
            degraded_reasons=(),
            trace=(),
        )
    )
    return cast(ReportState, result)
