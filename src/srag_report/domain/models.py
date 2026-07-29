"""
Strict, frozen Pydantic domain models for canonical SIVEP, CNES, IBGE, and PNI rows.

Shared validators (fail-closed):
- sha256 / source_sha256: exactly 64 lowercase hex characters.
- loaded_at / retrieval_at / published_at: timezone-aware UTC (utcoffset == timedelta(0)).
- size_bytes / data_rows*: non-negative (ge=0).

SivepCanonicalRow: NO update timestamp field. DT_DIGITA is insertion-only.
When evolution == DEATH_OTHER (3): evolution_date MUST be None.
UNKNOWN (9) is distinct from NO (2) — never conflated.
CnesCanonicalRow: competencia locked 202606; cod_leito in CNES_ICU_ALLOWLIST.
IbgePopulationRow: reference_date must be 2025-07-01.
PniObservation: population_scope ⊆ {NE,CO,S,SE}; never nationwide; never golden.
"""

from __future__ import annotations

import datetime
import re
from decimal import Decimal
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from .source import (
    CNES_COMPETENCIA,
    CNES_ICU_ALLOWLIST,
    IBGE_REFERENCE_DATE,
    PNI_ELIGIBLE_SCOPE,
    SivepEvolutionCode,
    SivepYesNoCode,
    SourceFamily,
    SourceStatus,
)

# ---------------------------------------------------------------------------
# Private helpers — shared across all models
# ---------------------------------------------------------------------------

_SHA256_RE: re.Pattern[str] = re.compile(r"[0-9a-f]{64}")


def _validate_sha256(v: str) -> str:
    if _SHA256_RE.fullmatch(v) is None:
        raise ValueError(f"sha256 must be exactly 64 lowercase hex chars, got {len(v)}-char value")
    return v


def _validate_utc_zero(v: datetime.datetime) -> datetime.datetime:
    offset = v.utcoffset()
    if offset is None or offset != datetime.timedelta(0):
        raise ValueError("datetime must be timezone-aware with UTC offset zero (Z / +00:00)")
    return v


# ---------------------------------------------------------------------------
# Source file metadata models
# ---------------------------------------------------------------------------


class SourceFileMetadata(BaseModel):
    """Runtime provenance record for a loaded source file; used in manifests."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    family: SourceFamily
    identifier: str
    local_path: str
    sha256: str
    size_bytes: int = Field(ge=0)
    data_rows_loaded: int = Field(ge=0)
    encoding: str
    loaded_at: datetime.datetime
    schema_version: str

    @field_validator("sha256")
    @classmethod
    def _check_sha256(cls, v: str) -> str:
        return _validate_sha256(v)

    @field_validator("loaded_at")
    @classmethod
    def _check_loaded_at_utc(cls, v: datetime.datetime) -> datetime.datetime:
        return _validate_utc_zero(v)


class SourceFileEntry(BaseModel):
    """Pre-ingest declaration of an expected source artifact within a SourceContractDocument."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    family: SourceFamily
    identifier: str
    sha256: str
    local_path: str
    size_bytes: int = Field(ge=0)
    data_rows: int = Field(ge=0)
    retrieval_at: datetime.datetime
    watermark: str
    status: SourceStatus
    year: int | None = None

    @field_validator("sha256")
    @classmethod
    def _check_sha256(cls, v: str) -> str:
        return _validate_sha256(v)

    @field_validator("retrieval_at")
    @classmethod
    def _check_retrieval_at_utc(cls, v: datetime.datetime) -> datetime.datetime:
        return _validate_utc_zero(v)


class SourceContractDocument(BaseModel):
    """Versioned machine-readable source-contract document. extra='forbid'."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    schema_version: Literal["1.0"]
    contract_version: str
    contract_date: datetime.date
    cnes_competencia: Literal[202606]
    cnes_icu_allowlist: tuple[int, ...]
    sources: tuple[SourceFileEntry, ...]


# ---------------------------------------------------------------------------
# SIVEP canonical row
# ---------------------------------------------------------------------------


class SivepCanonicalRow(BaseModel):
    """
    Single SIVEP-Gripe record after canonical normalization.

    - notification_key: dedup only; NOT agent-facing.
    - digitization_date: insertion-only; NOT update provenance; NOT agent-facing.
    - No DT_ATUALIZA/DT_ALTERACAO field exists in the 194-col public schema.
    - evolution==DEATH_OTHER(3) → evolution_date MUST be None.
    - UNKNOWN(9) distinct from NO(2).
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    year: Literal[2025, 2026]
    source_sha256: str

    notification_key: str
    notification_date: datetime.date | None
    symptom_onset: datetime.date | None
    hospitalization_flag: SivepYesNoCode | None
    hospitalization_date: datetime.date | None
    hospitalization_uf: str | None
    icu_flag: SivepYesNoCode | None
    icu_entry_date: datetime.date | None
    icu_exit_date: datetime.date | None
    evolution: SivepEvolutionCode | None
    evolution_date: datetime.date | None
    closure_date: datetime.date | None
    digitization_date: datetime.datetime | None
    residence_uf: str | None

    @field_validator("source_sha256")
    @classmethod
    def _check_sha256(cls, v: str) -> str:
        return _validate_sha256(v)

    @model_validator(mode="after")
    def _check_death_other_evolution_date(self) -> SivepCanonicalRow:
        if self.evolution == SivepEvolutionCode.DEATH_OTHER and self.evolution_date is not None:
            raise ValueError(
                "evolution_date must be None when evolution is DEATH_OTHER (3): "
                "DT_EVOLUCA is disabled in SIVEP source for this evolution code"
            )
        return self


