from __future__ import annotations

import argparse
import datetime as dt
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal

import httpx

from .agent.commentary import FakeCommentaryAdapter, OpenAICommentaryAdapter
from .agent.graph import GraphDependencies, NewsTool, run_report
from .agent.models import NewsItem, ReportRequest
from .audit.sink import AuditSink
from .data.publish import SnapshotManifest, load_published_snapshot_manifest
from .demo import build_demo_snapshot
from .domain.source import SourceFamily
from .governance import evaluate_golden_run
from .reporting.bundle import RunWorkspace
from .tools.analytics import ChartsTool, MetricsTool
from .tools.news import GoogleNewsRssTool

_SOURCES = ("SIVEP-Gripe", "CNES", "IBGE", "PNI")
_SOURCE_LABELS = {
    SourceFamily.SIVEP: "SIVEP-Gripe",
    SourceFamily.CNES: "CNES",
    SourceFamily.IBGE: "IBGE",
    SourceFamily.PNI: "PNI",
}


def _source_watermarks(manifest: SnapshotManifest) -> dict[str, str]:
    watermarks: dict[str, str] = {}
    for source in manifest.source_files:
        label = _SOURCE_LABELS[source.family]
        watermarks[label] = max(watermarks.get(label, source.watermark), source.watermark)
    return watermarks


class StaticDemoNewsTool:
    def collect(self, *, generated_at: dt.datetime) -> tuple[NewsItem, ...]:
        return (
            NewsItem(
                news_id="demo-news",
                title="Boletim sintético de SRAG para demonstração não-live",
                source="Agência Brasil",
                final_url="https://agenciabrasil.ebc.com.br/saude/noticia/demo",
                published_at=generated_at - dt.timedelta(days=1),
                collected_at=generated_at,
            ),
        )


def _date(value: str) -> dt.date:
    return dt.date.fromisoformat(value)


def _execute(
    *,
    request: ReportRequest,
    snapshot: Path,
    output_root: Path,
    generated_at: dt.datetime,
    snapshot_watermark: dt.date,
    watermarks: Mapping[str, str],
    news: NewsTool,
    commentary: FakeCommentaryAdapter | OpenAICommentaryAdapter,
    execution_mode: Literal["deterministic", "live"],
) -> Path:
    workspace = RunWorkspace(output_root, request)
    dependencies = GraphDependencies(
        metrics=MetricsTool(snapshot, watermark=snapshot_watermark),
        charts=ChartsTool(),
        news=news,
        commentary=commentary,
        workspace=workspace,
        audit=AuditSink(workspace.audit_path, run_id=request.run_id, clock=lambda: generated_at),
        generated_at=generated_at,
        sources=_SOURCES,
        watermarks=watermarks,
        execution_mode=execution_mode,
    )
    try:
        return run_report(request, dependencies)["run_path"]
    except BaseException:
        workspace.discard()
        raise


def _run_demo(args: argparse.Namespace) -> int:
    as_of = _date(args.as_of)
    snapshot = build_demo_snapshot(Path(args.snapshot), as_of=as_of)
    request = ReportRequest(
        geography="BR",
        as_of=as_of,
        snapshot_id="synthetic-demo",
        run_id=args.run_id,
    )
    run_path = _execute(
        request=request,
        generated_at=dt.datetime.combine(as_of, dt.time(12), tzinfo=dt.UTC),
        snapshot=snapshot,
        snapshot_watermark=as_of,
        watermarks={source: as_of.isoformat() for source in _SOURCES},
        output_root=Path(args.output_root),
        news=StaticDemoNewsTool(),
        commentary=FakeCommentaryAdapter([], error=RuntimeError("deterministic fallback")),
        execution_mode="deterministic",
    )
    print(run_path)
    return 0


def _run_live(args: argparse.Namespace) -> int:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required for live mode")
    as_of = _date(args.as_of)
    snapshot = Path(args.snapshot)
    manifest = load_published_snapshot_manifest(snapshot, expected_snapshot_id=args.snapshot_id)
    request = ReportRequest(
        geography="BR",
        as_of=as_of,
        snapshot_id=args.snapshot_id,
        run_id=args.run_id,
    )
    with httpx.Client(
        timeout=httpx.Timeout(15.0), follow_redirects=True, max_redirects=5
    ) as client:
        run_path = _execute(
            request=request,
            snapshot=snapshot,
            output_root=Path(args.output_root),
            snapshot_watermark=manifest.as_of,
            watermarks=_source_watermarks(manifest),
            generated_at=dt.datetime.now(dt.UTC),
            news=GoogleNewsRssTool(client),
            commentary=OpenAICommentaryAdapter(api_key=api_key),
            execution_mode="live",
        )
    print(run_path)
    return 0


def _run_gate(args: argparse.Namespace) -> int:
    result = evaluate_golden_run(Path(args.run_path))
    print(result.model_dump_json(indent=2))
    return 0 if result.eligible else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="srag-report")
    commands = parser.add_subparsers(dest="command", required=True)

    demo = commands.add_parser("demo", help="run the deterministic network-free demo")
    demo.add_argument("--as-of", default="2026-07-28")
    demo.add_argument("--run-id", default="demo-20260728")
    demo.add_argument("--snapshot", default="data/snapshots/demo.duckdb")
    demo.add_argument("--output-root", default="runs")
    demo.set_defaults(handler=_run_demo)

    live = commands.add_parser("live", help="run against a fixed snapshot and live services")
    live.add_argument("--snapshot", required=True)
    live.add_argument("--snapshot-id", required=True)
    live.add_argument("--as-of", required=True)
    live.add_argument("--run-id", required=True)
    live.add_argument("--output-root", default="runs")
    live.set_defaults(handler=_run_live)

    gate = commands.add_parser("gate", help="evaluate strict golden eligibility")
    gate.add_argument("run_path")
    gate.set_defaults(handler=_run_gate)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.handler(args))
