"""
Source-family enums, frozen code matrices, and field mappings for SRAG data foundation.

All constants are immutable at runtime. Changing any locked constant
(CNES_COMPETENCIA, CNES_ICU_ALLOWLIST) reopens the downstream contract.
"""

from __future__ import annotations

import datetime
from enum import IntEnum, StrEnum
from typing import Final

# ---------------------------------------------------------------------------
# Source-level enumerations
# ---------------------------------------------------------------------------


class SourceFamily(StrEnum):
    """Recognized official source families."""

    SIVEP = "sivep"
    CNES = "cnes"
    IBGE = "ibge"
    PNI = "pni"


class SourceStatus(StrEnum):
    """Verification status of a source artifact."""

    VERIFIED = "VERIFIED"
    PARTIAL = "PARTIAL"
    UNVERIFIED = "UNVERIFIED"
    INELIGIBLE = "INELIGIBLE"


class QualityState(StrEnum):
    """
    Completeness-driven quality state for a metric.

    Structural blockers (critical column absent, hash mismatch, insufficient period
    coverage) produce BLOCKED regardless of the completeness fraction.
    """

    AVAILABLE = "available"  # >= 90 %
    WARNING = "warning"  # 70 % <= x < 90 %
    UNAVAILABLE = "unavailable"  # < 70 %
    BLOCKED = "blocked"  # structural blocker — overrides percentage


# ---------------------------------------------------------------------------
# Reason codes
# ---------------------------------------------------------------------------


class NullReason(StrEnum):
    """Reason a field value was nullified during normalization."""

    IMPOSSIBLE_DATE = "impossible_date"
    FUTURE_DATE = "future_date"
    INVALID_ORDER = "invalid_order"
    FIELD_DISABLED_BY_EVOLUTION = "field_disabled_by_evolution"
    NOT_APPLICABLE = "not_applicable"
    MISSING = "missing"
    UNKNOWN_CODE = "unknown_code"


class QuarantineReason(StrEnum):
    """Reason a record was placed in quarantine (structural failure)."""

    MISSING_MINIMUM_STRUCTURE = "missing_minimum_structure"
    CRITICAL_COLUMN_ABSENT = "critical_column_absent"
    SCHEMA_INCOMPATIBLE = "schema_incompatible"
    HASH_MISMATCH = "hash_mismatch"


class DedupReason(StrEnum):
    """Resolution step used when deduplicating records sharing the same key."""

    CANONICAL_COMPLETENESS = "canonical_completeness"  # higher completeness wins
    STABLE_SHA256 = "stable_sha256"  # tiebreak: lower canonical-row SHA-256


# ---------------------------------------------------------------------------
# SIVEP code tables
# ---------------------------------------------------------------------------


class SivepYesNoCode(IntEnum):
    """
    Binary response codes for HOSPITAL and UTI fields.
    UNKNOWN (9 = Ignorado) is distinct from NO (2) — never conflated.
    """

    YES = 1
    NO = 2
    UNKNOWN = 9  # Ignorado — NOT equivalent to NO


class SivepEvolutionCode(IntEnum):
    """
    EVOLUCAO field codes.

    Normative semantics:
    - DEATH_SRAG (2): verified SRAG/respiratory death; DT_EVOLUCA present.
    - DEATH_OTHER (3): death from other causes; DT_EVOLUCA DISABLED in source → must be None.
    - UNKNOWN (9): ignorado — distinct from any other value.
    """

    CURE = 1  # Alta / Cura
    DEATH_SRAG = 2  # Óbito — SRAG / causa respiratória [VERIFIED]
    DEATH_OTHER = 3  # Óbito — outras causas; DT_EVOLUCA disabled
    UNKNOWN = 9  # Ignorado


# ---------------------------------------------------------------------------
# SIVEP canonical field names
# ---------------------------------------------------------------------------


class SivepCanonicalField(StrEnum):
    """All canonical field names produced by SIVEP normalization."""

    NOTIFICATION_KEY = "notification_key"  # pre-aggregation only; not agent-facing
    NOTIFICATION_DATE = "notification_date"
    SYMPTOM_ONSET = "symptom_onset"
    HOSPITALIZATION_FLAG = "hospitalization_flag"
    HOSPITALIZATION_DATE = "hospitalization_date"
    HOSPITALIZATION_UF = "hospitalization_uf"
    ICU_FLAG = "icu_flag"
    ICU_ENTRY_DATE = "icu_entry_date"
    ICU_EXIT_DATE = "icu_exit_date"
    EVOLUTION = "evolution"
    EVOLUTION_DATE = "evolution_date"
    CLOSURE_DATE = "closure_date"
    DIGITIZATION_DATE = "digitization_date"  # insertion timestamp only; not agent-facing
    RESIDENCE_UF = "residence_uf"


