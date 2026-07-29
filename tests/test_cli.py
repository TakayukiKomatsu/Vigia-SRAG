from __future__ import annotations

import datetime as dt
import os
import subprocess
import sys
from pathlib import Path

import pytest

from data.test_publish import _artifact, _contract, _normalization, _quality, _source
from srag_report.cli import main
from srag_report.data.publish import publish_snapshot
from srag_report.metrics.time import WatermarkError


def test_demo_quickstart_is_network_free_and_labeled_non_live(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(
        [
            "demo",
            "--snapshot",
            str(tmp_path / "demo.duckdb"),
            "--output-root",
            str(tmp_path / "runs"),
            "--run-id",
            "quickstart",
        ]
    )

    assert exit_code == 0
    run_path = tmp_path / "runs" / "quickstart"
    assert str(run_path) in capsys.readouterr().out
    report = (run_path / "report.html").read_text()
    assert "demonstração não-live" in report
    assert "Modo: deterministic" in report


def test_demo_run_bundle_is_byte_deterministic_across_processes(tmp_path: Path) -> None:
    for suffix, hash_seed in (("left", "1"), ("right", "2")):
        subprocess.run(
            [
                sys.executable,
                "-m",
                "srag_report",
                "demo",
                "--snapshot",
                str(tmp_path / f"{suffix}.duckdb"),
                "--output-root",
                str(tmp_path / suffix),
                "--run-id",
                "same-run",
            ],
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONHASHSEED": hash_seed},
        )

    left = tmp_path / "left" / "same-run"
    right = tmp_path / "right" / "same-run"
    left_files = sorted(path.relative_to(left) for path in left.rglob("*") if path.is_file())
    right_files = sorted(path.relative_to(right) for path in right.rglob("*") if path.is_file())
    assert left_files == right_files
    assert all((left / path).read_bytes() == (right / path).read_bytes() for path in left_files)


def test_live_mode_requires_only_declared_openai_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(SystemExit, match="OPENAI_API_KEY is required"):
        main(
            [
                "live",
                "--snapshot",
                "fixed.duckdb",
                "--snapshot-id",
                "fixed",
                "--as-of",
                "2026-07-28",
                "--run-id",
                "live-run",
            ]
        )


def test_live_rejects_as_of_after_published_snapshot_watermark(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = tmp_path / "source.csv"
    raw.write_text("synthetic\n", encoding="utf-8")
    published = publish_snapshot(
        tmp_path / "snapshots",
        snapshot_id="published-snapshot",
        artifact=_artifact(tmp_path),
        contract=_contract(_source(raw)),
        normalization=[_normalization()],
        quality=_quality("published-snapshot"),
        generated_at=dt.datetime(2026, 7, 28, 12, tzinfo=dt.UTC),
        as_of=dt.date(2026, 7, 26),
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-key")

    with pytest.raises(WatermarkError):
        main(
            [
                "live",
                "--snapshot",
                str(published / "analytics.duckdb"),
                "--snapshot-id",
                "published-snapshot",
                "--as-of",
                "2026-07-28",
                "--run-id",
                "future-request",
                "--output-root",
                str(tmp_path / "runs"),
            ]
        )

    assert not (tmp_path / "runs" / "future-request").exists()
