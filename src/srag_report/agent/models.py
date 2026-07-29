from __future__ import annotations

import datetime as dt
import re
from collections.abc import Mapping
from enum import StrEnum
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..metrics.models import ChartResult, MetricResult, QualityResult, SeriesResult

_SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_SHA256 = re.compile(r"[0-9a-f]{64}")


class RunStatus(StrEnum):
    RUNNING = "running"
    RESULT = "result"
    FAILURE = "failure"


class EventStatus(StrEnum):
    STARTED = "started"
    SUCCEEDED = "succeeded"
    DEGRADED = "degraded"
    FAILED = "failed"


class ReportRequest(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    geography: Literal["BR"] = "BR"
    as_of: dt.date
    snapshot_id: str
    run_id: str

    @field_validator("snapshot_id", "run_id")
    @classmethod
    def _safe_id(cls, value: str) -> str:
        if _SAFE_ID.fullmatch(value) is None:
            raise ValueError("identifier contains unsafe path characters")
        return value


class NewsItem(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    news_id: str
    title: str
    source: str
    final_url: str
    published_at: dt.datetime
    collected_at: dt.datetime

    @field_validator("news_id")
    @classmethod
    def _safe_news_id(cls, value: str) -> str:
        if _SAFE_ID.fullmatch(value) is None:
            raise ValueError("news_id contains unsafe characters")
        return value

    @field_validator("title", "source")
    @classmethod
    def _nonempty_text(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("text must be non-empty")
        return value

    @field_validator("final_url")
    @classmethod
    def _http_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("final_url must be an absolute HTTP(S) URL")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("final_url must not contain credentials")
        return value

    @field_validator("published_at", "collected_at")
    @classmethod
    def _utc_datetime(cls, value: dt.datetime) -> dt.datetime:
        if value.utcoffset() != dt.timedelta(0):
            raise ValueError("timestamps must be timezone-aware UTC")
        return value

    @model_validator(mode="after")
    def _published_before_collection(self) -> NewsItem:
        if self.published_at > self.collected_at:
            raise ValueError("published_at cannot be after collected_at")
        return self


class EvidenceBundle(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    request: ReportRequest
    metrics: tuple[MetricResult, ...]
    series: tuple[SeriesResult, ...]
    charts: tuple[ChartResult, ...]
    news: tuple[NewsItem, ...]
    sources: tuple[str, ...]
    watermarks: Mapping[str, str]
    quality: tuple[QualityResult, ...]

    @field_validator("sources")
    @classmethod
    def _nonempty_sources(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("evidence sources cannot be empty")
        return tuple(sorted(set(value)))

    @model_validator(mode="after")
    def _request_consistency(self) -> EvidenceBundle:
        if any(metric.snapshot_id != self.request.snapshot_id for metric in self.metrics):
            raise ValueError("metric snapshot_id differs from request")
        if any(series.snapshot_id != self.request.snapshot_id for series in self.series):
            raise ValueError("series snapshot_id differs from request")
        if any(metric.geography != self.request.geography for metric in self.metrics):
            raise ValueError("metric geography differs from request")
        return self

    def evidence_ids(self) -> frozenset[str]:
        return frozenset(
            [
                *(f"metric:{metric.metric_id.value}" for metric in self.metrics),
                *(f"series:{series.series_id}" for series in self.series),
                *(f"chart:{chart.chart_id}" for chart in self.charts),
                *(f"news:{item.news_id}" for item in self.news),
            ]
        )


class CommentaryClaim(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    claim_id: str
    text: str
    evidence_ids: tuple[str, ...]

    @field_validator("claim_id")
    @classmethod
    def _safe_claim_id(cls, value: str) -> str:
        if _SAFE_ID.fullmatch(value) is None:
            raise ValueError("claim_id contains unsafe characters")
        return value

    @field_validator("text")
    @classmethod
    def _nonempty_claim(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("claim text must be non-empty")
        return value

    @field_validator("evidence_ids")
    @classmethod
    def _nonempty_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("claim must cite at least one evidence ID")
        return value


class CommentaryClaims(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    claims: tuple[CommentaryClaim, ...]


class CommentaryResult(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    claims: tuple[CommentaryClaim, ...]
    requested_model: str
    served_model: str
    fallback_used: bool = False


class AuditEvent(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    run_id: str
    sequence: int = Field(ge=1)
    occurred_at: dt.datetime
    event_type: str
    component: str
    status: EventStatus
    summary: str
    evidence_ids: tuple[str, ...] = ()
    artifact_hashes: Mapping[str, str] = {}
    duration_ms: int = Field(ge=0)

    @field_validator("occurred_at")
    @classmethod
    def _utc_event(cls, value: dt.datetime) -> dt.datetime:
        if value.utcoffset() != dt.timedelta(0):
            raise ValueError("occurred_at must be timezone-aware UTC")
        return value

    @field_validator("artifact_hashes")
    @classmethod
    def _hashes(cls, value: Mapping[str, str]) -> Mapping[str, str]:
        if any(_SHA256.fullmatch(digest) is None for digest in value.values()):
            raise ValueError("artifact hashes must be lowercase SHA-256")
        return dict(sorted(value.items()))