# Source-column → canonical-field mapping (normative; 14 MVP fields)
SIVEP_SOURCE_TO_CANONICAL: Final[dict[str, SivepCanonicalField]] = {
    "NU_NOTIFIC": SivepCanonicalField.NOTIFICATION_KEY,
    "DT_NOTIFIC": SivepCanonicalField.NOTIFICATION_DATE,
    "DT_SIN_PRI": SivepCanonicalField.SYMPTOM_ONSET,
    "HOSPITAL": SivepCanonicalField.HOSPITALIZATION_FLAG,
    "DT_INTERNA": SivepCanonicalField.HOSPITALIZATION_DATE,
    "SG_UF_INTE": SivepCanonicalField.HOSPITALIZATION_UF,
    "UTI": SivepCanonicalField.ICU_FLAG,
    "DT_ENTUTI": SivepCanonicalField.ICU_ENTRY_DATE,
    "DT_SAIDUTI": SivepCanonicalField.ICU_EXIT_DATE,
    "EVOLUCAO": SivepCanonicalField.EVOLUTION,
    "DT_EVOLUCA": SivepCanonicalField.EVOLUTION_DATE,
    "DT_ENCERRA": SivepCanonicalField.CLOSURE_DATE,
    "DT_DIGITA": SivepCanonicalField.DIGITIZATION_DATE,
    "SG_UF": SivepCanonicalField.RESIDENCE_UF,
}

# All source columns that must be present; absence → schema blocker
SIVEP_REQUIRED_SOURCE_COLUMNS: Final[frozenset[str]] = frozenset(SIVEP_SOURCE_TO_CANONICAL.keys())

# Critical columns whose absence triggers quarantine (not nullification)
SIVEP_CRITICAL_SOURCE_COLUMNS: Final[frozenset[str]] = frozenset(
    {
        "NU_NOTIFIC",  # dedup key — absence makes the record unresolvable
        "DT_SIN_PRI",  # epidemiological anchor — absence makes the record unclassifiable
    }
)

# Fields used to score canonical completeness for deduplication.
# Excludes technical identifiers (NOTIFICATION_KEY, DIGITIZATION_DATE).
SIVEP_CANONICAL_COMPLETENESS_FIELDS: Final[frozenset[SivepCanonicalField]] = frozenset(
    {
        SivepCanonicalField.NOTIFICATION_DATE,
        SivepCanonicalField.SYMPTOM_ONSET,
        SivepCanonicalField.HOSPITALIZATION_FLAG,
        SivepCanonicalField.HOSPITALIZATION_DATE,
        SivepCanonicalField.HOSPITALIZATION_UF,
        SivepCanonicalField.ICU_FLAG,
        SivepCanonicalField.ICU_ENTRY_DATE,
        SivepCanonicalField.ICU_EXIT_DATE,
        SivepCanonicalField.EVOLUTION,
        SivepCanonicalField.EVOLUTION_DATE,
        SivepCanonicalField.CLOSURE_DATE,
        SivepCanonicalField.RESIDENCE_UF,
    }
)

# Fields FORBIDDEN in agent-facing (DuckDB) output
SIVEP_AGENT_FACING_FORBIDDEN: Final[frozenset[SivepCanonicalField]] = frozenset(
    {
        SivepCanonicalField.NOTIFICATION_KEY,  # technical dedup key
        SivepCanonicalField.DIGITIZATION_DATE,  # insertion provenance; not update; not clinical
    }
)

# Fields permitted in minimized agent-facing aggregations
SIVEP_MINIMIZATION_ALLOWLIST: Final[frozenset[SivepCanonicalField]] = frozenset(
    {
        SivepCanonicalField.SYMPTOM_ONSET,
        SivepCanonicalField.HOSPITALIZATION_FLAG,
        SivepCanonicalField.HOSPITALIZATION_UF,
        SivepCanonicalField.ICU_FLAG,
        SivepCanonicalField.EVOLUTION,
        SivepCanonicalField.EVOLUTION_DATE,
        SivepCanonicalField.RESIDENCE_UF,
    }
)

# Code matrix: EVOLUCAO raw integer → SivepEvolutionCode
SIVEP_EVOLUTION_CODE_MATRIX: Final[dict[int, SivepEvolutionCode]] = {
    1: SivepEvolutionCode.CURE,
    2: SivepEvolutionCode.DEATH_SRAG,
    3: SivepEvolutionCode.DEATH_OTHER,
    9: SivepEvolutionCode.UNKNOWN,
}

