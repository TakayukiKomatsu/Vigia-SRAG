#!/usr/bin/env python3
"""Acquire and attest the fixed official SRAG source artifacts.

This command is deliberately the *only* networked step in the official-source
workflow.  It writes an ignored acquisition sidecar; preparation consumes that
sidecar without opening a network connection.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

SIVEP_SHA256 = "5b1de50c4ca58b1c7068d61f58b42772d1634a06917d41443443fff1fdd359fb"
SIVEP_SIZE = 198_233_708
SIVEP_ROWS = 177_445
IBGE_SHA256 = "33dc6f79def9522e282cd69b87a9ce75327a81239d6060d9c8f9f5a49bd2a1b5"
IBGE_SIZE = 212_846


@dataclass(frozen=True, slots=True)
class OfficialSource:
    key: str
    family: str
    identifier: str
    landing_url: str
    resource_url: str
    license_reuse_statement: str
    license_evidence_url: str
    encoding: str
    expected_sha256: str
    expected_size_bytes: int
    expected_data_rows: int | None
    dictionary_version: str
    selected_column_mapping: dict[str, str]
    watermark: str
    relative_path: str
    optional: bool = False


SIVEP_SOURCE = OfficialSource(
    key="sivep",
    family="sivep",
    identifier="INFLUD26-27-07-2026.csv",
    landing_url="https://dadosabertos.saude.gov.br/dataset/srag-2019-a-2026",
    resource_url="https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG/2026/INFLUD26-27-07-2026.csv",
    license_reuse_statement="CC BY-ND 3.0 BR; reuse is subject to its no-derivatives terms.",
    license_evidence_url="https://dadosabertos.saude.gov.br/dataset/srag-2019-a-2026",
    encoding="utf-8",
    expected_sha256=SIVEP_SHA256,
    expected_size_bytes=SIVEP_SIZE,
    expected_data_rows=SIVEP_ROWS,
    dictionary_version="dicionario-de-dados-2019-a-2025.pdf (2026-01-29)",
    selected_column_mapping={
        "notification_key": "NU_NOTIFIC", "notification_date": "DT_NOTIFIC",
        "symptom_onset": "DT_SIN_PRI", "hospitalization_flag": "HOSPITAL",
        "hospitalization_date": "DT_INTERNA", "hospitalization_uf": "SG_UF_INTE",
        "icu_flag": "UTI", "icu_entry_date": "DT_ENTUTI", "icu_exit_date": "DT_SAIDUTI",
        "evolution": "EVOLUCAO", "evolution_date": "DT_EVOLUCA",
        "closure_date": "DT_ENCERRA", "digitization_date": "DT_DIGITA", "residence_uf": "SG_UF",
    },
    watermark="2026-07-26",
    relative_path="sivep/INFLUD26-27-07-2026.csv",
)
IBGE_SOURCE = OfficialSource(
    key="ibge", family="ibge", identifier="POP2025_20260113.ods",
    landing_url="https://www.ibge.gov.br/estatisticas/sociais/populacao/9103-estimativas-de-populacao.html",
    resource_url="https://ftp.ibge.gov.br/Estimativas_de_Populacao/Estimativas_2025/POP2025_20260113.ods",
    license_reuse_statement="Public-domain aggregated official data; attribution to IBGE/DPE/COPIS required.",
    license_evidence_url="https://www.ibge.gov.br/acesso-informacao/institucional/2018-05-31-15-17-49.html",
    encoding="ods", expected_sha256=IBGE_SHA256, expected_size_bytes=IBGE_SIZE,
    expected_data_rows=None, dictionary_version="POP2025_20260113.ods",
    selected_column_mapping={"year": "BRASIL", "geography": "BRASIL", "population_official": "POPULAÇÃO ESTIMADA", "reference_date": "2025-07-01"},
    watermark="2025-07-01", relative_path="ibge/POP2025_20260113.ods", optional=True,
)


def _utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def _count_csv_rows(path: Path, encoding: str) -> int:
    with path.open("r", encoding=encoding, newline="") as handle:
        return sum(1 for _ in csv.reader(handle, delimiter=";")) - 1


def _data_rows(path: Path, source: OfficialSource) -> int:
    if source.expected_data_rows is not None:
        return _count_csv_rows(path, source.encoding)
    # ODS is optional but receives the same complete provenance treatment.
    from srag_report.data.decoders import iter_ods_rows

    return sum(1 for _ in iter_ods_rows(path))


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    os.close(descriptor)
    temporary = Path(name)
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def acquire_source(client: httpx.Client, source: OfficialSource, output_root: Path) -> dict[str, Any]:
    """Download one artifact atomically and return its complete provenance record."""
    retrieved_at = _utc_now()
    record: dict[str, Any] = {
        "key": source.key, "family": source.family, "identifier": source.identifier,
        "status": "unavailable", "retrieved_at": retrieved_at,
        "official_landing_url": source.landing_url, "official_resource_url": source.resource_url,
        "license_reuse_statement": source.license_reuse_statement,
        "license_evidence_url": source.license_evidence_url, "encoding": source.encoding,
        "expected_sha256": source.expected_sha256, "expected_size_bytes": source.expected_size_bytes,
        "expected_data_rows": source.expected_data_rows, "dictionary_version": source.dictionary_version,
        "selected_column_mapping": source.selected_column_mapping, "watermark": source.watermark,
        "optional": source.optional,
    }
    destination = output_root / source.relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    os.close(descriptor)
    temporary = Path(name)
    try:
        digest = hashlib.sha256()
        size = 0
        with client.stream("GET", source.resource_url) as response:
            response.raise_for_status()
            with temporary.open("wb") as handle:
                for chunk in response.iter_bytes():
                    handle.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
        actual_hash = digest.hexdigest()
        actual_rows = _data_rows(temporary, source)
        record.update({"raw_sha256": actual_hash, "size_bytes": size, "data_rows": actual_rows})
        if actual_hash != source.expected_sha256:
            raise ValueError("sha256_mismatch")
        if size != source.expected_size_bytes:
            raise ValueError("size_mismatch")
        if source.expected_data_rows is not None and actual_rows != source.expected_data_rows:
            raise ValueError("row_count_mismatch")
        os.replace(temporary, destination)
        record["status"] = "verified"
        record["local_path"] = source.relative_path
    except Exception as exc:
        record["failure_code"] = str(exc).split(":", 1)[0] or type(exc).__name__
    finally:
        temporary.unlink(missing_ok=True)
    return record


def acquire_all(output_root: Path, *, blocked_root: Path, sources: tuple[OfficialSource, ...] = (SIVEP_SOURCE, IBGE_SOURCE)) -> dict[str, Any]:
    """Acquire fixed sources independently; only a failed SIVEP blocks execution."""
    with httpx.Client(timeout=httpx.Timeout(60.0), follow_redirects=True, trust_env=False) as client:
        records = [acquire_source(client, source, output_root) for source in sources]
    result = {"schema_version": "1.0", "generated_at": _utc_now(), "sources": records}
    _atomic_json(output_root / "acquisition.json", result)
    sivep = next(item for item in records if item["key"] == "sivep")
    if sivep["status"] != "verified":
        _atomic_json(blocked_root / "official-source-blocked.json", {
            "schema_version": "1.0", "blocked_at": _utc_now(), "reason_code": "sivep_acquisition_blocked",
            "sivep_status": sivep["status"], "failure_code": sivep.get("failure_code"),
        })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=Path("data/raw"))
    parser.add_argument("--blocked-root", type=Path, default=Path("runs"))
    args = parser.parse_args()
    result = acquire_all(args.output_root, blocked_root=args.blocked_root)
    return 0 if next(item for item in result["sources"] if item["key"] == "sivep")["status"] == "verified" else 1


if __name__ == "__main__":
    raise SystemExit(main())