# ---------------------------------------------------------------------------
# CNES canonical row
# ---------------------------------------------------------------------------


class CnesCanonicalRow(BaseModel):
    """
    CNES ICU-bed record. Competência locked to 202606.
    Competência is injected from the DBC filename — not read from a DBC column.
    cod_leito must be in CNES_ICU_ALLOWLIST = {61,62,63,75,76,79,80,81,82}.
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    competencia: Literal[202606]
    uf: str
    cod_leito: int
    qt_exist: int = Field(ge=0)
    source_sha256: str

    @field_validator("source_sha256")
    @classmethod
    def _check_sha256(cls, v: str) -> str:
        return _validate_sha256(v)

    @field_validator("cod_leito")
    @classmethod
    def _check_cod_leito_in_allowlist(cls, v: int) -> int:
        if v not in CNES_ICU_ALLOWLIST:
            raise ValueError(
                f"cod_leito {v} is not in the frozen CNES ICU allowlist for "
                f"competência {CNES_COMPETENCIA}: {sorted(CNES_ICU_ALLOWLIST)}"
            )
        return v

    @field_validator("uf")
    @classmethod
    def _check_uf(cls, v: str) -> str:
        if len(v) != 2 or not v.isalpha() or not v.isupper():
            raise ValueError(f"uf must be 2-char uppercase alpha, got {v!r}")
        return v


# ---------------------------------------------------------------------------
# IBGE canonical row
# ---------------------------------------------------------------------------


class IbgePopulationRow(BaseModel):
    """IBGE 2025 Brazil population estimate (ref 2025-07-01, 213 421 037) [VERIFIED]."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    year: Literal[2025]
    geography: Literal["BR"]
    population_official: Literal[213_421_037]
    reference_date: datetime.date
    source_sha256: str

    @field_validator("source_sha256")
    @classmethod
    def _check_sha256(cls, v: str) -> str:
        return _validate_sha256(v)

    @field_validator("reference_date")
    @classmethod
    def _check_reference_date(cls, v: datetime.date) -> datetime.date:
        if v != IBGE_REFERENCE_DATE:
            raise ValueError(f"IBGE reference_date must be {IBGE_REFERENCE_DATE}, got {v}")
        return v


# ---------------------------------------------------------------------------
# PNI observation
# ---------------------------------------------------------------------------


class PniObservation(BaseModel):
    """
    PNI influenza 2026 observation (NE/CO/S/SE scope).
    is_nationwide=False, is_golden=False always.
    Eligibility (published_at <= as_of) is the CALLER's responsibility.
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    campaign_year: Literal[2026]
    immunobiological: Literal["INF3"]
    population_scope: frozenset[str]
    period_start: datetime.date
    period_end: datetime.date
    numerator: int = Field(gt=0)
    denominator: int = Field(gt=0)
    coverage_pct: Decimal
    published_at: datetime.datetime
    source_label: str
    is_nationwide: Literal[False]
    is_golden: Literal[False]

    @field_validator("population_scope")
    @classmethod
    def _check_population_scope(cls, v: frozenset[str]) -> frozenset[str]:
        if not v:
            raise ValueError("population_scope must be non-empty")
        invalid = v - PNI_ELIGIBLE_SCOPE
        if invalid:
            raise ValueError(f"population_scope contains invalid regions: {sorted(invalid)}")
        return v

    @field_serializer("population_scope")
    def _serialize_population_scope(self, value: frozenset[str]) -> list[str]:
        return sorted(value)

    @field_validator("published_at")
    @classmethod
    def _check_published_at_utc(cls, v: datetime.datetime) -> datetime.datetime:
        return _validate_utc_zero(v)

    @model_validator(mode="after")
    def _check_period_order(self) -> PniObservation:
        if self.period_start > self.period_end:
            raise ValueError(
                f"period_start ({self.period_start}) must be <= period_end ({self.period_end})"
            )
        return self
