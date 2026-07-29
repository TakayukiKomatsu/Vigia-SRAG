from __future__ import annotations

import re
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..domain.source import QualityState

_SHA256_RE = re.compile(r"[0-9a-f]{64}")


class NormalizationCounts(BaseModel):
    """Mutually exclusive row outcomes for one source normalization pass."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    total_input: int = Field(ge=0)
    accepted: int = Field(ge=0)
    quarantined: int = Field(default=0, ge=0)
    deduplicated: int = Field(default=0, ge=0)
    filtered: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _outcomes_match_total(self) -> Self:
        outcomes = self.accepted + self.quarantined + self.deduplicated + self.filtered
        if outcomes != self.total_input:
            raise ValueError(
                "total_input must equal accepted + quarantined + deduplicated + filtered"
            )
        return self


class FieldReasonCounts(BaseModel):
    """Aggregate issue counts; never contains source rows or source values."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    by_reason: dict[str, int] = Field(default_factory=dict)
    by_field: dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _counts_are_nonnegative(self) -> Self:
        for collection_name, values in (
            ("by_reason", self.by_reason),
            ("by_field", self.by_field),
        ):
            invalid = {key: value for key, value in values.items() if value < 0}
            if invalid:
                raise ValueError(f"{collection_name} contains negative counts: {invalid}")
        return self


class _NormalizationResult(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    counts: NormalizationCounts
    reasons: FieldReasonCounts = Field(default_factory=FieldReasonCounts)
    completeness: float = Field(ge=0.0, le=1.0)
    quality_state: QualityState
    blocked: bool = False
    blocker_reason: str | None = None
    output_sha256: str | None = None
    output_path: str | None = None

    @model_validator(mode="after")
    def _state_is_consistent(self) -> Self:
        if self.blocked:
            if self.quality_state is not QualityState.BLOCKED:
                raise ValueError("blocked result requires quality_state=blocked")
            if self.blocker_reason is None or not self.blocker_reason.strip():
                raise ValueError("blocked result requires a non-empty blocker_reason")
        elif self.quality_state is QualityState.BLOCKED:
            raise ValueError("quality_state=blocked requires blocked=True")
        elif self.blocker_reason is not None:
            raise ValueError("non-blocked result cannot carry blocker_reason")

        if (self.output_sha256 is None) != (self.output_path is None):
            raise ValueError("output_sha256 and output_path must be present together")
        if self.output_sha256 is not None and _SHA256_RE.fullmatch(self.output_sha256) is None:
            raise ValueError("output_sha256 must be 64 lowercase hexadecimal characters")
        return self


class SivepNormalizationResult(_NormalizationResult):
    """Aggregate result of a SIVEP normalization pass."""


class CnesNormalizationResult(_NormalizationResult):
    """Aggregate result of a CNES normalization pass."""


class IbgeNormalizationResult(_NormalizationResult):
    """Aggregate result of an IBGE normalization pass."""


class PniNormalizationResult(_NormalizationResult):
    """Aggregate result of a PNI normalization pass."""

    eligible: bool
