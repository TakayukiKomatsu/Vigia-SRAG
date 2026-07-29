# Agente e relatório fundamentado de SRAG

> Status: DRAFT
> Tier: extended
> Version: 2.0
> Owner: Indicium HealthCare PoC
> Created: 2026-07-28
> Last Updated: 2026-07-28

## Summary

Orquestrar tools tipadas de métricas, gráficos e notícias em um LangGraph
controlado, gerar comentários estruturados pela API da OpenAI, validar todas
as claims e publicar relatório HTML com bundle de auditoria sanitizado.

## Problem

O desafio exige um agente que consulte banco e notícias ao vivo e explique o
cenário. Um agente livre pode executar consultas indevidas, obedecer conteúdo
jornalístico, inventar números/URLs ou exceder tempo e custo. Um pipeline sem
tools explícitas também não demonstra a arquitetura solicitada.

## Goals

- **FR-AR-1:** Validar request Brasil, `as_of`, snapshot, configuração e
  `run_id` antes das tools.
- **FR-AR-2:** Executar LangGraph fixo com rotas explícitas de sucesso,
  degradação e falha terminal.
- **FR-AR-3:** Expor tools tipadas de métricas e gráficos sem SQL, tabela,
  coluna ou registro arbitrário.
- **FR-AR-4:** Consultar Google News RSS ao vivo com query fixa, janela de 14
  dias, locale Brasil/português, allowlist e no máximo cinco itens.
- **FR-AR-5:** Congelar métricas, séries, gráficos, notícias e fontes agregadas
  validadas em um `EvidenceBundle` imutável.
- **FR-AR-6:** Usar um adaptador OpenAI para comentário estruturado vinculado
  a evidências e registrar o modelo exato configurado.
- **FR-AR-7:** Rejeitar IDs, números, citações, causalidade, diagnósticos,
  recomendações e instruções jornalísticas sem suporte.
- **FR-AR-8:** Renderizar HTML determinístico com métricas, suplementos,
  gráficos, contexto, métodos, fontes, watermarks, qualidade, limitações e
  `run_id`.
- **FR-AR-9:** Aplicar matriz de falhas inequívoca e fallback factual sem
  permitir que relatório degradado satisfaça o golden run.
- **FR-AR-10:** Ser dono de `AuditSink`, eventos JSONL, run bundle, limites e
  comportamento fail-closed para eventos críticos.

## Non-Functional Requirements

- **NFR-AR-1:** Texto do LLM não substitui valores, pontos de gráfico, datas ou
  URLs autoritativos.
- **NFR-AR-2:** Toda claim gerada referencia IDs existentes no
  `EvidenceBundle`.
- **NFR-AR-3:** Transições e fallback são determinísticos para a mesma
  evidência e respostas fake.
- **NFR-AR-4:** Falha de notícias ou OpenAI ainda produz relatório factual
  explicitamente degradado quando os componentes críticos permanecem válidos.
- **NFR-AR-5:** OpenAI, auditoria, evidência e relatório recebem somente
  agregados.
- **NFR-AR-6:** CI usa OpenAI fake e RSS fixo; smoke live é manual e
  identificado separadamente.

## Non-Goals

- geografia diferente de Brasil;
- SQL, URL de busca, prompt ou loop de tools arbitrários;
- busca web aberta ou leitura integral de artigos;
- múltiplos provedores de LLM;
- PDF do relatório;
- diagnóstico, recomendação clínica ou causalidade não sustentada.

## Package Architecture

```text
srag_report/
  config.py
  domain/
  data/
  metrics/
  tools/
  agent/
  reporting/
  audit/
  cli.py
```

- `domain`: requests, métricas, séries, evidências, claims e eventos, sem
  dependência de infraestrutura;
