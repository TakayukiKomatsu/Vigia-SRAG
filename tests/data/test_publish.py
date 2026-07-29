from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

import pytest

from srag_report.data.normalization import FieldReasonCounts, NormalizationCounts
from srag_report.data.publish import (
    NormalizationManifest,
    PublicationError,
    QualityManifest,
    build_snapshot_manifest,
    load_published_snapshot_manifest,
    normalization_manifest,
    publish_snapshot,
)
from srag_report.data.store import SnapshotArtifact, materialize_snapshot
from srag_report.domain.models import (
    CnesCanonicalRow,
    IbgePopulationRow,
    SourceContractDocument,
    SourceFileEntry,
)
from srag_report.domain.source import CNES_ICU_ALLOWLIST, QualityState, SourceFamily, SourceStatus

_SHA = "0" * 64
_GENERATED = dt.datetime(2026, 7, 28, 12, tzinfo=dt.UTC)


def _artifact(tmp_path: Path) -> SnapshotArtifact:
    return materialize_snapshot(
        tmp_path / "candidate.duckdb",
        sivep_rows=[],
        cnes_rows=[
            CnesCanonicalRow(
                competencia=202606,
                uf="SP",
                cod_leito=61,
                qt_exist=10,
                source_sha256=_SHA,
            )
        ],
        ibge_rows=[
            IbgePopulationRow(
                year=2025,
                geography="BR",
                population_official=213_421_037,
                reference_date=dt.date(2025, 7, 1),
                source_sha256=_SHA,
            )
        ],
    )


def _source(path: Path, status: SourceStatus = SourceStatus.VERIFIED) -> SourceFileEntry:
    payload = path.read_bytes()
    return SourceFileEntry(
        family=SourceFamily.SIVEP,
        identifier="synthetic-source",
        sha256=hashlib.sha256(payload).hexdigest(),
        local_path=str(path),
        size_bytes=len(payload),
        data_rows=2,
        retrieval_at=_GENERATED,
        watermark="2026-07-26",
        status=status,
        year=2026,
    )


def _contract(source: SourceFileEntry) -> SourceContractDocument:
    return SourceContractDocument(
        schema_version="1.0",
        contract_version="synthetic-1",
        contract_date=dt.date(2026, 7, 28),
        cnes_competencia=202606,
        cnes_icu_allowlist=tuple(sorted(CNES_ICU_ALLOWLIST)),
        sources=(source,),
    )


def _normalization() -> NormalizationManifest:
    return normalization_manifest(
        SourceFamily.SIVEP,
        counts=NormalizationCounts(total_input=2, accepted=2),
        reasons=FieldReasonCounts(),
        completeness=1.0,
        quality_state=QualityState.AVAILABLE,
        blocked=False,
        blocker_reason=None,
    )


def _quality(snapshot_id: str) -> QualityManifest:
    return QualityManifest(
        snapshot_id=snapshot_id,
        state=QualityState.AVAILABLE,
        metric_completeness={"case_growth": 1.0, "mortality_per_100k": 1.0},
    )


def test_publish_writes_complete_snapshot_then_selects_it(tmp_path: Path) -> None:
    raw = tmp_path / "source.csv"
    raw.write_text("synthetic\n", encoding="utf-8")
    artifact = _artifact(tmp_path)
    root = tmp_path / "snapshots"
    published = publish_snapshot(
        root,
        snapshot_id="snapshot-20260726",
        artifact=artifact,
        contract=_contract(_source(raw)),
        normalization=[_normalization()],
        quality=_quality("snapshot-20260726"),
        generated_at=_GENERATED,
        as_of=dt.date(2026, 7, 26),
    )
    assert (published / "analytics.duckdb").is_file()
    assert (published / "manifest.json").is_file()
    assert (published / "quality.json").is_file()
    assert (root / "CURRENT").read_text() == "snapshot-20260726\n"
    manifest = json.loads((published / "manifest.json").read_text())
    assert manifest["publication_state"] == "published"
    assert manifest["source_files"][0]["identifier"] == "synthetic-source"
    loaded = load_published_snapshot_manifest(
        published / "analytics.duckdb", expected_snapshot_id="snapshot-20260726"
    )
    assert loaded.as_of == dt.date(2026, 7, 26)
    snapshot = published / "analytics.duckdb"
    snapshot.write_bytes(snapshot.read_bytes() + b"tampered")
    with pytest.raises(PublicationError, match="snapshot_hash_mismatch"):
        load_published_snapshot_manifest(snapshot, expected_snapshot_id="snapshot-20260726")


def test_manifest_build_is_deterministic(tmp_path: Path) -> None:
    raw = tmp_path / "source.csv"
    raw.write_text("synthetic\n", encoding="utf-8")
    artifact = _artifact(tmp_path)
    arguments = {
        "snapshot_id": "snapshot-repeat",
        "generated_at": _GENERATED,
        "as_of": dt.date(2026, 7, 26),
        "contract": _contract(_source(raw)),
        "artifact": artifact,
        "normalization": [_normalization()],
        "quality": _quality("snapshot-repeat"),
    }
    assert (
        build_snapshot_manifest(**arguments).model_dump_json()
        == build_snapshot_manifest(**arguments).model_dump_json()
    )


def test_failed_candidate_preserves_current_snapshot(tmp_path: Path) -> None:
    raw = tmp_path / "source.csv"
    raw.write_text("synthetic\n", encoding="utf-8")
    artifact = _artifact(tmp_path)
    root = tmp_path / "snapshots"
    publish_snapshot(
        root,
        snapshot_id="good",
        artifact=artifact,
        contract=_contract(_source(raw)),
        normalization=[_normalization()],
        quality=_quality("good"),
        generated_at=_GENERATED,
        as_of=dt.date(2026, 7, 26),
    )
    raw.write_text("changed\n", encoding="utf-8")
    with pytest.raises(PublicationError, match="source_size_mismatch|source_hash_mismatch"):
        publish_snapshot(
            root,
            snapshot_id="bad",
            artifact=artifact,
            contract=_contract(
                SourceFileEntry(
                    **{
                        **_source(raw).model_dump(),
                        "sha256": "f" * 64,
                    }
                )
            ),
            normalization=[_normalization()],
            quality=_quality("bad"),
            generated_at=_GENERATED,
            as_of=dt.date(2026, 7, 26),
        )
    assert (root / "CURRENT").read_text() == "good\n"
    assert not (root / "bad").exists()
    failure = json.loads((root / "last-failure.json").read_text())
    assert failure["snapshot_id"] == "bad"


def test_unverified_source_never_publishes(tmp_path: Path) -> None:
    raw = tmp_path / "source.csv"
    raw.write_text("synthetic\n", encoding="utf-8")
    with pytest.raises(PublicationError, match="source_not_verified"):
        publish_snapshot(
            tmp_path / "snapshots",
            snapshot_id="blocked",
            artifact=_artifact(tmp_path),
            contract=_contract(_source(raw, SourceStatus.PARTIAL)),
            normalization=[_normalization()],
            quality=_quality("blocked"),
            generated_at=_GENERATED,
            as_of=dt.date(2026, 7, 26),
        )
