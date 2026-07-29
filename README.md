# Relatório epidemiológico de SRAG — Brasil

PoC reprodutível em Python 3.12 para preparar snapshots públicos minimizados, calcular métricas epidemiológicas, renderizar gráficos determinísticos e orquestrar um relatório HTML fundamentado. O agente recebe apenas agregados validados; registros clínicos, identificadores e SQL arbitrário não atravessam essa fronteira.

## Estado e limites

- SIVEP-Gripe 2025/2026, CNES 202606 e população IBGE 2025 possuem contratos locais verificados.
- A observação PNI 2026 disponível nesta PoC cobre somente `NE/CO/S/SE`; ela é exibida como suplemento limitado, nunca como dado nacional.
- O quickstart determinístico usa dados sintéticos, comentário fake/fallback e notícia fixa. Não representa vigilância ao vivo.
- O modo live requer um snapshot DuckDB local já verificado. Aquisição de fontes e evidências estão descritas em `.agent/specs/01-data-foundation/source-contracts.md`.
- Ainda não há bundle de referência baseado integralmente em fontes oficiais nem URL pública de release. O gate permanece fail-closed para métricas ausentes, escopo não nacional nas outras cinco métricas, degradação e artefatos inválidos.
- A PoC não oferece diagnóstico, previsão ou recomendação clínica.

## Instalação