- `data`: contratos, limpeza, qualidade, manifestos e DuckDB;
- `metrics`: fórmulas e consultas determinísticas;
- `tools`: interfaces estreitas de métricas, gráficos e notícias;
- `agent`: estado/nós LangGraph, OpenAI e validação de comentário;
- `reporting`: gráficos, HTML e fallback factual;
- `audit`: `AuditSink` e implementação JSONL;
- `cli.py`: preparação, geração e inspeção por `run_id`.

## Graph

```text
validate_request
  -> select_snapshot
  -> collect_metrics
  -> render_charts
  -> search_news
  -> validate_evidence
  -> generate_commentary
  -> validate_commentary
  -> render_report
  -> finalize_run
```

O estado é tipado. Falhas seguem a matriz deste spec; o LLM não escolhe nós,
tools, retries nem término.

## Tool Contracts

### Metrics Tool

Aceita apenas `geography="BR"`, `as_of` e `snapshot_id`. Consulta DuckDB
somente leitura e retorna `MetricResult`/`SeriesResult` agregados.

### Charts Tool

Aceita somente séries validadas e retorna `ChartResult` com arquivo, hash,
metadados e descrição. Não aceita dados ou código livres.

### News Tool

Consulta `https://news.google.com/rss/search` durante a execução com:

- `hl=pt-BR`;
- `gl=BR`;
- `ceid=BR:pt-419`;
- query fixa `("SRAG" OR "síndrome respiratória aguda grave") when:14d`.

Allowlist inicial: Ministério da Saúde, Fiocruz, Agência Brasil, G1, Estadão e
Folha de S.Paulo. O item precisa de título, fonte, URL final HTTP(S), data de
publicação e coleta. Redirect é aceito somente se o destino final continuar
HTTP(S) e corresponder à allowlist por domínio ou `source`. Item sem data,
stale, duplicado, inválido ou fora da allowlist é descartado. O máximo é cinco.

Título e descrição são dados não confiáveis delimitados. Instruções presentes
neles não alteram o grafo, as tools, a política nem o prompt do sistema.

## Domain Interfaces

```text
ReportRequest:
  geography = "BR", as_of, snapshot_id, run_id

NewsItem:
  news_id, title, source, final_url, published_at, collected_at

EvidenceBundle:
  request, metrics, series, charts, news, sources, watermarks, quality

CommentaryClaim:
  claim_id, text, evidence_ids

AuditEvent:
  run_id, sequence, occurred_at, event_type, component, status,
  summary, evidence_ids, artifact_hashes, duration_ms
```

Tools usam esses contratos, não dicionários ou payloads arbitrários.

## OpenAI and Grounding

Existe um único adaptador da API da OpenAI. O modelo vem da configuração do
repositório e seu nome exato entra na auditoria. Este spec não recebe `FINAL`
antes de existir um modelo padrão que passe o smoke test de saída estruturada.
Testes automatizados usam fake determinístico.

A OpenAI recebe somente o `EvidenceBundle` agregado e devolve
`CommentaryClaim[]`. Cada `evidence_id` precisa existir. A resposta não fornece
URLs, não altera números renderizados e não controla gráficos.

O validador rejeita:

- evidência inexistente;
- número sem vínculo com o objeto correto;
- citação ou URL inventada;
- causalidade sem evidência;
- diagnóstico ou recomendação clínica;
- instrução originada em conteúdo jornalístico.

Falha ou rejeição gera texto factual determinístico.

## Runtime Limits

- uma chamada normal por tool;
- uma tentativa adicional somente para falha transitória de notícia ou OpenAI;
- no máximo cinco notícias;
- no máximo 1.200 tokens de saída OpenAI;
- timeout global de 120 segundos;
- janela de notícias fixa de 14 dias.

## Audit and Run Bundle

Cada execução cria:

```text
runs/<run_id>/
  request.json
  evidence.json
  audit.jsonl
  charts/
  report.html
  manifest.json
```

Eventos incluem transições, tool calls, entradas/saídas resumidas, guardrails,
evidências, versões, modelo, decisões, falhas, duração, URLs, hashes e
artefatos. `evidence.json` preserva exatamente os agregados usados para
validar o comentário.

