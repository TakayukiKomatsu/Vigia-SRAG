# Fundação de dados SRAG

> Status: DRAFT
> Tier: extended
> Version: 2.0
> Owner: Indicium HealthCare PoC
> Created: 2026-07-28
> Last Updated: 2026-07-28

## Summary

Preparar snapshots oficiais fixados de SIVEP-Gripe, CNES, IBGE e PNI,
normalizá-los de forma determinística, minimizar os dados e publicar um
DuckDB analítico reproduzível para o relatório Brasil de SRAG.

## Problem

As fontes possuem schemas, calendários, competências e códigos diferentes.
Também contêm ausências, valores ignorados, datas inválidas e duplicatas.
Tratá-las como intercambiáveis ou adiar seus contratos concretos faria as
métricas dependerem de suposições não verificadas.

## Goals

- **FR-DF-1:** Manter contrato verificado para cada entrada oficial de SIVEP,
  CNES, IBGE e PNI.
- **FR-DF-2:** Carregar somente snapshots locais fixados: SIVEP 2025 e 2026,
  competência CNES completa aplicável, população IBGE aplicável e observação
  oficial elegível da campanha de influenza 2026.
- **FR-DF-3:** Normalizar o schema canônico mínimo Brasil sem converter
  desconhecido ou ignorado em resposta negativa.
- **FR-DF-4:** Aplicar deduplicação determinística, tratamento de invalidade
  por campo, códigos de motivo e quarentena estrutural.
- **FR-DF-5:** Expor somente dados analíticos minimizados; registros clínicos
  e chaves técnicas não atravessam a fronteira consumida pelo agente.
- **FR-DF-6:** Materializar DuckDB analítico somente leitura e manifestos
  imutáveis com fontes, hashes, contagens, schemas e watermarks.
- **FR-DF-7:** Calcular completude por métrica e aplicar estados de qualidade
  e bloqueios estruturais.
- **FR-DF-8:** Publicar atomicamente e preservar o último snapshot válido
  quando contrato, hash, schema ou cobertura falhar.

## Non-Functional Requirements

- **NFR-DF-1:** Mesmos bytes de origem e mesmas versões de regra produzem
  conteúdo normalizado e hashes idênticos.
- **NFR-DF-2:** Toda saída é rastreável ao recurso, recuperação, watermark,
  versão de schema e versão de transformação.
- **NFR-DF-3:** Saídas, logs, fixtures e fronteiras agentivas não contêm
  identificadores diretos nem registros clínicos linha a linha.
- **NFR-DF-4:** Um benchmark documentado processa ao menos 165.000 linhas
  SIVEP e registra tempo, pico de memória e contexto da máquina; o desafio não
  define SLA de ingestão.

## Non-Goals

- aquisição ao vivo das fontes de saúde durante a geração do relatório;
- recorte ou agregação por UF;
- cobertura vacinal de COVID-19;
- imputação clínica;
- publicação de arquivos brutos ou snapshots completos;
- migração automática e rollback de versões de schema.

## Scope

O MVP opera somente em Brasil. Notícias não pertencem a este pacote e são a
única aquisição ao vivo durante a geração do relatório.

## Source Contracts and Finalization Gate

O anexo [source-contracts.md](source-contracts.md) é normativo. Para cada
entrada ele registra URL oficial, identificador, licença/reuso, recuperação,
watermark, dicionário/schema, tamanho, SHA-256, linhas, encoding, delimitador,
mapeamento canônico, semântica temporal/geográfica, códigos, deduplicação,
falha e staleness.

Este spec permanece `DRAFT` enquanto qualquer contrato ou a fixture real
reduzida estiver `UNVERIFIED`. A ausência de evidência reabre o contrato; não
é resolvida silenciosamente no código.

## Proposed Behavior

### Inputs

1. CSVs SIVEP-Gripe 2025 e 2026, necessários para os 12 meses completos.
2. Competência mensal CNES completa mais recente compatível com o período.
3. Estimativa oficial IBGE da população do Brasil aplicável.
4. Observação oficial PNI mais recente da campanha de influenza 2026,
   publicada até o `as_of` solicitado.

Cada execução recebe caminhos locais e hashes esperados. Nenhuma URL de fonte
de saúde é chamada pelo runtime de relatório.

### Canonical Model

Campos preservados antes da agregação:

- SIVEP: chave de notificação (única por ano), data de notificação, início dos
  sintomas, internação, entrada e saída de UTI, evolução, data da evolução, UF de
  residência e UF de internação; **não inclui timestamp de atualização (não existe
  em dados públicos);**
- CNES: competência **202606 (congelada)**, UF do estabelecimento, código/categoria
  de UTI (allowlist exato: 61,62,63,75,76,79,80,81,82) e leitos existentes compatíveis;
- população: ano, geografia e população oficial;
- vacinação: campanha NE/CO/S/SE, imunobiológico, grupos-alvo, período, geografia de
  residência, numerador, denominador, cobertura publicada, atualização e fonte
  (elegível somente se publicada ≤ as_of solicitado).

As UFs permanecem apenas para validar/filtrar o agregado nacional e alinhar
residência/estabelecimento; não criam saída regional no MVP. A chave SIVEP é
usada somente antes da agregação e não aparece no DuckDB agent-facing.

### Normalization, Deduplication, and Quarantine

- desconhecido, ignorado e ausente permanecem distintos de "não";
- valores clínicos ausentes não são imputados;
- datas impossíveis, futuras ou com ordem inválida são anuladas ou rejeitadas
  conforme matriz de campo, sempre com código de motivo;