# Code matrix: HOSPITAL / UTI raw integer → SivepYesNoCode
SIVEP_YESNO_CODE_MATRIX: Final[dict[int, SivepYesNoCode]] = {
    1: SivepYesNoCode.YES,
    2: SivepYesNoCode.NO,
    9: SivepYesNoCode.UNKNOWN,
}


# ---------------------------------------------------------------------------
# CNES canonical fields and frozen constants
# ---------------------------------------------------------------------------


class CnesCanonicalField(StrEnum):
    """Canonical field names for CNES ICU-bed normalization output."""

    COMPETENCIA = "competencia"
    UF = "uf"
    COD_LEITO = "cod_leito"
    QT_EXIST = "qt_exist"


# Competência (202606) is injected from the DBC filename (LT{UF}202606.dbc) or the
# locked constant CNES_COMPETENCIA — it is NOT read from a DBC column.
CNES_SOURCE_TO_CANONICAL: Final[dict[str, CnesCanonicalField]] = {
    "CODUFMUN": CnesCanonicalField.UF,  # first 2 chars → 2-char UF
    "COD_LEITO": CnesCanonicalField.COD_LEITO,
    "QT_EXIST": CnesCanonicalField.QT_EXIST,
}

CNES_REQUIRED_SOURCE_COLUMNS: Final[frozenset[str]] = frozenset(
    {
        "CNES",  # facility ID (traceability; not canonical)
        "CODUFMUN",
        "TP_LEITO",  # filter: only '03' (complementar/UTI) processed
        "COD_LEITO",
        "QT_EXIST",
    }
)

CNES_CRITICAL_SOURCE_COLUMNS: Final[frozenset[str]] = frozenset(
    {
        "COD_LEITO",
        "QT_EXIST",
    }
)

# Frozen exact ICU cod_leito allowlist — competência 202606 ONLY.
# Source: source-contracts.md §ICU Codes; CNES/CONASS + Portaria SAES 3511/2025.
# Any other competência reopens this mapping.
CNES_ICU_ALLOWLIST: Final[frozenset[int]] = frozenset({61, 62, 63, 75, 76, 79, 80, 81, 82})

# Locked competência — changing this reopens the allowlist and field mapping
CNES_COMPETENCIA: Final[int] = 202606

CNES_BED_METRIC_FIELD: Final[str] = "QT_EXIST"
CNES_COMPLEMENTARY_BED_TYPE: Final[str] = "03"  # TP_LEITO value for UTI/complementar


# ---------------------------------------------------------------------------
# IBGE canonical fields and frozen constants
# ---------------------------------------------------------------------------


class IbgeCanonicalField(StrEnum):
    """Canonical field names for IBGE population estimate."""

    YEAR = "year"
    GEOGRAPHY = "geography"
    POPULATION_OFFICIAL = "population_official"
    REFERENCE_DATE = "reference_date"


IBGE_BRAZIL_POPULATION: Final[int] = 213_421_037
IBGE_REFERENCE_YEAR: Final[int] = 2025
IBGE_GEOGRAPHY: Final[str] = "BR"
IBGE_REFERENCE_DATE: Final[datetime.date] = datetime.date(2025, 7, 1)


# ---------------------------------------------------------------------------
# PNI canonical fields and frozen constants
# ---------------------------------------------------------------------------


class PniCanonicalField(StrEnum):
    """Canonical field names for PNI influenza observation."""

    CAMPAIGN_YEAR = "campaign_year"
    IMMUNOBIOLOGICAL = "immunobiological"
    POPULATION_SCOPE = "population_scope"
    PERIOD_START = "period_start"
    PERIOD_END = "period_end"
    NUMERATOR = "numerator"
    DENOMINATOR = "denominator"
    COVERAGE_PCT = "coverage_pct"
    PUBLISHED_AT = "published_at"
    SOURCE_LABEL = "source_label"
    IS_NATIONWIDE = "is_nationwide"
    IS_GOLDEN = "is_golden"


# Eligible population scope for the 2026 influenza campaign.
# NEVER "national". NEVER "golden". Eligible only when published_at <= as_of.
PNI_ELIGIBLE_SCOPE: Final[frozenset[str]] = frozenset({"NE", "CO", "S", "SE"})
PNI_CAMPAIGN_YEAR: Final[int] = 2026


# ---------------------------------------------------------------------------
# Quality thresholds (PoC guardrails; not official epidemiological standards)
# ---------------------------------------------------------------------------

QUALITY_THRESHOLD_AVAILABLE: Final[float] = 0.90  # >= 90 % → available
QUALITY_THRESHOLD_WARNING: Final[float] = 0.70  # >= 70 % → warning; < 70 % → unavailable
