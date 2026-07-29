# Governança, transparência e entrega da PoC SRAG

> Status: DRAFT
> Tier: extended
> Version: 2.2
> Owner: Indicium HealthCare PoC
> Created: 2026-07-28
> Last Updated: 2026-07-29

## Summary

Definir evidência estrita para a demonstração de referência, separar testes de
degradação, tornar o repositório reproduzível e seguro para publicação e
entregar README, relatório HTML de exemplo e diagrama conceitual em PDF.

## Problem

Uma PoC pode parecer completa mesmo sem métrica exigida, notícia live,
comentário válido, auditoria íntegra ou reprodução pública. Aceitar um
relatório degradado como referência esconderia exatamente os riscos avaliados
pelo desafio.

## Goals

- **FR-GD-1:** Validar golden run estrito com quatro métricas, dois
  suplementos, dois gráficos, notícia live, comentário válido de provedor
  aprovado e bundle sanitizado completo. Somente influenza pode ser scoped
  como suplemento explicitamente não-nacional.
- **FR-GD-2:** Manter suítes separadas de degradação e segurança que não
  substituem o golden run.
- **FR-GD-3:** Fornecer quickstarts determinístico e live; o live requer a
  chave do provedor selecionado, por padrão `OPEN_ROUTER_API_KEY`.
- **FR-GD-4:** Publicar README completo e HTML de referência sanitizado com
  rótulos live/não-live inequívocos.
- **FR-GD-5:** Publicar fonte e PDF legível do diagrama conceitual com todos os
  componentes, fluxos e limites de confiança.
- **FR-GD-6:** Aplicar pytest, Ruff, mypy, GitHub Actions, Gitleaks,
  `.gitignore` e higiene do repositório público.
- **FR-GD-7:** Verificar URL GitHub pública por clone limpo não autenticado e
  preservar evidência de release.
- **FR-GD-8:** Manter 28 tarefas Must nos Dias 1–5 e impedir Stretch antes de
  todos os gates obrigatórios.

## Non-Functional Requirements

- **NFR-GD-1:** Ausência de evento crítico de auditoria impede publicação.
- **NFR-GD-2:** Artefatos liberados não contêm segredo, documento restrito,
  registro clínico, chave técnica, payload bruto ou corpo integral de artigo.
- **NFR-GD-3:** Quickstart determinístico funciona em clone limpo sem editar
  código, credencial ou chamada live de provedor/RSS.
- **NFR-GD-4:** O PDF é legível e todos os componentes/limites exigidos podem
  ser identificados visualmente.
- **NFR-GD-5:** Qualidade, CI e secret scan passam no commit de release.

## Non-Goals

- observabilidade de produção, SIEM ou autenticação multiusuário;
- SLA de produção;
- relatório em PDF;
- dashboards ou deploy em nuvem;
- completar itens Stretch antes do MVP.

## Ownership and Dependencies

SDD 03 cria `AuditSink` e o run bundle. Este pacote apenas valida, documenta e
libera esses artefatos. Assim, a auditoria existe desde o primeiro nó e não há
dependência circular.

Este spec só recebe `FINAL` quando SDDs 01, 02 e 03 estiverem `FINAL` com suas
evidências registradas.

## Strict Golden Run

O relatório de referência passa somente se contiver:

1. aumento de casos real, disponível e nacional sem `population_scope`;
2. mortalidade populacional real, disponível e nacional sem `population_scope`;
3. pressão estimada de SRAG sobre capacidade registrada de UTI real,
   disponível e nacional sem `population_scope`;
4. cobertura oficial de influenza 2026 real, disponível, publicada até
   `as_of`, com `population_scope` explícito; escopo regional é permitido
   somente aqui e nunca recebe rótulo nacional;
5. letalidade hospitalar e uso de UTI suplementares, nacionais sem
   `population_scope`;
6. gráfico diário completo de 30 dias;
7. gráfico mensal completo de 12 meses;
8. ao menos uma notícia recente válida coletada ao vivo;
9. claims estruturadas e validadas de provedor/modelo aprovado;
10. fontes, métodos, watermarks, qualidade, limitações e `run_id`;
11. `request.json`, `evidence.json`, `audit.jsonl`, `charts/`, `report.html` e
    `manifest.json` íntegros e sanitizados.

Qualquer ausência falha o golden. Métrica indisponível não satisfaz o item
correspondente. Influenza scoped é suplemento limitado elegível; escopo
geográfico ou populacional em qualquer das outras cinco métricas reprova o
gate. Toda observação scoped renderiza explicitamente como não-nacional.

## Degradation and Security

Casos de notícia, provedor de modelo ou métrica indisponível e falhas de auditoria são
testados separadamente segundo SDD 03. Um resultado degradado pode demonstrar
resiliência, mas nunca é selecionado como relatório de referência.

A suíte cobre prompt injection, SQL arbitrário, URL inválida, citação/número
inventado, vazamento de campo, segredo e evento crítico ausente.

## Quickstarts

### Deterministic

- adaptador fake;
- RSS fixo;
- fixture permitida;
- nenhuma credencial;
- nenhuma chamada live de provedor/RSS;
- sem edição de código;
- relatório marcado como demonstração não-live.

### Live

- requer `OPEN_ROUTER_API_KEY` por padrão ou a chave do provedor explicitamente selecionado;
- usa provedor/modelo aprovados e registra modelos solicitado e servido;
- consulta Google News RSS durante a execução;
- usa snapshots de saúde fixados;
- produz candidato ao golden run, sujeito a todos os gates.

