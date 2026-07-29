from __future__ import annotations

import datetime as dt
import hashlib
import os
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from ..agent.models import (
    CommentaryClaim,
    CommentaryResult,
    EvidenceBundle,
    ReportRequest,
    RunStatus,
)


class RunManifest(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    run_id: str
    snapshot_id: str
    generated_at: dt.datetime
    as_of: dt.date
    status: RunStatus
    degraded_reasons: tuple[str, ...]
    requested_model: str
    served_model: str
    execution_mode: Literal["deterministic", "live"]
    commentary_claims: tuple[CommentaryClaim, ...]
    fallback_used: bool
    artifact_hashes: Mapping[str, str]

    @field_validator("generated_at")
    @classmethod
    def _utc_generated_at(cls, value: dt.datetime) -> dt.datetime:
        if value.utcoffset() != dt.timedelta(0):
            raise ValueError("generated_at must be timezone-aware UTC")
        return value


class RunWorkspace:
    """Stage a complete run outside the published path, then rename atomically."""

    def __init__(self, root: Path, request: ReportRequest) -> None:
        self.root = root
        self.request = request
        self.candidate = root / f".{request.run_id}.candidate"
        self.final = root / request.run_id
        if self.final.exists() or self.candidate.exists():
            raise FileExistsError(f"run already exists: {request.run_id}")
        self.candidate.mkdir(parents=True)
        self.charts_dir.mkdir()
        self.write_json("request.json", request)

    @property
    def charts_dir(self) -> Path:
        return self.candidate / "charts"

    @property
    def audit_path(self) -> Path:
        return self.candidate / "audit.jsonl"

    @property
    def report_path(self) -> Path:
        return self.candidate / "report.html"

    def write_json(self, relative_path: str, model: BaseModel) -> None:
        path = self.candidate / relative_path
        payload = (model.model_dump_json(indent=2) + "\n").encode()
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        os.close(descriptor)
        temporary_path = Path(temporary_name)
        try:
            temporary_path.write_bytes(payload)
            os.replace(temporary_path, path)
        finally:
            temporary_path.unlink(missing_ok=True)

    def write_evidence(self, evidence: EvidenceBundle) -> None:
        self.write_json("evidence.json", evidence)

    def _artifact_hashes(self) -> dict[str, str]:
        required = [
            self.candidate / "request.json",
            self.candidate / "evidence.json",
            self.candidate / "audit.jsonl",
            self.candidate / "report.html",
        ]
        required.extend(sorted(self.charts_dir.glob("*.svg")))
        missing = [path.name for path in required[:4] if not path.is_file()]
        if missing:
            raise RuntimeError(f"run bundle incomplete: missing={missing}")
        return {
            str(path.relative_to(self.candidate)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in required
        }

    def finalize(
        self,
        *,
        generated_at: dt.datetime,
        commentary: CommentaryResult,
        degraded_reasons: Sequence[str],
        execution_mode: Literal["deterministic", "live"],
    ) -> Path:
        hashes = self._artifact_hashes()
        manifest = RunManifest(
            run_id=self.request.run_id,
            snapshot_id=self.request.snapshot_id,
            generated_at=generated_at,
            as_of=self.request.as_of,
            status=RunStatus.RESULT,
            degraded_reasons=tuple(degraded_reasons),
            requested_model=commentary.requested_model,
            served_model=commentary.served_model,
            execution_mode=execution_mode,
            commentary_claims=commentary.claims,
            fallback_used=commentary.fallback_used,
            artifact_hashes=hashes,
        )
        self.write_json("manifest.json", manifest)
        os.replace(self.candidate, self.final)
        return self.final

    def discard(self) -> None:
        shutil.rmtree(self.candidate, ignore_errors=True)
