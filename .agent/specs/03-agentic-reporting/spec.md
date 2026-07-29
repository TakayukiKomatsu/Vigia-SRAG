# Agente e relatório fundamentado de SRAG

> Status: DRAFT
> Tier: extended
> Version: 2.2
> Owner: Indicium HealthCare PoC
> Created: 2026-07-28
> Last Updated: 2026-07-29

## Summary

Orquestrar tools tipadas de métricas, gráficos e notícias em um LangGraph
controlado, gerar comentários estruturados por provedor aprovado (OpenRouter
por padrão ou OpenAI explícito), validar todas as claims e publicar relatório
HTML com bundle de auditoria sanitizado.

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
- **FR-AR-6:** Usar adaptadores aprovados de saída estruturada — OpenRouter
  como padrão e OpenAI explícito — vinculados a evidências, registrando modelos
  solicitado e servido.
- **FR-AR-7:** Rejeitar IDs, números, citações, causalidade, diagnósticos,
  recomendações e instruções jornalísticas sem suporte.
- **FR-AR-8:** Renderizar HTML determinístico com métricas, suplementos,
  gráficos, contexto, métodos, fontes, watermarks, qualidade, limitações e
  `run_id`.
- **FR-AR-9:** Aplicar matriz de falhas inequívoca e fallback factual sem
  permitir que relatório degradado satisfaça o golden run. Somente a cobertura
  PNI de influenza pode permanecer scoped como suplemento explicitamente
  não-nacional; escopo nas outras cinco métricas falha o gate.
- **FR-AR-10:** Ser dono de `AuditSink`, eventos JSONL, run bundle, limites e
  comportamento fail-closed para eventos críticos.

## Non-Functional Requirements

- **NFR-AR-1:** Texto do LLM não substitui valores, pontos de gráfico, datas ou
  URLs autoritativos.
- **NFR-AR-2:** Toda claim gerada referencia IDs existentes no
  `EvidenceBundle`.
- **NFR-AR-3:** Transições e fallback são determinísticos para a mesma
  evidência e respostas fake.
- **NFR-AR-4:** Falha de notícias ou do provedor de modelo ainda produz
  relatório factual explicitamente degradado quando os componentes críticos
  permanecem válidos.
- **NFR-AR-5:** Provedor de modelo, auditoria, evidência e relatório recebem
  somente agregados.
- **NFR-AR-6:** CI usa adaptador fake e RSS fixo; smoke live é manual e
  identificado separadamente.

## Non-Goals

- geografia diferente de Brasil;
- SQL, URL de busca, prompt ou loop de tools arbitrários;
- busca web aberta ou leitura integral de artigos;
- provedores além de OpenRouter padrão e OpenAI explícito;
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
- `agent`: estado/nós LangGraph, provedores de comentário e validação;
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

## Model Providers and Grounding

Os adaptadores implementam o mesmo `CommentaryAdapter`. O modo live usa
OpenRouter por padrão com `OPEN_ROUTER_API_KEY`, `openrouter/free` e a API
compatível de Chat Completions pelo cliente Python `openai`; OpenAI permanece
selecionável explicitamente com `OPENAI_API_KEY` e `gpt-5.6`. O modelo
solicitado e o modelo efetivamente servido entram no manifesto/auditoria.
Testes automatizados usam fake determinístico; o smoke OpenRouter estruturado
foi concluído antes da promoção desta integração.

O provedor recebe somente o `EvidenceBundle` agregado e devolve
`CommentaryClaim[]` sob schema estrito e allowlist exata de `evidence_id`.
Cada ID precisa existir. A resposta não fornece URLs, não altera números
renderizados e não controla gráficos.

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
- uma tentativa adicional somente para falha transitória ou resposta
  estruturada inválida de notícia/provedor;
- no máximo cinco notícias;
- no máximo 4.096 tokens de saída no OpenRouter e 1.200 no OpenAI;
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
ao persistir evento crítico antes do provedor de modelo ou publicação interrompe a
execução.

## Scoped and Limited Observations

