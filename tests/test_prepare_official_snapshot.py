from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from odf import opendocument, table, text

_SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(_SCRIPTS))
import acquire_official_sources as acquire  # noqa: E402
import prepare_official_snapshot as prepare  # noqa: E402


def _sivep_bytes() -> bytes:
    fields = [
        "NU_NOTIFIC",
        "DT_NOTIFIC",
        "DT_SIN_PRI",
        "HOSPITAL",
        "DT_INTERNA",
        "SG_UF_INTE",
        "UTI",
        "DT_ENTUTI",
        "DT_SAIDUTI",
        "EVOLUCAO",
        "DT_EVOLUCA",
        "DT_ENCERRA",
        "DT_DIGITA",
        "SG_UF",
    ]
    row = [
        "fixture-1",
        "2026-07-02",
        "2026-07-01",
        "1",
        "2026-07-03",
        "SP",
        "2",
        "",
        "",
        "1",
        "2026-07-05",
        "2026-07-05",
        "2026-07-02T00:00:00.000Z",
        "SP",
    ]
    return (";".join(fields) + "\n" + ";".join(row) + "\n").encode()


def _official_ibge_ods(path: Path) -> None:
    document = opendocument.OpenDocumentSpreadsheet()
    sheet = table.Table(name="BRASIL_E_UFs")
    for values in (
        ("POPULAÇÃO ESTIMADA",),
        ("BRASIL E UNIDADES DA FEDERAÇÃO", "POPULAÇÃO ESTIMADA"),
        ("Brasil", "213.421.037"),
    ):
        row = table.TableRow()
        for value in values:
            cell = table.TableCell()
            cell.addElement(text.P(text=value))
            row.addElement(cell)
        sheet.addElement(row)
    document.spreadsheet.addElement(sheet)
    document.save(str(path))


def _source(
    base: acquire.OfficialSource, *, payload: bytes, relative_path: str
) -> acquire.OfficialSource:
    return replace(
        base,
        expected_sha256=hashlib.sha256(payload).hexdigest(),
        expected_size_bytes=len(payload),
        expected_data_rows=1 if base.key == "sivep" else None,
        resource_url=f"https://fixture.test/{relative_path}",
        relative_path=relative_path,
    )


def _record(
    source: acquire.OfficialSource, payload: bytes, *, rows: int | None = None
) -> dict[str, object]:
    return {
        "key": source.key,
        "family": source.family,
        "identifier": source.identifier,
        "status": "verified",
        "retrieved_at": "2026-07-27T00:00:00Z",
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
        "raw_sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
        "data_rows": rows,
    }


def test_acquisition_records_complete_provenance_and_independent_optional_failure(
    tmp_path: Path,
) -> None:
    sivep_payload = _sivep_bytes()
    sivep = _source(acquire.SIVEP_SOURCE, payload=sivep_payload, relative_path="sivep.csv")
    ibge = _source(acquire.IBGE_SOURCE, payload=b"wrong", relative_path="ibge.ods")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200 if request.url.path == "/sivep.csv" else 404, content=sivep_payload, request=request
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        first = acquire.acquire_source(client, sivep, tmp_path / "raw")
        second = acquire.acquire_source(client, ibge, tmp_path / "raw")
    assert first["status"] == "verified"
    assert first["official_landing_url"] != first["official_resource_url"]
    assert first["license_reuse_statement"] and first["license_evidence_url"]
    assert first["selected_column_mapping"] and first["dictionary_version"]
    assert second["status"] == "unavailable"
    assert (tmp_path / "raw" / "sivep.csv").read_bytes() == sivep_payload