Não são persistidos registros clínicos, chaves técnicas, segredos, payloads
brutos, corpo integral de notícia ou objeto fora da allowlist do evento. Falha
ao persistir evento crítico antes da OpenAI ou publicação interrompe a
execução.

## Failure Matrix

| Falha | Rota | Publica | Golden |
|---|---|---|---|
| request inválido ou `as_of` após watermark | termina antes das tools/OpenAI | não | não |
| snapshot, hash, schema ou evidência inválida | termina antes da OpenAI | não | não |
| métrica indisponível com motivo válido | seção explícita | sim, degradado | não |
| nenhuma notícia válida após retry permitido | relatório quantitativo com limitação | sim, degradado | não |
| OpenAI falha após retry ou claims são inválidas | comentário factual determinístico | sim, degradado | não |
| gráfico ou renderer falha | termina publicação | não | não |
| auditoria crítica falha | termina antes da OpenAI/publicação | não | não |
| timeout global antes de bundle publicável | termina e audita timeout | não | não |

## Report Contract

O HTML contém cabeçalho Brasil com `generated_at`, `as_of` e watermarks; quatro
métricas obrigatórias; letalidade e uso UTI suplementares; dois gráficos;
notícias aceitas; comentários validados ou fallback; qualidade, métodos,
fontes, limitações e `run_id`. Números, datas, URLs e gráficos vêm dos objetos
validados, nunca do texto livre.

## Acceptance Criteria

- **AC-AR-1 (FR-AR-1, FR-AR-2):** Requests válidos seguem os dez nós; requests
  inválidos terminam antes das tools.
- **AC-AR-2 (FR-AR-3):** Tools analíticas rejeitam interfaces arbitrárias e
  não retornam linhas.
- **AC-AR-3 (FR-AR-4):** RSS aplica query, locale, janela, allowlist, redirects,
  deduplicação e limite.
- **AC-AR-4 (FR-AR-4, FR-AR-7):** Conteúdo jornalístico não controla execução.
- **AC-AR-5 (FR-AR-5, NFR-AR-5):** Evidência e payload OpenAI contêm somente
  agregados e IDs.
- **AC-AR-6 (FR-AR-6):** Claims estruturadas usam modelo auditado, IDs válidos
  e limite de tokens.
- **AC-AR-7 (FR-AR-7, NFR-AR-1, NFR-AR-2):** Invenções e linguagem proibida
  são rejeitadas e auditadas.
- **AC-AR-8 (FR-AR-8):** HTML contém todas as seções e objetos obrigatórios.
- **AC-AR-9 (FR-AR-9, NFR-AR-4):** Cada falha segue uma rota única e nenhum
  degradado é golden.
- **AC-AR-10 (FR-AR-10):** Limites, eventos críticos, hashes e sanitização são
  aplicados.
- **AC-AR-11 (NFR-AR-3, NFR-AR-6):** Fake OpenAI e RSS fixo produzem execução
  determinística sem chamadas live no CI.

## Verification Plan

- contratos de request, tools, evidência, claims, eventos e bundle;
- grafo completo com fake OpenAI e RSS fixo;
- prompt injection, SQL arbitrário, URL inválida, vazamento, número/citação
  inventados e linguagem clínica;
- todas as rotas da matriz de falhas;
- limites de chamadas, retry, itens, tokens e timeout;
- smoke manual do modelo OpenAI configurado e RSS live antes de `FINAL`.

## Open Questions

O modelo OpenAI padrão permanece bloqueado até smoke estruturado bem-sucedido.
Isso é uma atividade verificável, não uma decisão para múltiplos provedores.

## Change Log

- 2026-07-28 — v2.0: Brasil, HTML e OpenAI apenas; Google News RSS fixado;
  LangGraph e falhas controlados; `AuditSink` antecipado; limites e bundle
  sanitizado explícitos.