Requer Python 3.12 e [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync --extra dev
```

As dependências de runtime estão fixadas em `pyproject.toml`/`uv.lock`. Copie `.env.example` somente para o modo live; nunca versione `.env`.

## Quickstart determinístico, sem credencial ou rede

```bash
uv run srag-report demo
```

O comando cria `data/snapshots/demo.duckdb` e `runs/demo-20260728/`. Ele não chama provedor de modelo nem RSS e marca o HTML como `demonstração não-live`. Um `run_id` é imutável; para outra execução, escolha outro identificador:

```bash
uv run srag-report demo --run-id demo-2
```

Inspeção:

```bash
open runs/demo-20260728/report.html
cat runs/demo-20260728/evidence.json
cat runs/demo-20260728/manifest.json
```

## Execução live

O provedor padrão é OpenRouter e requer `OPEN_ROUTER_API_KEY`; OpenAI permanece disponível com `--provider openai` e `OPENAI_API_KEY`. O snapshot publicado, seu `manifest.json` adjacente e seu ID são argumentos explícitos e verificados; o processo consulta o Google News RSS no momento da execução.

```bash
export OPEN_ROUTER_API_KEY='...'
uv run srag-report live \
  --snapshot data/snapshots/<snapshot-id>/analytics.duckdb \
  --snapshot-id <snapshot-id> \
  --provider openrouter \
  --model openrouter/free \
  --as-of 2026-07-28 \
  --run-id live-20260728
```

O OpenRouter reutiliza o cliente Python `openai` pela API compatível de Chat Completions, sem runtime adicional. O modelo padrão é `openrouter/free`; `--model` permite fixar outro modelo OpenRouter. Para OpenAI explícito, use `--provider openai --model gpt-5.6`. `manifest.json` registra provedor indiretamente pelos modelos solicitado/servido, modo, fallback, claims e hashes. Falha do provedor após uma repetição permitida produz comentário determinístico e torna a execução degradada. Notícia ausente degrada para relatório quantitativo. Falha de auditoria, snapshot, gráfico, renderer ou publicação interrompe a execução.

O último smoke sanitizado fica em `examples/live-smoke-result.json`. OpenRouter respondeu via `openrouter/free`, o modelo servido foi registrado, três claims passaram schema e grounding, o relatório live completo foi publicado e o gate estrito passou sobre a fixture sintética permitida. Esse resultado valida a integração, mas não é promovido a referência epidemiológica oficial.

## Golden gate estrito

```bash
uv run srag-report gate runs/<run-id>
```

Saída elegível exige: modo live sem degradação/fallback; seis métricas disponíveis e com qualidade `available`, sendo que somente a cobertura PNI de influenza pode ter `population_scope` regional explícito; as outras cinco métricas devem ser nacionais e sem escopo; séries/gráficos completos de 30 dias e 12 meses; notícia válida dos últimos 14 dias; claims estruturadas do provedor aprovado e revalidadas; evento crítico de publicação; conjunto exato de artefatos e hashes íntegros. O processo retorna código `2` quando o candidato não é elegível. PNI regional nunca é rotulada como nacional.

## Arquitetura

```text
SIVEP + CNES + IBGE + PNI
          │ contratos, normalização, minimização e qualidade
          ▼
   snapshot DuckDB somente leitura
          │ tools agregadas e tipadas
          ├── MetricsTool ──► seis resultados + séries 30d/12m
          ├── ChartsTool  ──► SVG determinístico
Google News RSS ──► NewsTool com query/locale/janela/allowlist fixos
          │
          ▼
 LangGraph de dez nós ──► EvidenceBundle imutável
          │                │
          │                └── OpenRouter/OpenAI structured output ou fallback
          ▼
 validador de claims ──► renderer HTML sanitizado
          │
          └── AuditSink síncrono ──► run bundle publicado por rename atômico
```

O diagrama conceitual imprimível está em `docs/architecture.html`; o PDF de release é `docs/architecture.pdf`.

### Fluxo LangGraph fixo

1. `validate_request`
2. `select_snapshot`
3. `collect_metrics`
4. `render_charts`
5. `search_news`
6. `validate_evidence`
7. `generate_commentary`
8. `validate_commentary`
9. `render_report`
10. `finalize_run`

Não há roteamento livre. `MetricsTool` aceita somente um `ReportRequest` e retorna pacote agregado; não expõe SQL/tabela/coluna/linha. `ChartsTool` aceita somente séries validadas. `NewsTool` usa a query fixa `("SRAG" OR "síndrome respiratória aguda grave") when:14d`, locale Brasil/português, no máximo cinco itens, redirects validados e allowlist de fontes/domínios.

## Métricas, períodos e qualidade

| Resultado | Definição resumida | Período |
|---|---|---|
| Aumento de casos | `(casos_ref - casos_ant) / casos_ant × 100`; `stable_zero` para 0/0; `new_activity` para anterior 0 e atual > 0 | duas semanas epidemiológicas completas; referência encerra sábado ≥14 dias antes de `as_of` |
| Mortalidade/100 mil | óbitos por SRAG / população IBGE × 100.000 | quatro semanas epidemiológicas estabilizadas mais recentes |
| Pressão UTI | paciente-dias SRAG em UTI / (leitos UTI CNES × dias) × 100 | mês completo anterior; valor impossível >100% é bloqueado |
| Cobertura influenza | numerador/denominador oficial PNI | campanha 2026 publicada até `as_of`; escopo explícito |
| Letalidade hospitalar | óbitos SRAG / (óbitos SRAG + curas) × 100 | coorte hospitalar madura de quatro semanas; encerra ≥28 dias antes de `as_of` |
| Uso de UTI | hospitalizações SRAG com UTI / hospitalizações elegíveis × 100 | mesma coorte madura |

As séries têm exatamente 30 datas diárias consecutivas terminando em `as_of` e 12 meses-calendário completos anteriores ao mês de `as_of`; dias/meses sem casos recebem zero. Cada objeto carrega fórmula versionada, período, snapshot, fontes, watermark, numerador/denominador quando aplicável, qualidade e limitações.

Qualidade por completude: `available` ≥90%, `warning` ≥70% e <90%, `unavailable` <70%; bloqueadores estruturais prevalecem. Métricas indisponíveis mostram motivo, nunca zero inventado.

## Grounding, guardrails e privacidade

O `EvidenceBundle` contém somente métricas, séries, gráficos, notícias permitidas, fontes, watermarks e qualidade. OpenRouter e OpenAI usam saída estruturada validada por Pydantic. Toda claim deve citar IDs existentes; números precisam existir nas evidências citadas. O validador rejeita URL inventada, linguagem causal/clínica, instruções oriundas de notícia e prompt injection. Títulos e claims são escapados no HTML.

URLs RSS aceitam apenas HTTP(S), portas 80/443, destinos globais, redirects inspecionados e fontes/domínios permitidos. O bundle não contém `notification_key`, campos SIVEP brutos, payload de notícia, corpo de artigo, segredo ou linha clínica.

`AuditSink` grava JSONL append-only com flush/fsync antes do provedor de modelo e da publicação. Eventos guardam transições, decisões, duração, modelo e hashes, nunca chave ou payload bruto. Se um evento crítico não persistir, não há publicação.

## Run bundle

Cada `runs/<run_id>/` publicado contém:

```text
request.json
evidence.json
audit.jsonl
charts/daily-cases.svg
charts/monthly-cases.svg
report.html
manifest.json
```

Arquivos são preparados em diretório candidato, validados, hasheados e movidos atomicamente. Um `run_id` existente nunca é sobrescrito. `manifest.json` é o ponto de entrada para modo, modelos, degradações, claims e hashes.

Um bundle completo não-live, seguro para versionamento, está em
`examples/deterministic-run/`. Abra `examples/deterministic-run/report.html` e use
`manifest.json` para verificar os hashes; ele é evidência do quickstart, não um golden live.

## Desenvolvimento e verificação

```bash
uv run pytest
uv run ruff check .
uv run mypy src
```

A suíte separa contratos, normalização, DuckDB, fórmulas/períodos, gráficos, RSS, grounding, grafo, degradação, segurança, CLI e golden gate. O CI também executa Gitleaks. `.gitignore` exclui `.env`, dados brutos, snapshots, runs locais, estado de agentes e o documento restrito do desafio.

Resultados medidos de ingestão (165.000 linhas) e do pacote analítico completo estão em
`examples/benchmark-result.json`, com tempo, memória e contexto da máquina.

A fonte de verdade funcional está em `.agent/specs/`; os quatro SDDs continuam `DRAFT` enquanto os contratos oficiais ainda marcados `UNVERIFIED`, o bundle de referência oficial e a publicação pública não forem comprovados. O smoke OpenRouter e o gate estrito sobre fixture permitida já foram reproduzidos.