def test_prepare_sivep_only_publishes_empty_supporting_tables_and_ineligibility(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sivep_payload = _sivep_bytes()
    sivep_path = tmp_path / "INFLUD26.csv"
    sivep_path.write_bytes(sivep_payload)
    sivep = _source(acquire.SIVEP_SOURCE, payload=sivep_payload, relative_path="sivep/INFLUD26.csv")
    monkeypatch.setattr(prepare, "SIVEP_SOURCE", sivep)
    acquisition = tmp_path / "acquisition.json"
    acquisition.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "sources": [
                    _record(sivep, sivep_payload, rows=1),
                    {"key": "ibge", "status": "unavailable"},
                ],
            }
        ),
        encoding="utf-8",
    )
    published = prepare.prepare_snapshot(
        acquisition_path=acquisition,
        sivep_csv=sivep_path,
        ibge_ods=None,
        output_root=tmp_path / "snapshots",
        snapshot_id="official-fixture",
        as_of=dt.date(2026, 7, 26),
        generated_at=dt.datetime(2026, 7, 27, tzinfo=dt.UTC),
    )
    evidence = json.loads((published / "official-preparation.json").read_text())
    provenance_path = published / "official-provenance.json"
    provenance_bytes = provenance_path.read_bytes()
    provenance = json.loads(provenance_bytes)
    provenance_sidecar = (
        (published / "official-provenance.json.sha256").read_text(encoding="ascii").strip()
    )
    manifest = json.loads((published / "manifest.json").read_text())
    assert evidence["golden_eligible"] is False
    assert evidence["metric_states"] == {
        "case_growth": "available",
        "mortality_per_100k": "unavailable",
        "hospital_cfr": "available",
        "icu_pressure": "unavailable",
        "icu_use": "available",
        "influenza_coverage": "unavailable",
    }
    assert manifest["quality_state"] == "warning"
    assert manifest["table_counts"]["ibge_population"] == 0
    assert manifest["table_counts"]["cnes_icu_beds"] == 0
    assert manifest["table_counts"]["pni_observations"] == 0
    assert "content_sha256" not in provenance
    assert hashlib.sha256(provenance_bytes).hexdigest() == provenance_sidecar
    assert evidence["official_provenance_sha256"] == provenance_sidecar
    assert evidence["official_provenance_result"] == provenance["result"]
    for output in (evidence, provenance):
        serialized = json.dumps(output)
        assert "notification_key" not in serialized
        assert "digitization_date" not in serialized
        assert "fixture-1" not in serialized
        assert str(tmp_path) not in serialized


def test_prepare_ignores_supplied_ibge_path_when_sidecar_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sivep_payload = _sivep_bytes()
    sivep_path = tmp_path / "INFLUD26.csv"
    sivep_path.write_bytes(sivep_payload)
    sivep = _source(acquire.SIVEP_SOURCE, payload=sivep_payload, relative_path="sivep/INFLUD26.csv")
    monkeypatch.setattr(prepare, "SIVEP_SOURCE", sivep)
    acquisition = tmp_path / "acquisition.json"
    acquisition.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "sources": [
                    _record(sivep, sivep_payload, rows=1),
                    {"key": "ibge", "status": "unavailable"},
                ],
            }
        ),
        encoding="utf-8",
    )

    published = prepare.prepare_snapshot(
        acquisition_path=acquisition,
        sivep_csv=sivep_path,
        ibge_ods=tmp_path / "unavailable-population.ods",
        output_root=tmp_path / "snapshots",
        snapshot_id="ibge-sidecar-unavailable",
        as_of=dt.date(2026, 7, 26),
        generated_at=dt.datetime(2026, 7, 27, tzinfo=dt.UTC),
    )

    evidence = json.loads((published / "official-preparation.json").read_text())
    manifest = json.loads((published / "manifest.json").read_text())
    assert evidence["source_status"]["sivep"] == "verified"
    assert evidence["source_status"]["ibge"] == "unavailable"
    assert evidence["metric_states"]["mortality_per_100k"] == "unavailable"
    assert manifest["table_counts"]["ibge_population"] == 0
    assert evidence["golden_eligible"] is False
    assert "ibge_source_unavailable" in evidence["golden_ineligibility_reasons"]


def test_prepare_rejects_hash_mismatch_without_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _source(acquire.SIVEP_SOURCE, payload=_sivep_bytes(), relative_path="sivep.csv")
    monkeypatch.setattr(prepare, "SIVEP_SOURCE", source)
    csv_path = tmp_path / "sivep.csv"
    csv_path.write_bytes(b"changed")
    acquisition = tmp_path / "acquisition.json"
    acquisition.write_text(
        json.dumps({"schema_version": "1.0", "sources": [_record(source, _sivep_bytes(), rows=1)]}),
        encoding="utf-8",
    )
    with pytest.raises(prepare.PreparationError, match="sivep_hash_mismatch"):
        prepare.prepare_snapshot(
            acquisition_path=acquisition,
            sivep_csv=csv_path,
            ibge_ods=None,
            output_root=tmp_path / "snapshots",
            snapshot_id="bad",
            as_of=dt.date(2026, 7, 26),
        )


