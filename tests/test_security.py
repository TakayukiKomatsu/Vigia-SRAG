from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest
from test_evidence import _evidence

from srag_report.agent.models import CommentaryClaim, CommentaryResult, EventStatus, NewsItem
from srag_report.audit.sink import AuditSink, AuditWriteError
from srag_report.reporting.html import render_report_html
from srag_report.tools.analytics import MetricsTool

_GENERATED = dt.datetime(2026, 7, 28, 12, tzinfo=dt.UTC)


def test_evidence_bundle_excludes_record_level_and_secret_fields(tmp_path: Path) -> None:
    payload = _evidence(tmp_path).model_dump_json().casefold()

    for prohibited in (
        "notification_key",
        "nu_notific",
        "dt_sin_pri",
        "authorization:",
        "openai_api_key",
        "api_key",
    ):
        assert prohibited not in payload


def test_analytical_tool_exposes_no_arbitrary_sql_interface() -> None:
    assert not hasattr(MetricsTool, "query")
    assert not hasattr(MetricsTool, "execute")


def test_untrusted_news_and_commentary_are_html_escaped(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    malicious_news = NewsItem(
        news_id="malicious",
        title='<script>alert("news")</script>',
        source="Agência Brasil",
        final_url="https://agenciabrasil.ebc.com.br/saude/noticia",
        published_at=_GENERATED - dt.timedelta(days=1),
        collected_at=_GENERATED,
    )
    evidence = evidence.model_copy(update={"news": (malicious_news,)})
    commentary = CommentaryResult(
        claims=(
            CommentaryClaim(
                claim_id="escaped",
                text='Taxa de aumento: 50 por cento; <img src=x onerror="alert(1)">.',
                evidence_ids=("metric:case_growth",),
            ),
        ),
        requested_model="fake",
        served_model="fake",
    )
    report_path = tmp_path / "report.html"

    render_report_html(
        evidence,
        commentary,
        generated_at=_GENERATED,
        output_path=report_path,
        execution_mode="deterministic",
    )

    report = report_path.read_text()
    assert "<script>" not in report
    assert "<img src=x" not in report
    assert "&lt;script&gt;" in report
    assert "&lt;img src=x" in report


def test_audit_rejects_secret_like_summary(tmp_path: Path) -> None:
    sink = AuditSink(tmp_path / "audit.jsonl", run_id="secret-test")

    with pytest.raises(AuditWriteError, match="prohibited secret-like text"):
        sink.emit(
            event_type="failure",
            component="test",
            status=EventStatus.FAILED,
            summary="api_key leaked",
        )

    assert not (tmp_path / "audit.jsonl").exists()
