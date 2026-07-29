from __future__ import annotations

import datetime as dt
import os
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from ..agent.models import AuditEvent, EventStatus


class AuditWriteError(RuntimeError):
    pass


class AuditSink:
    """Synchronous append-only JSONL sink; every event is flushed and fsynced."""

    def __init__(
        self,
        path: Path,
        *,
        run_id: str,
        clock: Callable[[], dt.datetime] | None = None,
    ) -> None:
        self.path = path
        self.run_id = run_id
        self._clock = clock or (lambda: dt.datetime.now(dt.UTC))
        self._sequence = 0
        path.parent.mkdir(parents=True, exist_ok=True)

    def emit(
        self,
        *,
        event_type: str,
        component: str,
        status: EventStatus,
        summary: str,
        evidence_ids: Sequence[str] = (),
        artifact_hashes: Mapping[str, str] | None = None,
        duration_ms: int = 0,
    ) -> AuditEvent:
        if "api_key" in summary.casefold() or "authorization:" in summary.casefold():
            raise AuditWriteError("audit summary contains prohibited secret-like text")
        self._sequence += 1
        event = AuditEvent(
            run_id=self.run_id,
            sequence=self._sequence,
            occurred_at=self._clock(),
            event_type=event_type,
            component=component,
            status=status,
            summary=summary,
            evidence_ids=tuple(evidence_ids),
            artifact_hashes=artifact_hashes or {},
            duration_ms=duration_ms,
        )
        payload = (event.model_dump_json() + "\n").encode()
        try:
            descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            with os.fdopen(descriptor, "ab") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            self._sequence -= 1
            raise AuditWriteError(f"failed to persist critical audit event: {exc}") from exc
        return event