def test_prepare_with_independently_attested_ibge_ods(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sivep_payload = _sivep_bytes()
    sivep_path = tmp_path / "sivep.csv"
    sivep_path.write_bytes(sivep_payload)
    ods_path = tmp_path / "population.ods"
    _official_ibge_ods(ods_path)
    sivep = _source(acquire.SIVEP_SOURCE, payload=sivep_payload, relative_path="sivep.csv")
    ibge = _source(
        acquire.IBGE_SOURCE, payload=ods_path.read_bytes(), relative_path="population.ods"
    )
    monkeypatch.setattr(prepare, "SIVEP_SOURCE", sivep)
    monkeypatch.setattr(prepare, "IBGE_SOURCE", ibge)
    acquisition = tmp_path / "acquisition.json"
    ibge_payload = ods_path.read_bytes()
    ibge_record = _record(ibge, ibge_payload, rows=prepare._data_rows(ods_path, ibge))
    acquisition.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "sources": [_record(sivep, sivep_payload, rows=1), ibge_record],
            }
        ),
        encoding="utf-8",
    )
    published = prepare.prepare_snapshot(
        acquisition_path=acquisition,
        sivep_csv=sivep_path,
        ibge_ods=ods_path,
        output_root=tmp_path / "snapshots",
        snapshot_id="with-ibge",
        as_of=dt.date(2026, 7, 26),
        generated_at=dt.datetime(2026, 7, 27, tzinfo=dt.UTC),
    )
    evidence = json.loads((published / "official-preparation.json").read_text())
    manifest = json.loads((published / "manifest.json").read_text())
    assert evidence["source_status"]["ibge"] == "verified"
    assert evidence["metric_states"]["mortality_per_100k"] == "available"
    assert manifest["table_counts"]["ibge_population"] == 1
    assert manifest["source_files"][1]["data_rows"] == ibge_record["data_rows"]


def test_prepare_with_official_ibge_title_row_uses_second_row_as_header(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sivep_payload = _sivep_bytes()
    sivep_path = tmp_path / "sivep.csv"
    sivep_path.write_bytes(sivep_payload)
    ods_path = tmp_path / "POP2025_20260113.ods"
    _official_ibge_ods(ods_path)
    sivep = _source(acquire.SIVEP_SOURCE, payload=sivep_payload, relative_path="sivep.csv")
    ibge = _source(
        acquire.IBGE_SOURCE, payload=ods_path.read_bytes(), relative_path="POP2025_20260113.ods"
    )
    monkeypatch.setattr(prepare, "SIVEP_SOURCE", sivep)
    monkeypatch.setattr(prepare, "IBGE_SOURCE", ibge)
    ibge_payload = ods_path.read_bytes()
    acquisition = tmp_path / "acquisition.json"
    acquisition.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "sources": [
                    _record(sivep, sivep_payload, rows=1),
                    _record(ibge, ibge_payload, rows=prepare._data_rows(ods_path, ibge)),
                ],
            }
        ),
        encoding="utf-8",
    )

    published = prepare.prepare_snapshot(
        acquisition_path=acquisition,
        sivep_csv=sivep_path,
        ibge_ods=ods_path,
        output_root=tmp_path / "snapshots",
        snapshot_id="official-ibge-layout",
        as_of=dt.date(2026, 7, 26),
        generated_at=dt.datetime(2026, 7, 27, tzinfo=dt.UTC),
    )

    manifest = json.loads((published / "manifest.json").read_text())
    assert manifest["table_counts"]["ibge_population"] == 1


@pytest.mark.parametrize(
    "field, replacement",
    [
        ("identifier", "tampered.csv"),
        ("official_landing_url", "https://tampered.test/landing"),
        ("official_resource_url", "https://tampered.test/file.csv"),
        ("license_reuse_statement", "tampered"),
        ("license_evidence_url", "https://tampered.test/license"),
        ("dictionary_version", "tampered"),
        ("selected_column_mapping", {}),
        ("watermark", "1900-01-01"),
        ("encoding", "latin-1"),
        ("expected_sha256", "0" * 64),
        ("expected_size_bytes", 0),
        ("expected_data_rows", 0),
    ],
)
def test_prepare_rejects_tampered_immutable_sidecar_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, replacement: object
) -> None:
    payload = _sivep_bytes()
    source = _source(acquire.SIVEP_SOURCE, payload=payload, relative_path="sivep.csv")
    monkeypatch.setattr(prepare, "SIVEP_SOURCE", source)
    csv_path = tmp_path / "sivep.csv"
    csv_path.write_bytes(payload)
    record = _record(source, payload, rows=1)
    record[field] = replacement
    acquisition = tmp_path / "acquisition.json"
    acquisition.write_text(
        json.dumps({"schema_version": "1.0", "sources": [record]}), encoding="utf-8"
    )
    with pytest.raises(prepare.PreparationError, match="sivep_immutable_metadata_mismatch"):
        prepare.prepare_snapshot(
            acquisition_path=acquisition,
            sivep_csv=csv_path,
            ibge_ods=None,
            output_root=tmp_path / "snapshots",
            snapshot_id="tampered",
            as_of=dt.date(2026, 7, 26),
        )


def test_raw_inputs_and_snapshots_are_ignored_and_untracked() -> None:
    root = Path(__file__).parents[1]
    tracked = subprocess.run(
        ["git", "ls-files", "data/raw", "data/snapshots"],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )
    assert tracked.stdout == ""
    for path in ("data/raw/probe.csv", "data/snapshots/probe.duckdb"):
        ignored = subprocess.run(["git", "check-ignore", "-q", path], cwd=root).returncode
        untracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", path], cwd=root
        ).returncode
        assert ignored == 0
        assert untracked != 0
