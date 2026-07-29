from __future__ import annotations

import hashlib
from pathlib import Path

from test_graph import _AS_OF, _GENERATED, _dependencies

from srag_report.agent.commentary import DEFAULT_OPENROUTER_MODEL
from srag_report.agent.evidence import deterministic_fallback
from srag_report.agent.graph import run_report
from srag_report.agent.models import CommentaryResult, EvidenceBundle, ReportRequest
from srag_report.governance import evaluate_golden_run
from srag_report.metrics.enums import MetricId
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


def test_missing_critical_publication_event_revokes_eligibility(tmp_path: Path) -> None:
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
    assert "critical_publication_event_absent" in result.failures
