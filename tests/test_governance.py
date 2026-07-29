from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path

import pytest
from test_graph import _AS_OF, _GENERATED, _dependencies

from srag_report.agent.commentary import DEFAULT_OPENROUTER_MODEL
from srag_report.agent.evidence import deterministic_fallback
from srag_report.agent.graph import run_report
from srag_report.agent.models import CommentaryResult, EventStatus, EvidenceBundle, ReportRequest
from srag_report.governance import evaluate_golden_run
from srag_report.metrics.enums import MetricId, MetricState, UnavailableReason
from srag_report.reporting.bundle import RunManifest
from srag_report.reporting.html import render_report_html


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(tmp_path: Path) -> Path:
    request = ReportRequest(geography="BR", as_of=_AS_OF, snapshot_id="snapshot", run_id="gate-run")
    return run_report(request, _dependencies(tmp_path, request))["run_path"]


def _promote_fixture_to_live_candidate(run_path: Path) -> None:
    evidence_path = run_path / "evidence.json"
    evidence = EvidenceBundle.model_validate_json(evidence_path.read_text())
    evidence_path.write_text(evidence.model_dump_json(indent=2) + "\n")

    commentary = CommentaryResult(
        claims=deterministic_fallback(evidence),
        requested_model=DEFAULT_OPENROUTER_MODEL,
        served_model="openai/gpt-oss-20b:free",
    )
    render_report_html(
        evidence,
        commentary,
        generated_at=_GENERATED,
        output_path=run_path / "report.html",
        execution_mode="live",
    )
    manifest_path = run_path / "manifest.json"
    manifest = RunManifest.model_validate_json(manifest_path.read_text())
    hashes = dict(manifest.artifact_hashes)
    hashes["evidence.json"] = _digest(evidence_path)
    hashes["report.html"] = _digest(run_path / "report.html")
    manifest = manifest.model_copy(
        update={
            "execution_mode": "live",
            "degraded_reasons": (),
            "requested_model": commentary.requested_model,
            "served_model": commentary.served_model,
            "commentary_claims": commentary.claims,
            "fallback_used": False,
            "artifact_hashes": hashes,
        }
    )
    manifest_path.write_text(manifest.model_dump_json(indent=2) + "\n")

    def promote_audit(events: list[dict[str, object]]) -> None:
        model = next(event for event in events if event["event_type"] == "model")
        model.update(
            {
                "status": EventStatus.SUCCEEDED.value,
                "summary": (
                    f"requested_model={commentary.requested_model}; "
                    f"served_model={commentary.served_model}; fallback=False"
                ),
            }
        )
        terminal = next(
            event
            for event in events
            if event["event_type"] == "transition"
            and event["component"] == "generate_commentary"
            and event["status"] != EventStatus.STARTED.value
        )
        terminal["status"] = EventStatus.SUCCEEDED.value
        publication = next(event for event in events if event["event_type"] == "publication")
        publication["artifact_hashes"] = {"report.html": _digest(run_path / "report.html")}

    _rewrite_audit(run_path, promote_audit)


def _rewrite_manifest(run_path: Path, **updates: object) -> None:
    manifest_path = run_path / "manifest.json"
    manifest = RunManifest.model_validate_json(manifest_path.read_text())
    manifest_path.write_text(manifest.model_copy(update=updates).model_dump_json(indent=2) + "\n")


def _rewrite_audit(
    run_path: Path,
    mutate: Callable[[list[dict[str, object]]], None],
) -> None:
    audit_path = run_path / "audit.jsonl"
    events = [json.loads(line) for line in audit_path.read_text().splitlines()]
    mutate(events)
    audit_path.write_text("\n".join(json.dumps(event) for event in events) + "\n")
    manifest_path = run_path / "manifest.json"
    manifest = RunManifest.model_validate_json(manifest_path.read_text())
    hashes = dict(manifest.artifact_hashes)
    hashes["audit.jsonl"] = _digest(audit_path)
    manifest_path.write_text(
        manifest.model_copy(update={"artifact_hashes": hashes}).model_dump_json(indent=2) + "\n"
    )


def test_strict_gate_accepts_complete_live_run_with_scoped_influenza(
    tmp_path: Path,
) -> None:
    run_path = _run(tmp_path)
    _promote_fixture_to_live_candidate(run_path)
    evidence = EvidenceBundle.model_validate_json((run_path / "evidence.json").read_text())
    influenza = next(
        metric for metric in evidence.metrics if metric.metric_id is MetricId.INFLUENZA_COVERAGE
    )

    result = evaluate_golden_run(run_path)

    assert influenza.population_scope == frozenset({"CO", "NE", "S", "SE"})
    assert result.eligible
    assert result.failures == ()


def test_deterministic_degraded_scoped_run_is_not_golden(tmp_path: Path) -> None:
    result = evaluate_golden_run(_run(tmp_path))

    assert not result.eligible
    assert "not_live" in result.failures
    assert "degraded_or_fallback" in result.failures