## README and Reference Artifact

O README cobre instalação, configuração, arquitetura, fontes e aquisição,
fórmulas, períodos, qualidade, grafo, tools, provedores de modelo, notícias,
auditoria, guardrails, privacidade, testes, quickstarts, limitações e exemplo.
O HTML de referência é sanitizado e informa se é live.

## Architecture PDF

O diagrama mostra:

- SIVEP, CNES, IBGE e PNI;
- Google News RSS;
- DuckDB;
- tools de métricas, gráficos e notícias;
- LangGraph orquestrador;
- OpenRouter/OpenAI e validador;
- renderer HTML;
- `AuditSink` e run bundle;
- fluxos, agregação e limites de dados sensíveis.

O PDF é o único PDF obrigatório.

## Repository and CI

O repositório inclui pacote Python tipado, `pyproject.toml` com dependências
fixadas, configuração exemplo, fixtures pequenas permitidas, README, HTML
sanitizado, fonte/PDF de arquitetura e GitHub Actions.

Checks: pytest, Ruff, mypy e Gitleaks. `.gitignore` exclui `.env`, dados brutos,
snapshots completos, run bundles locais, `.omc/`, `.superpowers/` e
`Desafio de GenAI.txt`. Antes de publicar, arquivos staged e histórico são
inspecionados para segredo e material restrito.

## Public Release Gate

Uma pessoa sem autenticação deve conseguir:

1. acessar a URL pública;
2. clonar o commit de release;
3. seguir o quickstart determinístico sem editar código;
4. localizar o `run_id`, evidências e HTML de exemplo;
5. verificar o golden live sanitizado já versionado.

Release só termina quando todos os passos e o smoke live forem registrados.

## Five-Day Plan

- Dia 1: contratos, pacote e quatro fontes no DuckDB.
- Dia 2: métricas, suplementos, qualidade, séries e gráficos.
- Dia 3: tools, LangGraph, RSS, provedores, validação, auditoria e HTML.
- Dia 4: golden/degradação, README, exemplo e arquitetura PDF.
- Dia 5: clone limpo, CI, secret scan, smoke live, revisão visual e publicação.

Stretch não começa antes dos 28 itens Must e do golden estrito.

## Acceptance Criteria

- **AC-GD-1 (FR-GD-1, NFR-GD-1, NFR-GD-2):** Golden contém os onze itens,
  integridade e sanitização.
- **AC-GD-2 (FR-GD-2, NFR-GD-1):** Degradação/segurança seguem seus resultados
  sem elegibilidade golden.
- **AC-GD-3 (FR-GD-3, NFR-GD-3):** Quickstart determinístico funciona no clone
  limpo sem credencial, rede live ou edição.
- **AC-GD-4 (FR-GD-3):** Quickstart live requer somente a chave do provedor
  selecionado e registra modelos solicitado/servido e RSS live.
- **AC-GD-5 (FR-GD-4):** README e HTML sanitizado cobrem documentação e rótulo.
- **AC-GD-6 (FR-GD-5, NFR-GD-4):** PDF é legível e contém todos os componentes
  e limites.
- **AC-GD-7 (FR-GD-6, NFR-GD-2, NFR-GD-5):** Qualidade, CI, Gitleaks, staged
  files, histórico e ignores passam.
- **AC-GD-8 (FR-GD-7):** URL pública e clone não autenticado reproduzem a demo
  e expõem evidência de release.
- **AC-GD-10 (FR-GD-1):** Influenza pode ter escopo regional como suplemento
  explicitamente não-nacional; qualquer escopo nas outras cinco métricas
  reprova o golden.
- **AC-GD-9 (FR-GD-8):** O backlog possui 7+7+8+6 tarefas completas nos Dias
  1–5 e Stretch isolado.
- **AC-GD-11 (FR-GD-1):** Evidência oficial SIVEP é registrada com proveniência;
  CNES/PNI indisponíveis tornam as métricas dependentes indisponíveis e impedem
  promoção a golden, sem fingir que a execução oficial falhou.
- **AC-GD-12 (FR-GD-6, FR-GD-7):** Verificadores de metadados, conteúdo atual,
  histórico e release externo falham fechados; a evidência externa permanece
  vinculada à SHA imutável e clone anônimo aprovado.

## Verification Plan

- golden end-to-end estrito;
- degradação e segurança separadas;
- quickstart determinístico em clone limpo;
- smoke manual live;
- inspeção do README/HTML e do PDF renderizado;
- pytest, Ruff, mypy, CI e Gitleaks;
- staged files, histórico, URL pública e clone não autenticado;
- validação mecânica de IDs e 28 tarefas.

## Open Questions

O smoke OpenRouter e o gate estrito sobre fixture permitida estão verdes.
Contratos oficiais restantes, bundle de referência real e URL pública continuam
como bloqueadores explícitos; este spec permanece `DRAFT`.

## Change Log

- 2026-07-29 — v2.2: critérios executáveis adicionam proveniência SIVEP,
  indisponibilidade explícita de CNES/PNI e verificadores de release externos.

- 2026-07-29 — v2.1: OpenRouter padrão, OpenAI explícito, modelos
  solicitado/servido auditados e PNI scoped permitido somente como suplemento;
  release público permanece handoff do owner.

- 2026-07-28 — v2.0: golden estrito; degradação separada; HTML apenas;
  quickstarts distintos; CI/secret scan; PDF conceitual e publicação pública
  verificáveis; 28 tarefas em cinco dias.
