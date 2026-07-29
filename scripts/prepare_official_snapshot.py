#!/usr/bin/env python3
"""Prepare a minimized official snapshot from already-attested local inputs.

No HTTP client is imported or used here.  Acquisition is intentionally a
separate command so this command is reproducible and network-free.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from acquire_official_sources import IBGE_SOURCE, SIVEP_SOURCE, OfficialSource

from srag_report.data.normalization import FieldReasonCounts, NormalizationCounts
from srag_report.data.publish import (
    NormalizationManifest,
    QualityManifest,
    normalization_manifest,
    publish_snapshot,
)
from srag_report.data.sivep import normalize_sivep_csv_to_jsonl
from srag_report.data.sources import normalize_ibge_ods
from srag_report.data.store import materialize_snapshot
from srag_report.domain.models import (
    IbgePopulationRow,
    SivepCanonicalRow,
    SourceContractDocument,
    SourceFileEntry,
)
from srag_report.domain.source import CNES_ICU_ALLOWLIST, QualityState, SourceFamily, SourceStatus


class PreparationError(RuntimeError):
    pass


def _file_sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _csv_rows(path: Path, encoding: str) -> int:
    import csv

    with path.open("r", encoding=encoding, newline="") as handle:
        return sum(1 for _ in csv.reader(handle, delimiter=";")) - 1


def _data_rows(path: Path, source: OfficialSource) -> int:
    if source.expected_data_rows is not None:
        return _csv_rows(path, source.encoding)
    from srag_report.data.decoders import iter_ods_rows

    return sum(1 for _ in iter_ods_rows(path))


def _load_acquisition(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PreparationError("acquisition_invalid") from exc
    if value.get("schema_version") != "1.0" or not isinstance(value.get("sources"), list):
        raise PreparationError("acquisition_invalid")
    return value


def _mapping_sha256(mapping: dict[str, str]) -> str:
    payload = json.dumps(mapping, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _acquisition_record(
    acquisition: dict[str, Any], source: OfficialSource
) -> dict[str, Any] | None:
    record = next(
        (
            item
            for item in acquisition["sources"]
            if isinstance(item, dict) and item.get("key") == source.key
        ),
        None,
    )
    return record if isinstance(record, dict) else None


def _attested(
    acquisition: dict[str, Any], source: OfficialSource, supplied_path: Path
) -> dict[str, Any]:
    record = _acquisition_record(acquisition, source)
    if record is None:
        raise PreparationError(f"{source.key}_not_verified")
    immutable_fields = {
        "key": source.key,
        "family": source.family,
        "identifier": source.identifier,
        "status": "verified",
        "official_landing_url": source.landing_url,
        "official_resource_url": source.resource_url,
        "license_reuse_statement": source.license_reuse_statement,
        "license_evidence_url": source.license_evidence_url,
        "encoding": source.encoding,
        "expected_sha256": source.expected_sha256,
        "expected_size_bytes": source.expected_size_bytes,
        "expected_data_rows": source.expected_data_rows,
        "dictionary_version": source.dictionary_version,
        "selected_column_mapping": source.selected_column_mapping,
        "watermark": source.watermark,
        "optional": source.optional,
    }
    if record.get("status") != "verified":
        raise PreparationError(f"{source.key}_not_verified")
    if any(record.get(field) != value for field, value in immutable_fields.items()):
        raise PreparationError(f"{source.key}_immutable_metadata_mismatch")
    actual_hash = _file_sha256(supplied_path)
    actual_size = supplied_path.stat().st_size
    actual_rows = _data_rows(supplied_path, source)
    if actual_hash != source.expected_sha256:
        raise PreparationError(f"{source.key}_hash_mismatch")
    if actual_size != source.expected_size_bytes:
        raise PreparationError(f"{source.key}_size_mismatch")
    if source.expected_data_rows is not None and actual_rows != source.expected_data_rows:
        raise PreparationError(f"{source.key}_row_count_mismatch")
    required = ("retrieved_at", "raw_sha256", "size_bytes", "data_rows")
    if any(not record.get(field) for field in required):
        raise PreparationError(f"{source.key}_provenance_incomplete")
    if record["raw_sha256"] != actual_hash or record["size_bytes"] != actual_size:
        raise PreparationError(f"{source.key}_attestation_mismatch")
    if record.get("data_rows") != actual_rows:
        raise PreparationError(f"{source.key}_attestation_mismatch")
    return record


def _source_entry(
    source: OfficialSource, record: dict[str, Any], path: Path, *, year: int
) -> SourceFileEntry:
    return SourceFileEntry(
        family=SourceFamily(source.family),
        identifier=source.identifier,
        sha256=source.expected_sha256,
        local_path=str(path),
        size_bytes=source.expected_size_bytes,
        data_rows=int(record["data_rows"]),
        retrieval_at=dt.datetime.fromisoformat(str(record["retrieved_at"]).replace("Z", "+00:00")),
        watermark=source.watermark,
        status=SourceStatus.VERIFIED,
        year=year,
    )


def _sanitized_source_attestation(source: OfficialSource, record: dict[str, Any]) -> dict[str, Any]:
    """Expose complete verification results without raw mappings or local paths."""
    return {
        "key": source.key,
        "family": source.family,
        "identifier": source.identifier,
        "verified": True,
        "official_landing_url": source.landing_url,
        "official_resource_url": source.resource_url,
        "license_reuse_statement": source.license_reuse_statement,
        "license_evidence_url": source.license_evidence_url,
        "encoding": source.encoding,
        "expected_sha256": source.expected_sha256,
        "expected_size_bytes": source.expected_size_bytes,
        "expected_data_rows": source.expected_data_rows,
        "actual_sha256": record["raw_sha256"],
        "actual_size_bytes": record["size_bytes"],
        "actual_data_rows": record["data_rows"],
        "dictionary_version": source.dictionary_version,
        "selected_column_mapping_sha256": _mapping_sha256(source.selected_column_mapping),
        "selected_column_mapping_verified": True,
        "watermark": source.watermark,
        "retrieved_at": record["retrieved_at"],
    }


def _write_official_provenance(
    published: Path,
    *,
    snapshot_id: str,
    result: str,
    sources: list[dict[str, Any]],
    artifact_sha256: str,
) -> tuple[str, str]:
    attestation = {
        "schema_version": "1.0",
        "snapshot_id": snapshot_id,
        "result": result,
        "canonical_snapshot_sha256": artifact_sha256,
        "sources": sources,
    }
    payload = (json.dumps(attestation, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    digest = hashlib.sha256(payload).hexdigest()
    provenance_path = published / "official-provenance.json"
    _atomic_write_bytes(provenance_path, payload)
    _atomic_write_bytes(provenance_path.with_suffix(".json.sha256"), f"{digest}\n".encode("ascii"))
    return digest, result


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    """Replace ``path`` with complete bytes, never a partially-written file."""
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    os.close(descriptor)
    temporary = Path(name)
    try:
        with temporary.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _jsonl_rows(path: Path) -> Iterable[SivepCanonicalRow]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            yield SivepCanonicalRow.model_validate_json(line)


def _absent_manifest(family: SourceFamily, reason: str) -> NormalizationManifest:
    return normalization_manifest(
        family,
        counts=NormalizationCounts(total_input=0, accepted=0),
        reasons=FieldReasonCounts(by_reason={reason: 1}),
        completeness=0.0,
        quality_state=QualityState.UNAVAILABLE,
        blocked=False,
        blocker_reason=None,
    )


def prepare_snapshot(
    *,
    acquisition_path: Path,
    sivep_csv: Path,
    ibge_ods: Path | None,
    output_root: Path,
    snapshot_id: str,
    as_of: dt.date,
    generated_at: dt.datetime | None = None,
) -> Path:
    """Verify local attestations and publish an explicitly ineligible warning snapshot."""
    acquisition = _load_acquisition(acquisition_path)
    sivep_record = _attested(acquisition, SIVEP_SOURCE, sivep_csv)
    attested_sources = [_sanitized_source_attestation(SIVEP_SOURCE, sivep_record)]
    generated = generated_at or dt.datetime.now(dt.UTC)
    if generated.utcoffset() != dt.timedelta(0):
        raise PreparationError("generated_at_not_utc")
    normalized_jsonl = output_root / ".prepared" / f"{snapshot_id}.sivep.jsonl"
    sivep_result = normalize_sivep_csv_to_jsonl(
        sivep_csv,
        normalized_jsonl,
        source_sha256=SIVEP_SOURCE.expected_sha256,
        year=2026,
        watermark=as_of,
    )
    if sivep_result.blocked:
        raise PreparationError("sivep_normalization_blocked")
    sources = [_source_entry(SIVEP_SOURCE, sivep_record, sivep_csv, year=2026)]
    ibge_rows: tuple[IbgePopulationRow, ...] = ()
    normalization = [
        normalization_manifest(
            SourceFamily.SIVEP,
            counts=sivep_result.counts,
            reasons=sivep_result.reasons,
            completeness=sivep_result.completeness,
            quality_state=sivep_result.quality_state,
            blocked=False,
            blocker_reason=None,
        )
    ]
    ibge_available = False
    if (
        ibge_ods is not None
        and (_acquisition_record(acquisition, IBGE_SOURCE) or {}).get("status") == "verified"
    ):
        verified_ibge = _attested(acquisition, IBGE_SOURCE, ibge_ods)
        ibge_row, ibge_result = normalize_ibge_ods(
            ibge_ods,
            source_sha256=IBGE_SOURCE.expected_sha256,
            header_row_index=1,
        )
        if ibge_result.blocked or ibge_row is None:
            raise PreparationError("ibge_normalization_blocked")
        ibge_rows = (ibge_row,)
        sources.append(_source_entry(IBGE_SOURCE, verified_ibge, ibge_ods, year=2025))
        normalization.append(
            normalization_manifest(
                SourceFamily.IBGE,
                counts=ibge_result.counts,
                reasons=ibge_result.reasons,
                completeness=ibge_result.completeness,
                quality_state=ibge_result.quality_state,
                blocked=False,
                blocker_reason=None,
            )
        )
        ibge_available = True
        attested_sources.append(_sanitized_source_attestation(IBGE_SOURCE, verified_ibge))
    else:
        normalization.append(_absent_manifest(SourceFamily.IBGE, "ibge_source_unavailable"))
    normalization.extend(
        (
            _absent_manifest(SourceFamily.CNES, "cnes_source_unavailable"),
            _absent_manifest(SourceFamily.PNI, "pni_source_unavailable"),
        )
    )
    contract = SourceContractDocument(
        schema_version="1.0",
        contract_version="official-2026-07-29",
        contract_date=dt.date(2026, 7, 29),
        cnes_competencia=202606,
        cnes_icu_allowlist=tuple(sorted(CNES_ICU_ALLOWLIST)),
        sources=tuple(sources),
    )
    artifact = materialize_snapshot(
        output_root / ".prepared" / f"{snapshot_id}.duckdb",
        sivep_rows=_jsonl_rows(normalized_jsonl),
        cnes_rows=(),
        ibge_rows=ibge_rows,
        source_contracts=(contract,),
    )
    metric_states = {
        "case_growth": "available",
        "mortality_per_100k": "available" if ibge_available else "unavailable",
        "hospital_cfr": "available",
        "icu_pressure": "unavailable",
        "icu_use": "available",
        "influenza_coverage": "unavailable",
    }
    quality = QualityManifest(
        snapshot_id=snapshot_id,
        state=QualityState.WARNING,
        metric_completeness={
            name: 1.0 if state == "available" else 0.0 for name, state in metric_states.items()
        },
    )
    published = publish_snapshot(
        output_root,
        snapshot_id=snapshot_id,
        artifact=artifact,
        contract=contract,
        normalization=normalization,
        quality=quality,
        generated_at=generated,
        as_of=as_of,
    )
    provenance_sha256, provenance_result = _write_official_provenance(
        published,
        snapshot_id=snapshot_id,
        result="prepared_warning_ineligible",
        sources=attested_sources,
        artifact_sha256=artifact.content_sha256,
    )
    evidence = {
        "schema_version": "1.0",
        "source_status": {
            "sivep": "verified",
            "ibge": "verified" if ibge_available else "unavailable",
            "cnes": "unavailable",
            "pni": "unavailable",
        },
        "normalization": {
            item.family.value: item.counts.model_dump(mode="json") for item in normalization
        },
        "effective_watermarks": {
            "sivep": SIVEP_SOURCE.watermark,
            "ibge": IBGE_SOURCE.watermark if ibge_available else None,
        },
        "metric_states": metric_states,
        "golden_eligible": False,
        "golden_ineligibility_reasons": ["cnes_source_unavailable", "pni_source_unavailable"]
        + ([] if ibge_available else ["ibge_source_unavailable"]),
        "canonical_snapshot_sha256": artifact.content_sha256,
        "snapshot_file_sha256": artifact.file_sha256,
        "official_provenance_sha256": provenance_sha256,
        "official_provenance_result": provenance_result,
    }
    (published / "official-preparation.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return published


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acquisition", type=Path, required=True)
    parser.add_argument("--sivep-csv", type=Path, required=True)
    parser.add_argument("--ibge-ods", type=Path)
    parser.add_argument("--output-root", type=Path, default=Path("data/snapshots"))
    parser.add_argument("--snapshot-id", default="official-20260727")
    parser.add_argument("--as-of", type=dt.date.fromisoformat, default=dt.date(2026, 7, 26))
    args = parser.parse_args()
    prepare_snapshot(
        acquisition_path=args.acquisition,
        sivep_csv=args.sivep_csv,
        ibge_ods=args.ibge_ods,
        output_root=args.output_root,
        snapshot_id=args.snapshot_id,
        as_of=args.as_of,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