@pytest.mark.parametrize(
    ("state", "value"),
    (
        (MetricState.AVAILABLE, None),
        (MetricState.STABLE_ZERO, 0.0),
    ),
)
def test_gate_requires_scope_for_value_bearing_influenza(
    tmp_path: Path,
    state: MetricState,
    value: float | None,
) -> None:
    run_path = _run(tmp_path)
    _promote_fixture_to_live_candidate(run_path)
    evidence_path = run_path / "evidence.json"
    evidence = EvidenceBundle.model_validate_json(evidence_path.read_text())
    metrics = tuple(
        metric.model_copy(
            update={
                "population_scope": None,
                "state": state,
                **({"value": value} if value is not None else {}),
            }
        )
        if metric.metric_id is MetricId.INFLUENZA_COVERAGE
        else metric
        for metric in evidence.metrics
    )
    updated_evidence = evidence.model_copy(update={"metrics": metrics})
    evidence_path.write_text(updated_evidence.model_dump_json() + "\n")
    manifest = RunManifest.model_validate_json((run_path / "manifest.json").read_text())
    _rewrite_manifest(
        run_path,
        artifact_hashes={**manifest.artifact_hashes, "evidence.json": _digest(evidence_path)},
        commentary_claims=deterministic_fallback(updated_evidence),
    )

    assert evaluate_golden_run(run_path).failures == ("influenza_scope_missing",)


def test_gate_does_not_require_scope_for_non_value_bearing_influenza(
    tmp_path: Path,
) -> None:
    run_path = _run(tmp_path)
    _promote_fixture_to_live_candidate(run_path)
    evidence_path = run_path / "evidence.json"
    evidence = EvidenceBundle.model_validate_json(evidence_path.read_text())
    unscoped_metrics = tuple(
        metric.model_copy(update={"population_scope": None})
        if metric.metric_id is MetricId.INFLUENZA_COVERAGE
        else metric
        for metric in evidence.metrics
    )

    for state, reason in (
        (MetricState.NEW_ACTIVITY, None),
        (MetricState.UNAVAILABLE, UnavailableReason.NOT_PUBLISHED_BY_CUTOFF),
    ):
        metrics = tuple(
            metric.model_copy(
                update={
                    "state": state,
                    "value": None,
                    "reason": reason,
                }
            )
            if metric.metric_id is MetricId.INFLUENZA_COVERAGE
            else metric
            for metric in unscoped_metrics
        )
        evidence_path.write_text(
            evidence.model_copy(update={"metrics": metrics}).model_dump_json() + "\n"
        )
        manifest = RunManifest.model_validate_json((run_path / "manifest.json").read_text())
        _rewrite_manifest(
            run_path,
            artifact_hashes={**manifest.artifact_hashes, "evidence.json": _digest(evidence_path)},
        )

        assert "influenza_scope_missing" not in evaluate_golden_run(run_path).failures


def test_gate_rejects_blank_and_padded_fallback_model_identities(tmp_path: Path) -> None:
    run_path = _run(tmp_path)
    _promote_fixture_to_live_candidate(run_path)

    _rewrite_manifest(run_path, requested_model="", served_model="   ")
    assert "unapproved_or_unserved_model" in evaluate_golden_run(run_path).failures

    _rewrite_manifest(run_path, requested_model="unapproved-model", served_model="served-model")
    assert "unapproved_or_unserved_model" in evaluate_golden_run(run_path).failures

    _rewrite_manifest(run_path, requested_model=DEFAULT_OPENROUTER_MODEL, served_model=" Fallback ")
    assert "unapproved_or_unserved_model" in evaluate_golden_run(run_path).failures


def test_gate_rejects_fallback_and_degradation_even_when_model_is_approved(tmp_path: Path) -> None:
    run_path = _run(tmp_path)
    _promote_fixture_to_live_candidate(run_path)

    _rewrite_manifest(run_path, fallback_used=True)
    assert "degraded_or_fallback" in evaluate_golden_run(run_path).failures

    _rewrite_manifest(run_path, fallback_used=False, degraded_reasons=("news_unavailable",))
    assert "degraded_or_fallback" in evaluate_golden_run(run_path).failures


def test_gate_rejects_manifest_fallback_when_audit_claims_no_fallback(tmp_path: Path) -> None:
    run_path = _run(tmp_path)
    _promote_fixture_to_live_candidate(run_path)

    def audit_claims_no_fallback(events: list[dict[str, object]]) -> None:
        model = next(event for event in events if event["event_type"] == "model")
        model["summary"] = (
            f"requested_model={DEFAULT_OPENROUTER_MODEL}; "
            "served_model=openai/gpt-oss-20b:free; fallback=False"
        )

    _rewrite_audit(run_path, audit_claims_no_fallback)
    _rewrite_manifest(run_path, fallback_used=True)

    result = evaluate_golden_run(run_path)

    assert not result.eligible
    assert "degraded_or_fallback" in result.failures
    assert "model_event_absent" in result.failures


