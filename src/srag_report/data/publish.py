from __future__ import annotations

import datetime as dt
import hashlib
import os
import re
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..domain.models import SourceContractDocument, SourceFileEntry
from ..domain.source import QualityState, SourceFamily, SourceStatus
from .normalization import FieldReasonCounts, NormalizationCounts
from .store import (
    SnapshotArtifact,
    assert_minimized_schema,
    logical_snapshot_sha256,
    open_snapshot,
    snapshot_table_counts,
)

_SHA256 = re.compile(r"[0-9a-f]{64}")
_SNAPSHOT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


class PublicationState(StrEnum):
    PUBLISHED = "published"
    REJECTED = "rejected"


class NormalizationManifest(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    family: SourceFamily
    counts: NormalizationCounts
    reasons: FieldReasonCounts
    completeness: float = Field(ge=0.0, le=1.0)
    quality_state: QualityState
    blocked: bool
    blocker_reason: str | None = None

    @model_validator(mode="after")
    def _check_blocker(self) -> NormalizationManifest:
        if self.blocked != (self.quality_state is QualityState.BLOCKED):
            raise ValueError("blocked must match quality_state=BLOCKED")
        if self.blocked != (self.blocker_reason is not None):
            raise ValueError("blocker_reason presence must match blocked")
        return self


class QualityManifest(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    snapshot_id: str
    state: QualityState
    metric_completeness: Mapping[str, float]
    structural_blockers: tuple[str, ...] = ()

    @field_validator("snapshot_id")
    @classmethod
    def _valid_snapshot_id(cls, value: str) -> str:
        if _SNAPSHOT_ID.fullmatch(value) is None:
            raise ValueError("snapshot_id contains unsafe path characters")
        return value

    @field_validator("metric_completeness")
    @classmethod
    def _valid_completeness(cls, value: Mapping[str, float]) -> Mapping[str, float]:
        if any(not 0.0 <= completeness <= 1.0 for completeness in value.values()):
            raise ValueError("metric completeness must be within [0, 1]")
        return dict(sorted(value.items()))

    @model_validator(mode="after")
    def _check_blockers(self) -> QualityManifest:
        if bool(self.structural_blockers) != (self.state is QualityState.BLOCKED):
            raise ValueError("structural blockers must exist exactly when state is BLOCKED")
        return self


class SnapshotManifest(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    snapshot_id: str
    generated_at: dt.datetime
    as_of: dt.date
    contract_version: str
    source_files: tuple[SourceFileEntry, ...]
    duckdb_content_sha256: str
    duckdb_file_sha256: str
    table_counts: Mapping[str, int]
    table_schemas: Mapping[str, tuple[str, ...]]
    normalization: tuple[NormalizationManifest, ...]
    quality_state: QualityState
    publication_state: PublicationState = PublicationState.PUBLISHED

    @field_validator("snapshot_id")
    @classmethod
    def _valid_snapshot_id(cls, value: str) -> str:
        if _SNAPSHOT_ID.fullmatch(value) is None:
            raise ValueError("snapshot_id contains unsafe path characters")
        return value

    @field_validator("generated_at")
    @classmethod
    def _utc_generated_at(cls, value: dt.datetime) -> dt.datetime:
        if value.utcoffset() != dt.timedelta(0):
            raise ValueError("generated_at must be timezone-aware UTC")
        return value

    @field_validator("duckdb_content_sha256", "duckdb_file_sha256")
    @classmethod
    def _valid_sha256(cls, value: str) -> str:
        if _SHA256.fullmatch(value) is None:
            raise ValueError("snapshot hash must be 64 lowercase hexadecimal characters")
        return value

    @field_validator("table_counts")
    @classmethod
    def _valid_counts(cls, value: Mapping[str, int]) -> Mapping[str, int]:
        if any(count < 0 for count in value.values()):
            raise ValueError("table counts cannot be negative")
        return dict(sorted(value.items()))


class PublicationFailure(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    snapshot_id: str
    failed_at: dt.datetime
    reason_code: str
    detail: str


class PublicationError(RuntimeError):
    pass


def normalization_manifest(
    family: SourceFamily,
    *,
    counts: NormalizationCounts,
    reasons: FieldReasonCounts,
    completeness: float,
    quality_state: QualityState,
    blocked: bool,
    blocker_reason: str | None,
) -> NormalizationManifest:
    return NormalizationManifest(
        family=family,
        counts=counts,
        reasons=reasons,
        completeness=completeness,
        quality_state=quality_state,
        blocked=blocked,
        blocker_reason=blocker_reason,
    )


def _file_sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _verify_source_files(sources: Sequence[SourceFileEntry]) -> None:
    for source in sources:
        if source.status is not SourceStatus.VERIFIED:
            raise PublicationError(
                f"source_not_verified:{source.family.value}:{source.identifier}:{source.status.value}"
            )
        path = Path(source.local_path)
        if not path.is_file():
            raise PublicationError(f"source_missing:{source.identifier}")
        if path.stat().st_size != source.size_bytes:
            raise PublicationError(f"source_size_mismatch:{source.identifier}")
        if _file_sha256(path) != source.sha256:
            raise PublicationError(f"source_hash_mismatch:{source.identifier}")


def _table_schemas(path: Path) -> dict[str, tuple[str, ...]]:
    with open_snapshot(path) as connection:
        rows = connection.execute(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'main'
            ORDER BY table_name, ordinal_position
            """
        ).fetchall()
    schemas: dict[str, list[str]] = {}
    for table_name, column_name in rows:
        schemas.setdefault(str(table_name), []).append(str(column_name))
    return {table: tuple(columns) for table, columns in sorted(schemas.items())}


def build_snapshot_manifest(
    *,
    snapshot_id: str,
    generated_at: dt.datetime,
    as_of: dt.date,
    contract: SourceContractDocument,
    artifact: SnapshotArtifact,
    normalization: Sequence[NormalizationManifest],
    quality: QualityManifest,
) -> SnapshotManifest:
    if snapshot_id != quality.snapshot_id:
        raise ValueError("manifest and quality snapshot IDs differ")
    if any(item.blocked for item in normalization):
        raise PublicationError("normalization_blocked")
    if quality.structural_blockers:
        raise PublicationError("quality_blocked")
    actual_counts = snapshot_table_counts(artifact.path)
    if actual_counts != dict(artifact.table_counts):
        raise PublicationError("snapshot_count_mismatch")
    if _file_sha256(artifact.path) != artifact.file_sha256:
        raise PublicationError("snapshot_hash_mismatch")
    assert_minimized_schema(artifact.path)
    return SnapshotManifest(
        snapshot_id=snapshot_id,
        generated_at=generated_at,
        as_of=as_of,
        contract_version=contract.contract_version,
        source_files=contract.sources,
        duckdb_content_sha256=artifact.content_sha256,
        duckdb_file_sha256=artifact.file_sha256,
        table_counts=actual_counts,
        table_schemas=_table_schemas(artifact.path),
        normalization=tuple(normalization),
        quality_state=quality.state,
    )


def load_published_snapshot_manifest(
    snapshot_path: Path, *, expected_snapshot_id: str
) -> SnapshotManifest:
    """Load and verify the immutable manifest adjacent to a published DuckDB snapshot."""
    manifest_path = snapshot_path.parent / "manifest.json"
    try:
        manifest = SnapshotManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PublicationError("snapshot_manifest_invalid") from exc
    if manifest.snapshot_id != expected_snapshot_id:
        raise PublicationError("snapshot_id_mismatch")
    if not snapshot_path.is_file():
        raise PublicationError("snapshot_missing")
    if _file_sha256(snapshot_path) != manifest.duckdb_file_sha256:
        raise PublicationError("snapshot_hash_mismatch")
    if logical_snapshot_sha256(snapshot_path) != manifest.duckdb_content_sha256:
        raise PublicationError("snapshot_content_hash_mismatch")
    if snapshot_table_counts(snapshot_path) != dict(manifest.table_counts):
        raise PublicationError("snapshot_count_mismatch")
    if _table_schemas(snapshot_path) != dict(manifest.table_schemas):
        raise PublicationError("snapshot_schema_mismatch")
    assert_minimized_schema(snapshot_path)
    return manifest


def _write_json(path: Path, model: BaseModel) -> None:
    path.write_text(model.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _record_failure(
    root: Path,
    *,
    snapshot_id: str,
    failed_at: dt.datetime,
    reason_code: str,
    detail: str,
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    failure = PublicationFailure(
        snapshot_id=snapshot_id,
        failed_at=failed_at,
        reason_code=reason_code,
        detail=detail,
    )
    descriptor, temporary_name = tempfile.mkstemp(prefix=".last-failure.", dir=root)
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        _write_json(temporary_path, failure)
        os.replace(temporary_path, root / "last-failure.json")
    finally:
        temporary_path.unlink(missing_ok=True)


def _select_snapshot(root: Path, snapshot_id: str) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=".CURRENT.", dir=root)
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        temporary_path.write_text(snapshot_id + "\n", encoding="utf-8")
        os.replace(temporary_path, root / "CURRENT")
    finally:
        temporary_path.unlink(missing_ok=True)


def publish_snapshot(
    root: Path,
    *,
    snapshot_id: str,
    artifact: SnapshotArtifact,
    contract: SourceContractDocument,
    normalization: Sequence[NormalizationManifest],
    quality: QualityManifest,
    generated_at: dt.datetime,
    as_of: dt.date,
) -> Path:
    """Validate, stage, and atomically select an immutable snapshot directory."""
    final_path = root / snapshot_id
    candidate = root / f".{snapshot_id}.candidate"
    try:
        if final_path.exists():
            raise PublicationError("snapshot_already_exists")
        _verify_source_files(contract.sources)
        manifest = build_snapshot_manifest(
            snapshot_id=snapshot_id,
            generated_at=generated_at,
            as_of=as_of,
            contract=contract,
            artifact=artifact,
            normalization=normalization,
            quality=quality,
        )
        candidate.mkdir(parents=True, exist_ok=False)
        shutil.copyfile(artifact.path, candidate / "analytics.duckdb")
        if _file_sha256(candidate / "analytics.duckdb") != artifact.file_sha256:
            raise PublicationError("staged_snapshot_hash_mismatch")
        _write_json(candidate / "manifest.json", manifest)
        _write_json(candidate / "quality.json", quality)
        os.replace(candidate, final_path)
        _select_snapshot(root, snapshot_id)
        return final_path
    except Exception as exc:
        shutil.rmtree(candidate, ignore_errors=True)
        reason_code = str(exc).split(":", 1)[0] or type(exc).__name__
        _record_failure(
            root,
            snapshot_id=snapshot_id,
            failed_at=generated_at,
            reason_code=reason_code,
            detail=str(exc),
        )
        if isinstance(exc, PublicationError):
            raise
        raise PublicationError(str(exc)) from exc
