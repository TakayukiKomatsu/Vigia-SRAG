from __future__ import annotations

import datetime as dt
from decimal import Decimal
from pathlib import Path
from typing import Literal

from .data.store import materialize_snapshot
from .domain.models import CnesCanonicalRow, IbgePopulationRow, PniObservation, SivepCanonicalRow
from .domain.source import SivepEvolutionCode, SivepYesNoCode

_DEMO_SHA256 = "0" * 64
_DEMO_AS_OF = dt.date(2026, 7, 28)


def build_demo_snapshot(path: Path, *, as_of: dt.date = _DEMO_AS_OF) -> Path:
    """Build a synthetic, non-live snapshot with complete metric time windows."""
    start = as_of - dt.timedelta(days=400)
    sivep_rows: list[SivepCanonicalRow] = []
    for index in range(401):
        onset = start + dt.timedelta(days=index)
        if onset.year not in {2025, 2026}:
            raise ValueError("demo supports only as_of dates whose 400-day window is 2025/2026")
        year: Literal[2025, 2026] = 2025 if onset.year == 2025 else 2026
        death = index % 11 == 0
        evolution = SivepEvolutionCode.DEATH_SRAG if death else SivepEvolutionCode.CURE
        sivep_rows.append(
            SivepCanonicalRow(
                year=year,
                source_sha256=_DEMO_SHA256,
                notification_key=f"DEMO-{onset:%Y%m%d}-{index:06d}",
                notification_date=onset,
                symptom_onset=onset,
                hospitalization_flag=SivepYesNoCode.YES,
                hospitalization_date=onset,
                hospitalization_uf="SP",
                icu_flag=SivepYesNoCode.YES if index % 3 == 0 else SivepYesNoCode.NO,
                icu_entry_date=onset if index % 3 == 0 else None,
                icu_exit_date=(onset + dt.timedelta(days=2)) if index % 3 == 0 else None,
                evolution=evolution,
                evolution_date=onset + dt.timedelta(days=7),
                closure_date=onset + dt.timedelta(days=8),
                digitization_date=dt.datetime.combine(onset, dt.time(12), tzinfo=dt.UTC),
                residence_uf="SP",
            )
        )

    artifact = materialize_snapshot(
        path,
        sivep_rows=sivep_rows,
        cnes_rows=(
            CnesCanonicalRow(
                competencia=202606,
                uf="SP",
                cod_leito=61,
                qt_exist=100,
                source_sha256=_DEMO_SHA256,
            ),
        ),
        ibge_rows=(
            IbgePopulationRow(
                year=2025,
                geography="BR",
                population_official=213_421_037,
                reference_date=dt.date(2025, 7, 1),
                source_sha256=_DEMO_SHA256,
            ),
        ),
        pni_rows=(
            PniObservation(
                campaign_year=2026,
                immunobiological="INF3",
                population_scope=frozenset({"NE", "CO", "S", "SE"}),
                period_start=dt.date(2026, 3, 1),
                period_end=dt.date(2026, 5, 31),
                numerator=61_700,
                denominator=100_000,
                coverage_pct=Decimal("61.7"),
                published_at=dt.datetime(2026, 7, 27, 12, tzinfo=dt.UTC),
                source_label="synthetic-demo-pni",
                is_nationwide=False,
                is_golden=False,
            ),
        ),
    )
    return artifact.path