def test_strict_gate_rejects_scoped_non_influenza_evidence(tmp_path: Path) -> None:
    run_path = _run(tmp_path)
    _promote_fixture_to_live_candidate(run_path)
    evidence_path = run_path / "evidence.json"
    evidence = EvidenceBundle.model_validate_json(evidence_path.read_text())
    metrics = tuple(
        metric.model_copy(update={"population_scope": frozenset({"SE"})})
        if metric.metric_id is MetricId.CASE_GROWTH
        else metric
        for metric in evidence.metrics
    )
    evidence_path.write_text(
        evidence.model_copy(update={"metrics": metrics}).model_dump_json(indent=2) + "\n"
    )
    manifest_path = run_path / "manifest.json"
    manifest = RunManifest.model_validate_json(manifest_path.read_text())
    hashes = dict(manifest.artifact_hashes)
    hashes["evidence.json"] = _digest(evidence_path)
    manifest_path.write_text(
        manifest.model_copy(update={"artifact_hashes": hashes}).model_dump_json(indent=2) + "\n"
    )

    result = evaluate_golden_run(run_path)

    assert not result.eligible
    assert result.failures == ("invalid_manifest_or_evidence",)


def test_artifact_tampering_revokes_golden_eligibility(tmp_path: Path) -> None:
    run_path = _run(tmp_path)
    _promote_fixture_to_live_candidate(run_path)
    with (run_path / "report.html").open("a") as handle:
        handle.write("tampered")

    result = evaluate_golden_run(run_path)

    assert not result.eligible
    assert "artifact_hash_invalid:report.html" in result.failures


def test_missing_final_publication_event_revokes_eligibility(tmp_path: Path) -> None:
    run_path = _run(tmp_path)
    _promote_fixture_to_live_candidate(run_path)
    audit_path = run_path / "audit.jsonl"
    audit_path.write_text("\n".join(audit_path.read_text().splitlines()[:-1]) + "\n")
    manifest_path = run_path / "manifest.json"
    manifest = RunManifest.model_validate_json(manifest_path.read_text())
    hashes = dict(manifest.artifact_hashes)
    hashes["audit.jsonl"] = _digest(audit_path)
    manifest_path.write_text(
        manifest.model_copy(update={"artifact_hashes": hashes}).model_dump_json(indent=2) + "\n"
    )

    result = evaluate_golden_run(run_path)

    assert not result.eligible
    assert "audit_node_order_invalid" in result.failures


def test_gate_rejects_typed_audit_mutations_after_hash_is_updated(tmp_path: Path) -> None:
    def mutate_run_id(events: list[dict[str, object]]) -> None:
        events[0]["run_id"] = "another-run"

    def mutate_sequence(events: list[dict[str, object]]) -> None:
        events[1]["sequence"] = 8

    def mutate_status(events: list[dict[str, object]]) -> None:
        events[1]["status"] = EventStatus.FAILED.value

    def mutate_timestamp(events: list[dict[str, object]]) -> None:
        events[1]["occurred_at"] = "2026-01-01T00:00:00Z"

    def mutate_node_order(events: list[dict[str, object]]) -> None:
        events[2]["component"] = "render_charts"

    def mutate_model(events: list[dict[str, object]]) -> None:
        model = next(event for event in events if event["event_type"] == "model")
        model["summary"] = "requested_model=wrong; served_model=wrong; fallback=False"

    def mutate_model_fallback(events: list[dict[str, object]]) -> None:
        model = next(event for event in events if event["event_type"] == "model")
        model["summary"] = (
            f"requested_model={DEFAULT_OPENROUTER_MODEL}; "
            "served_model=openai/gpt-oss-20b:free; fallback=True"
        )

    def mutate_live_news(events: list[dict[str, object]]) -> None:
        news = next(
            event
            for event in events
            if event["component"] == "search_news"
            and event["status"] == EventStatus.SUCCEEDED.value
        )
        news["status"] = EventStatus.FAILED.value

    def mutate_publication(events: list[dict[str, object]]) -> None:
        events[-1]["status"] = EventStatus.FAILED.value

    mutations = (
        (mutate_run_id, "audit_invalid"),
        (mutate_sequence, "audit_sequence_invalid"),
        (mutate_status, "audit_node_order_invalid"),
        (mutate_timestamp, "audit_invalid"),
        (mutate_node_order, "audit_node_order_invalid"),
        (mutate_model, "model_event_absent"),
        (mutate_model_fallback, "model_event_absent"),
        (mutate_live_news, "live_news_event_absent"),
        (mutate_publication, "audit_node_order_invalid"),
    )
    for mutate, expected in mutations:
        run_path = _run(tmp_path / expected / mutate.__name__)
        _promote_fixture_to_live_candidate(run_path)
        _rewrite_audit(run_path, mutate)

        result = evaluate_golden_run(run_path)

        assert expected in result.failures
