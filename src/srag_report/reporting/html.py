from __future__ import annotations

import datetime as dt
import hashlib
import html
import os
import tempfile
from pathlib import Path
from typing import Literal

from ..agent.models import CommentaryResult, EvidenceBundle
from ..metrics.models import MetricResult


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _metric_card(metric: MetricResult) -> str:
    value = metric.value
    state = metric.state
    if value is None:
        reason = metric.reason.value if metric.reason is not None else state.value
        rendered_value = f"Indisponível: {_escape(reason)}"
    else:
        rendered_value = f"{value:g} {_escape(metric.unit)}"
    scope = metric.population_scope
    scope_html = ""
    if scope:
        scope_html = (
            '<p class="limited"><strong>Escopo limitado:</strong> '
            + _escape(", ".join(sorted(scope)))
            + ". Não representa Brasil inteiro.</p>"
        )
    limitations = "".join(f"<li>{_escape(item)}</li>" for item in metric.limitations)
    return f"""
    <article class="metric" data-metric-id="{_escape(metric.metric_id.value)}">
      <h3>{_escape(metric.label)}</h3>
      <p class="value">{rendered_value}</p>
      <p>Período: {_escape(metric.period_start)} a {_escape(metric.period_end)}</p>
      <p>Estado: {_escape(state.value)} | Qualidade: {_escape(metric.quality.state.value)}</p>
      {scope_html}<ul>{limitations}</ul>
    </article>"""


def render_report_html(
    evidence: EvidenceBundle,
    commentary: CommentaryResult,
    *,
    generated_at: dt.datetime,
    output_path: Path,
    execution_mode: Literal["deterministic", "live"],
) -> str:
    if generated_at.utcoffset() != dt.timedelta(0):
        raise ValueError("generated_at must be timezone-aware UTC")
    metrics = "".join(_metric_card(metric) for metric in evidence.metrics)
    charts = "".join(
        f"<figure><img src=\"{_escape(chart.path)}\" alt=\"{_escape(chart.alt_text)}\">"
        f"<figcaption>{_escape(chart.title)} — {_escape(chart.period)}. "
        f"Fonte: {_escape(', '.join(chart.source_ids))}; watermark: {_escape(chart.watermark)}."
        "</figcaption></figure>"
        for chart in evidence.charts
    )
    news = (
        "".join(
            f'<li><a href="{_escape(item.final_url)}" rel="noopener noreferrer">'
            f"{_escape(item.title)}</a> — {_escape(item.source)}, "
            f"{_escape(item.published_at.date())}</li>"
            for item in evidence.news
        )
        or "<li>Nenhuma notícia válida na janela; relatório quantitativo degradado.</li>"
    )
    claims = "".join(
        f"<li>{_escape(claim.text)} <small>[{_escape(', '.join(claim.evidence_ids))}]</small></li>"
        for claim in commentary.claims
    )
    methods = "".join(
        f"<li>{_escape(metric.metric_id.value)}: {_escape(metric.formula_version.value)}; "
        f"fontes {_escape(', '.join(metric.source_ids))}</li>"
        for metric in evidence.metrics
    )
    watermarks = "".join(
        f"<li>{_escape(source)}: {_escape(value)}</li>"
        for source, value in sorted(evidence.watermarks.items())
    )
    fallback = ""
    if commentary.fallback_used:
        fallback = (
            '<p class="limited">Comentário factual determinístico usado após '
            "falha/rejeição do provedor de comentários.</p>"
        )
    document = f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Relatório Brasil de SRAG — {_escape(evidence.request.as_of)}</title>
<style>
body{{
  font-family:system-ui,sans-serif;max-width:1120px;margin:auto;
  padding:2rem;color:#18212b
}}
header{{border-bottom:4px solid #0072b2}}
.grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:1rem}}
.metric,figure,section{{border:1px solid #ccd5df;border-radius:.4rem;padding:1rem}}
.value{{font-size:1.5rem;font-weight:700}}
.limited{{background:#fff3cd;border-left:4px solid #e69f00;padding:.6rem}}
img{{max-width:100%;height:auto}}
a{{color:#005ea8}}
@media(max-width:720px){{.grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<header><h1>Relatório epidemiológico de SRAG — Brasil</h1>
<p><strong>Modo: {_escape(execution_mode)}</strong>
({"execução live" if execution_mode == "live" else "demonstração não-live"}).</p>
<p>generated_at: {_escape(generated_at.isoformat())} |
as_of: {_escape(evidence.request.as_of)} |
run_id: {_escape(evidence.request.run_id)}</p></header>
<main>
<section><h2>Métricas e indicadores</h2><div class="grid">{metrics}</div></section>
<section><h2>Séries e gráficos</h2>{charts}</section>
<section><h2>Notícias recentes validadas</h2><ul>{news}</ul></section>
<section><h2>Comentário fundamentado</h2>{fallback}<ul>{claims}</ul>
<p>Modelo solicitado: {_escape(commentary.requested_model)};
servido: {_escape(commentary.served_model)}.</p></section>
<section><h2>Qualidade, métodos e fontes</h2><h3>Watermarks</h3><ul>{watermarks}</ul>
<h3>Métodos</h3><ul>{methods}</ul><p>Fontes: {_escape(', '.join(evidence.sources))}.</p>
<p>Este relatório demonstra uma PoC de dados públicos. Não oferece diagnóstico,
previsão ou recomendação clínica.</p></section>
</main></body></html>"""
    payload = document.encode()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.", dir=output_path.parent
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        temporary_path.write_bytes(payload)
        os.replace(temporary_path, output_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return hashlib.sha256(payload).hexdigest()