Uma métrica pode ter escopo geográfico ou cobertura populacional limitada.
A cobertura PNI de influenza com grupos-alvo/regiões de residência pode
permanecer no golden como suplemento explicitamente limitado, nunca nacional.
Qualquer `population_scope` nas outras cinco métricas reprova o golden.

Quando a métrica depender de observação com escopo ou cobertura cutoff
inelegível (não publicada até `as_of` solicitado), o resultado fica
indisponível e a seção é renderizada explicitamente com limitação estruturada.
Nunca substitui com substituto inventado.

## Failure Matrix
| Falha | Rota | Publica | Golden |
|---|---|---|---|
| request inválido ou `as_of` após watermark | termina antes das tools/provedor | não | não |
| snapshot, hash, schema ou evidência inválida | termina antes do provedor | não | não |
| métrica indisponível com motivo válido | seção explícita | sim, degradado | não |
| influenza scoped e disponível | seção suplementar com limitação | sim | sim, se os demais gates passarem |
| outra métrica scoped | seção explícita com limitação | sim | não |
| nenhuma notícia válida após retry permitido | relatório quantitativo com limitação | sim, degradado | não |
| provedor falha após retry ou claims são inválidas | comentário factual determinístico | sim, degradado | não |
| gráfico ou renderer falha | termina publicação | não | não |
| auditoria crítica falha | termina antes do provedor/publicação | não | não |
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
- **AC-AR-5 (FR-AR-5, NFR-AR-5):** Evidência e payload do provedor contêm
  somente agregados e IDs.
- **AC-AR-6 (FR-AR-6):** Claims estruturadas usam provedor/modelo auditados,
  IDs válidos e limite de tokens.
- **AC-AR-7 (FR-AR-7, NFR-AR-1, NFR-AR-2):** Invenções e linguagem proibida
  são rejeitadas e auditadas.
- **AC-AR-8 (FR-AR-8):** HTML contém todas as seções e objetos obrigatórios.
- **AC-AR-9 (FR-AR-9, NFR-AR-4):** Cada falha segue uma rota única; nenhum
  degradado é golden, e escopo somente é aceito para influenza suplementar.
- **AC-AR-10 (FR-AR-9):** Observações scoped são marcadas explicitamente,
  nunca rotuladas nacionais; o gate rejeita escopo nas outras cinco métricas.
- **AC-AR-11 (FR-AR-10):** Limites, eventos críticos, hashes e sanitização são
  aplicados.
- **AC-AR-12 (NFR-AR-3, NFR-AR-6):** Adaptador fake e RSS fixo produzem
  execução determinística sem chamadas live no CI.
- **AC-AR-13 (FR-AR-4, FR-AR-6, FR-AR-9, FR-AR-10):** Contratos locais
  impõem três claims, tentativa transitória limitada, falhas neutras ao
  provedor, exclusão de notícias do payload e evento de rejeição sanitizado.
- **AC-AR-14 (FR-AR-4):** Toda requisição RSS aplica redirects, limites de
  resposta/campos e bloqueia destinos não globais antes da conexão.

## Verification Plan

- contratos de request, tools, evidência, claims, eventos e bundle;
- grafo completo com adaptador fake e RSS fixo;
- prompt injection, SQL arbitrário, URL inválida, vazamento, número/citação
  inventados e linguagem clínica;
- todas as rotas da matriz de falhas;
- limites de chamadas, retry, itens, tokens e timeout;
- smoke manual OpenRouter/RSS, incluindo modelo servido, schema e grounding.

## Open Questions

O smoke OpenRouter padrão foi concluído. O spec permanece `DRAFT` pelos
contratos oficiais e pelo release público, não por uma decisão de provedor.

## Change Log

- 2026-07-29 — v2.2: aceitação enumera contratos locais de comentário e a
  política RSS limitada; rastreabilidade aponta para testes executáveis.

- 2026-07-29 — v2.1: OpenRouter padrão via cliente compatível, OpenAI explícito,
  modelos solicitado/servido auditados e influenza scoped permitida apenas
  como suplemento não-nacional.

- 2026-07-28 — v2.0: Brasil, HTML e OpenAI apenas; Google News RSS fixado;
  LangGraph e falhas controlados; `AuditSink` antecipado; limites e bundle
  sanitizado explícitos.
