# Governança, transparência e entrega da PoC SRAG

> Status: DRAFT
> Tier: extended
> Version: 2.0
> Owner: Indicium HealthCare PoC
> Created: 2026-07-28
> Last Updated: 2026-07-28

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
  suplementos, dois gráficos, notícia live, comentário OpenAI válido e bundle
  sanitizado completo.
- **FR-GD-2:** Manter suítes separadas de degradação e segurança que não
  substituem o golden run.
- **FR-GD-3:** Fornecer quickstarts determinístico e live; somente o live
  requer `OPENAI_API_KEY`.
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
  código, credencial ou chamada live de OpenAI/RSS.
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

1. aumento de casos real, disponível e não-scoped nacionalmente;
2. mortalidade populacional real, disponível e não-scoped nacionalmente;
3. pressão estimada de SRAG sobre capacidade registrada de UTI real,
   disponível e não-scoped nacionalmente;
4. cobertura oficial de influenza 2026 real, disponível, elegível
   nacionalmente (não limitada a regiões específicas) e publicada até `as_of`;
5. letalidade hospitalar e uso de UTI suplementares, não-scoped;
6. gráfico diário completo de 30 dias;
7. gráfico mensal completo de 12 meses;
8. ao menos uma notícia recente válida coletada ao vivo;
9. claims OpenAI estruturadas e validadas;
10. fontes, métodos, watermarks, qualidade, limitações e `run_id`;
11. `request.json`, `evidence.json`, `audit.jsonl`, `charts/`, `report.html` e
    `manifest.json` íntegros e sanitizados.

Qualquer ausência falha o golden. Métrica indisponível não satisfaz o item
correspondente. Observação com escopo geográfico ou cobertura limitada não é
elegível e deve renderizar explicitamente como limitada.

## Degradation and Security

Casos de notícia, OpenAI ou métrica indisponível e falhas de auditoria são
testados separadamente segundo SDD 03. Um resultado degradado pode demonstrar
resiliência, mas nunca é selecionado como relatório de referência.

A suíte cobre prompt injection, SQL arbitrário, URL inválida, citação/número
inventado, vazamento de campo, segredo e evento crítico ausente.

## Quickstarts

### Deterministic

- OpenAI fake;
- RSS fixo;
- fixture permitida;
- nenhuma credencial;
- nenhuma chamada OpenAI/RSS live;
- sem edição de código;
- relatório marcado como demonstração não-live.

### Live

- requer somente `OPENAI_API_KEY`;
- usa o modelo padrão aprovado e registra seu nome exato;
- consulta Google News RSS durante a execução;
- usa snapshots de saúde fixados;
- produz candidato ao golden run, sujeito a todos os gates.

## README and Reference Artifact

O README cobre instalação, configuração, arquitetura, fontes e aquisição,
fórmulas, períodos, qualidade, grafo, tools, OpenAI, notícias, auditoria,
guardrails, privacidade, testes, quickstarts, limitações e leitura do exemplo.
O HTML de referência é sanitizado e informa se é live.

## Architecture PDF

O diagrama mostra:

- SIVEP, CNES, IBGE e PNI;
- Google News RSS;
- DuckDB;
- tools de métricas, gráficos e notícias;
- LangGraph orquestrador;
- OpenAI e validador;
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
- Dia 3: tools, LangGraph, RSS, OpenAI, validação, auditoria e HTML.
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
- **AC-GD-4 (FR-GD-3):** Quickstart live requer somente a chave OpenAI e
  registra modelo/RSS live.
- **AC-GD-5 (FR-GD-4):** README e HTML sanitizado cobrem documentação e rótulo.
- **AC-GD-6 (FR-GD-5, NFR-GD-4):** PDF é legível e contém todos os componentes
  e limites.
- **AC-GD-7 (FR-GD-6, NFR-GD-2, NFR-GD-5):** Qualidade, CI, Gitleaks, staged
  files, histórico e ignores passam.
- **AC-GD-8 (FR-GD-7):** URL pública e clone não autenticado reproduzem a demo
  e expõem evidência de release.
- **AC-GD-10 (FR-GD-1):** Observações com escopo geográfico ou cobertura
  regional limitada nunca são selecionadas como golden; devem renderizar como
  explicitamente limitadas e não-nacionais.
- **AC-GD-9 (FR-GD-8):** O backlog possui 7+7+8+6 tarefas completas nos Dias
  1–5 e Stretch isolado.

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

Os gates upstream e a URL pública ainda não existem; são bloqueadores
explícitos. Este spec permanece `DRAFT`.

## Change Log

- 2026-07-28 — v2.0: golden estrito; degradação separada; HTML apenas;
  quickstarts distintos; CI/secret scan; PDF conceitual e publicação pública
  verificáveis; 28 tarefas em cinco dias.