- registros sem estrutura mínima vão para quarentena;
- **deduplicação SIVEP-intra-arquivo** (2025 ou 2026): `NU_NOTIFIC` é chave estável
  dentro de um ano; não existe campo de atualização em dados públicos; múltiplos
  registros com mesma `NU_NOTIFIC` (improvável com dados públicos anônimos) resolvem
  por: maior completude canônica → desempate estável (hash de linha canônico);
- **deduplicação SIVEP-inter-arquivo** (2025 ↔ 2026): `NU_NOTIFIC` não recorre
  (zero overlap verificado); ambos arquivos são carregados conforme calendário;
- aceites, exclusões, nulificações, quarentenas e duplicatas são contados por
  fonte, campo, métrica e motivo.
### Quality

Cada métrica recebe a completude dos campos dos quais depende:

- `>= 90%`: valor disponível;
- `>= 70%` e `< 90%`: valor disponível com aviso proeminente;
- `< 70%`: métrica indisponível.

Coluna crítica ausente, hash inválido ou período não coberto bloqueia o
snapshot ou a seção afetada independentemente da porcentagem. Os limiares são
guardrails da PoC, não padrões epidemiológicos oficiais. O snapshot de
referência precisa manter disponíveis as quatro métricas e as duas séries.

### Publication

Arquivos candidatos são escritos fora do diretório publicado. Manifesto,
hashes, schema, contagens e verificações são concluídos antes da troca
atômica. Falha preserva o último snapshot válido e registra motivo estruturado.

## Interfaces and Data

Comando lógico de preparação:

```text
srag-report prepare-data --contracts source-contracts.yml --output data/snapshots
```

Saídas lógicas:

```text
data/snapshots/<snapshot_id>/
  analytics.duckdb
  manifest.json
  quality.json
```

O manifesto contém `snapshot_id`, versões, arquivos/fontes, SHA-256,
watermarks, linhas recebidas/aceitas/rejeitadas/deduplicadas, schemas,
qualidade e estado de publicação.

## Failure Handling

| Falha | Resultado |
|---|---|
| contrato, recurso ou hash não verificado | não iniciar ingestão |
| coluna crítica ausente ou schema incompatível | rejeitar candidato |
| registro estruturalmente inválido | quarentenar e contar |
| campo não crítico inválido | anular conforme matriz e contar |
| período insuficiente | bloquear apenas os resultados dependentes |
| publicação parcial | não selecionar candidato; preservar último válido |

## Security and Compliance

Dados brutos e completos ficam fora do Git. Somente fixtures pequenas,
permitidas e minimizadas podem ser versionadas. Segredos, registros clínicos,
chaves técnicas, payloads brutos e o documento restrito do desafio não entram
em logs, artefatos públicos ou commits.

## Observability and Capacity

Cada estágio registra fonte, versão, duração, contagens, códigos de qualidade e
hashes, sem linhas clínicas. O benchmark de `NFR-DF-4` documenta a máquina e
mede o volume aproximado citado pelo desafio.

## Acceptance Criteria

- **AC-DF-1 (FR-DF-1, NFR-DF-2):** Os quatro contratos e a fixture real
  reduzida são verificáveis antes da promoção do status.
- **AC-DF-2 (FR-DF-2):** Somente as quatro famílias fixadas são carregadas e
  cada saída identifica seu recurso exato.
- **AC-DF-3 (FR-DF-3, FR-DF-4):** Normalização, deduplicação, invalidade e
  quarentena seguem regras determinísticas e contabilizadas.
- **AC-DF-4 (FR-DF-5, NFR-DF-3):** Nenhum identificador, chave técnica ou
  registro clínico atravessa a fronteira analítica.
- **AC-DF-5 (FR-DF-6, NFR-DF-1, NFR-DF-2):** DuckDB e manifestos são
  reproduzíveis e verificáveis.
- **AC-DF-6 (FR-DF-7):** Limiares e bloqueios estruturais produzem os estados
  definidos.
- **AC-DF-7 (FR-DF-8):** Falha de candidato preserva o último snapshot válido.
- **AC-DF-8 (NFR-DF-4):** O benchmark processa ao menos 165.000 linhas e
  registra as medições exigidas.

## Verification Plan

- contratos e schemas por fonte;
- fixtures de códigos desconhecidos, datas inválidas, duplicatas e quarentena;
- teste de minimização e busca de campos proibidos;
- duas execuções idênticas para comparar hashes;
- falhas de hash, schema, cobertura e publicação;
- benchmark com ao menos 165.000 linhas.

## Fixtures and Finalization Gate

**Synthetic Public Fixtures** (contract-faithful, deterministic test data):
- Dados minimizados, permutados e gerados conformes a contratos verificados
- Reproduzem cenários de normalização, deduplicação, invalidade e quarentena
- Compatíveis com CC BY-ND (sem dados originais)
- Utilizados em T-DF-2 até T-DF-6 para testes de determinismo e privacidade

**Real Reduced Fixture** (raw source derivate, gate T-DF-1):
- Snapshot anual verificado de SIVEP (minimizado conforme allowlist)
- Estado de elegibilidade (`VERIFIED`, `PARTIAL`, `INELIGIBLE`) definido em source-contracts.md
- Requer permissão legal explícita para redistribuição
- Utilizado somente após resolução de todos bloqueadores de source-contracts.md
- Spec permanece `DRAFT` enquanto fixture real estiver `UNVERIFIED`
## Open Questions

Os recursos, códigos e metadados marcados `UNVERIFIED` no anexo são
bloqueadores com evidência e dono explícitos. Não há questão de produto aberta.

## Change Log

- 2026-07-28 — v2.0: reduz escopo ao Brasil e snapshots fixados; torna
  contratos oficiais e fixture um gate explícito; remove COVID-19, paridade
  live/local e rollback do MVP.
