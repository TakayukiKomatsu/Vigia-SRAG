"""
Format decoders for SRAG source file ingestion.

Each decoder is isolated so callers import by name and optional heavy
dependencies (DBC blast decompressor) are guarded by ImportError only at
call time, not at module import time.

Public API:
    iter_csv_rows(path, encoding)     → Iterator[dict[str, str]]
    iter_dbf_rows(path)               → Iterator[dict[str, Any]]
    iter_ods_rows(path, sheet_index)  → Iterator[dict[str, Any]]
    decode_dbc_to_rows(path)          → Iterator[dict[str, Any]]   # optional dep
"""

from __future__ import annotations

import csv
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# CSV — stdlib only
# ---------------------------------------------------------------------------


def iter_csv_rows(
    path: Path,
    encoding: str = "utf-8",
    delimiter: str = ";",
) -> Iterator[dict[str, str]]:
    """Stream source CSV rows without materialising the file."""
    with path.open(newline="", encoding=encoding) as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path}")
        for row in reader:
            yield dict(row)


# ---------------------------------------------------------------------------
# DBF — requires dbfread
# ---------------------------------------------------------------------------


def iter_dbf_rows(path: Path) -> Iterator[dict[str, Any]]:
    """
    Stream rows from a dBASE III/IV DBF file as dicts.

    Requires dbfread (pure-Python):  pip install dbfread>=2.0.7
    """
    try:
        import dbfread  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError(
            "dbfread is required to read DBF files.\n" "Install with:  pip install dbfread>=2.0.7"
        ) from exc

    for record in dbfread.DBF(str(path), raw=False):
        yield dict(record)


# ---------------------------------------------------------------------------
# ODS — requires odfpy
# ---------------------------------------------------------------------------


def iter_ods_rows(
    path: Path,
    sheet_index: int = 0,
    *,
    header_row_index: int = 0,
) -> Iterator[dict[str, Any]]:
    """
    Stream data rows from an ODS spreadsheet as dicts keyed by column header.

    Headers are taken from the row at ``header_row_index`` (default 0).
    Empty rows (all cells blank) are silently skipped.

    Requires odfpy (pure-Python):  pip install odfpy>=1.4.1
    """
    try:
        from odf import opendocument, table, teletype  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError(
            "odfpy is required to read ODS files. Install with: pip install odfpy==1.4.1"
        ) from exc

    document = opendocument.load(str(path))
    sheets = document.spreadsheet.getElementsByType(table.Table)
    if not 0 <= sheet_index < len(sheets):
        raise ValueError(
            f"Sheet index {sheet_index} is out of range " f"(document has {len(sheets)} sheet(s))"
        )

    def expanded_rows() -> Iterator[list[str]]:
        for row in sheets[sheet_index].getElementsByType(table.TableRow):
            values: list[str] = []
            for cell in row.getElementsByType(table.TableCell):
                repeat = int(cell.getAttribute("numbercolumnsrepeated") or 1)
                value = teletype.extractText(cell).strip()
                values.extend([value] * repeat)
            row_repeat = int(row.getAttribute("numberrowsrepeated") or 1)
            for _ in range(row_repeat):
                yield values

    rows = expanded_rows()
    headers: list[str] | None = None
    for row_index, values in enumerate(rows):
        if row_index < header_row_index:
            continue
        if row_index == header_row_index:
            headers = values
            if not any(headers):
                raise ValueError(f"ODS header row {header_row_index} is empty")
            continue
        if headers is None:
            raise ValueError("ODS header row was not found")
        if not any(values):
            continue
        padded = values + [""] * max(0, len(headers) - len(values))
        yield dict(zip(headers, padded[: len(headers)], strict=True))


# ---------------------------------------------------------------------------
# DBC (DATASUS compressed DBF) — optional; isolated behind this function only
# ---------------------------------------------------------------------------


def decode_dbc_to_rows(path: Path) -> Iterator[dict[str, Any]]:
    """Decompress a DATASUS DBC file and stream its DBF rows."""
    try:
        import datasus_dbc
    except ImportError as exc:
        raise ImportError(
            "datasus-dbc is required to read DBC files. "
            "Install with: pip install datasus-dbc==0.1.3"
        ) from exc

    with tempfile.TemporaryDirectory(prefix="srag-dbc-") as directory:
        dbf_path = Path(directory) / f"{path.stem}.dbf"
        dbf_path.write_bytes(datasus_dbc.decompress_bytes(path.read_bytes()))
        yield from iter_dbf_rows(dbf_path)
