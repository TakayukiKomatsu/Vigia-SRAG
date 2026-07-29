> Version: 2.2
> Date: 2026-07-29
> Document Status: DRAFT
> Release Status: EXTERNAL-BLOCKED

# Relatório epidemiológico de SRAG — Brasil

PoC em Python 3.12 que prepara um snapshot DuckDB minimizado, calcula métricas agregadas e publica um relatório HTML fundamentado. Registros clínicos, identificadores, SQL livre, payloads de notícia e segredos não cruzam a fronteira do agente.

## Estado reproduzido

Em 2026-07-29, a aquisição oficial verificou SIVEP (177.445 linhas; SHA-256 `5b1de50c…359fb`) e IBGE (37 linhas de origem; SHA-256 `33dc6f79…a1b5`). CNES e PNI não estavam disponíveis. A preparação oficial é, portanto, `warning/ineligible`, não um bundle golden nem uma referência epidemiológica completa.

O live run `official-20260727-openrouter-20260729` pediu `openrouter/free` e registrou como servido `nvidia/nemotron-3-super-120b-a12b:free`; RSS aceitou um item G1; três claims passaram a validação local e `fallback_used` foi `false`. Mesmo assim, o gate foi intencionalmente inelegível: `degraded_or_fallback`, `incomplete_artifact_set`, `metric_unavailable:influenza_coverage`, `metric_quality_not_available:influenza_coverage`, `metric_unavailable:icu_pressure`, `metric_quality_not_available:icu_pressure`, `monthly_series_incomplete`, `chart_set_incomplete` e `audit_node_order_invalid`.

`icu_use` é a proporção de casos SRAG hospitalizados com uso de UTI — não ocupação nacional de leitos. `icu_pressure` permanece indisponível sem CNES. A cobertura de influenza permanece indisponível sem publicação oficial PNI. Esta PoC não fornece diagnóstico, previsão ou recomendação clínica.

## Instalação e execução

```bash
uv sync --extra dev
uv run srag-report demo
```

Use `.env` somente para uma execução live e carregue-o explicitamente:

```bash
uv run --env-file .env srag-report live \
  --snapshot data/snapshots/official-20260727/analytics.duckdb \
  --snapshot-id official-20260727 \
  --provider openrouter \
  --model openrouter/free \
  --as-of 2026-07-26 \
  --run-id official-20260727-openrouter-20260729
```

O alias solicitado `openrouter/free` é roteado pelo provedor e pode servir modelos diferentes; o manifesto registra ambos, solicitado e servido. Falhas de comentários usam códigos neutros ao provedor (`model_provider_unavailable`, `model_output_invalid` ou `commentary_rejected`) e produzem fallback factual degradado, nunca uma alegação de sucesso do provedor.

Para reproduzir a evidência oficial, a aquisição (único passo com download de fonte) e a preparação offline são:

```bash
uv run python scripts/acquire_official_sources.py --output-root data/raw --blocked-root runs
uv run python scripts/prepare_official_snapshot.py \
  --acquisition data/raw/acquisition.json \
  --sivep-csv data/raw/sivep/INFLUD26-27-07-2026.csv \
  --ibge-ods data/raw/ibge/POP2025_20260113.ods \
  --output-root data/snapshots \
  --snapshot-id official-20260727 \
  --as-of 2026-07-26
```

As entradas brutas, snapshots e bundles de execução continuam ignorados; não os adicione ao repositório.

## Limites de segurança e governança

O RSS é limitado a HTTP(S), portas 80/443, hosts/endereços globais permitidos, DNS fixado por requisição, redirects revalidados, corpo máximo de 1 MiB e XML/atributos limitados. Títulos, URLs de artigo e IDs de notícia são excluídos da visão minimizada enviada ao LLM; o item RSS serve apenas para contexto sanitizado do relatório.

O `AuditSink` grava JSONL append-only antes de ações críticas. O gate interno confere consistência do bundle e evidência de execução (hashes, transições, modelos, publicação e limites); ele não prova autenticidade criptográfica contra quem possa reescrever o bundle inteiro.

```bash
uv run srag-report gate runs/<run-id>
```

Elegibilidade requer execução live sem degradação/fallback, métricas e séries/gráficos completos, notícia válida, claims validadas, auditoria ordenada e conjunto exato de artefatos. O código de saída é `2` para candidato inelegível.

## Arquitetura e entrega

O diagrama de uma página A4 paisagem está em `docs/architecture.html` e `docs/architecture.pdf`. Os exemplos sanitizados são `examples/live-smoke-result.json` e `examples/official-source-run.json`; não contêm linhas brutas, segredos, caminhos absolutos ou texto restrito.

A publicação pública e a verificação de clone anônimo são ações exclusivas do owner. Enquanto URL pública, SHA publicada e clone sem autenticação não forem reproduzidos, o release permanece `EXTERNAL-BLOCKED`.
