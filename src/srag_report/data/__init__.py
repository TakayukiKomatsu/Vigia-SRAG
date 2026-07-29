"""Data layer: source-contract loading, validation, and quality evaluation."""

from .contracts import (
    ContractFieldError,
    ContractValidationError,
    evaluate_quality_state,
    load_source_contract,
)
from .normalization import (
    CnesNormalizationResult,
    FieldReasonCounts,
    IbgeNormalizationResult,
    NormalizationCounts,
    PniNormalizationResult,
    SivepNormalizationResult,
)
from .publish import (
    NormalizationManifest,
    PublicationError,
    PublicationState,
    QualityManifest,
    SnapshotManifest,
    build_snapshot_manifest,
    load_published_snapshot_manifest,
    normalization_manifest,
    publish_snapshot,
)
from .sivep import (
    canonical_completeness,
    canonical_row_sha256,
    normalize_sivep_csv_to_jsonl,
    normalize_sivep_rows,
)
from .sources import (
    normalize_cnes_dbc,
    normalize_cnes_rows,
    normalize_ibge_ods,
    normalize_ibge_rows,
    normalize_pni_observation,
)
from .store import (
    SnapshotArtifact,
    assert_minimized_schema,
    logical_snapshot_sha256,
    materialize_snapshot,
    open_snapshot,
    snapshot_table_counts,
)

__all__ = [
    "ContractFieldError",
    "ContractValidationError",
    "evaluate_quality_state",
    "load_source_contract",
    "CnesNormalizationResult",
    "FieldReasonCounts",
    "IbgeNormalizationResult",
    "NormalizationCounts",
    "PniNormalizationResult",
    "SivepNormalizationResult",
    "canonical_completeness",
    "canonical_row_sha256",
    "normalize_sivep_csv_to_jsonl",
    "normalize_sivep_rows",
    "normalize_cnes_dbc",
    "normalize_cnes_rows",
    "normalize_ibge_ods",
    "normalize_ibge_rows",
    "normalize_pni_observation",
    "SnapshotArtifact",
    "assert_minimized_schema",
    "logical_snapshot_sha256",
    "materialize_snapshot",
    "open_snapshot",
    "snapshot_table_counts",
    "NormalizationManifest",
    "PublicationError",
    "PublicationState",
    "QualityManifest",
    "SnapshotManifest",
    "build_snapshot_manifest",
    "load_published_snapshot_manifest",
    "normalization_manifest",
    "publish_snapshot",
]
