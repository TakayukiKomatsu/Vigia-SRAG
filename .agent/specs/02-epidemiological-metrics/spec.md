---
Document Status: DRAFT
Release Status: EXTERNAL-BLOCKED
Tier: extended
Version: 2.2
Owner: Indicium HealthCare PoC
Created: 2026-07-28
Date: 2026-07-29
---

# Métricas e gráficos epidemiológicos de SRAG

## Summary

Calcular para o Brasil quatro métricas obrigatórias, dois indicadores
suplementares e as séries/gráficos diário e mensal exigidos, usando fórmulas,
períodos, qualidade e proveniência determinísticos.

## Problem

“Mortalidade”, “ocupação de UTI” e “taxa de vacinação” são ambíguas sem
denominador e fonte. Usar letalidade como mortalidade, publicar um proxy acima
de 100% ou misturar calendários produziria um relatório tecnicamente
enganoso. O LLM não participa dos cálculos.

## Goals

- **FR-MT-1:** Derivar `generated_at`, `as_of`, watermarks, semanas
  epidemiológicas brasileiras e cutoffs efetivos de cada resultado.
- **FR-MT-2:** Calcular aumento de casos entre semanas epidemiológicas
  completas, consecutivas e estabilizadas.
- **FR-MT-3:** Calcular a mortalidade populacional obrigatória por SRAG por
  100.000 habitantes nas quatro semanas epidemiológicas estabilizadas mais
  recentes.
- **FR-MT-4:** Calcular letalidade hospitalar suplementar em uma coorte madura
  de quatro semanas.
- **FR-MT-5:** Calcular a pressão obrigatória de SRAG sobre capacidade de UTI
  por paciente-dias SIVEP sobre leito-dias CNES compatíveis.
- **FR-MT-6:** Calcular a proporção suplementar de internações SRAG com uso de
  UTI, sem rotulá-la como ocupação.
- **FR-MT-7:** Selecionar como indicador suplementar a observação oficial mais
  recente da campanha de influenza 2026 para a população-alvo, preservando
  `population_scope` explícito e cutoff em `as_of`; o escopo regional é
  permitido, mas nunca recebe rótulo nacional. Se não publicada no cutoff,
  o resultado é indisponível com motivo estruturado.
- **FR-MT-8:** Produzir série diária de 30 dias encerrada em `as_of`, marcando
  os 14 dias mais recentes como provisórios.
- **FR-MT-9:** Produzir série dos 12 meses-calendário completos anteriores ao
  mês de `as_of`.
- **FR-MT-10:** Retornar contratos tipados de métrica, qualidade,
  proveniência, série e gráfico e renderizar os dois gráficos sem LLM.

## Non-Functional Requirements

- **NFR-MT-1:** Fórmulas, arredondamento, indisponibilidade e denominador zero
  são determinísticos e versionados.
- **NFR-MT-2:** Cada valor e gráfico expõe período efetivo, fonte, snapshot,
  watermark, versão de fórmula e qualidade.
- **NFR-MT-3:** Consultas ao DuckDB são somente leitura e nenhuma aritmética ou
  série é delegada ao LLM.
- **NFR-MT-4:** O pacote completo termina em até cinco segundos na fixture
  reduzida do ambiente de teste documentado.
- **NFR-MT-5:** Gráficos correspondem às séries e incluem título, período,
  unidade, fonte, watermark e descrição textual.

## Non-Goals

- métricas ou gráficos por UF;
- cobertura de COVID-19;
- ocupação observada de UTI por todas as causas;
- inferência causal ou recomendação clínica;
- preenchimento com zero fora de período comprovadamente coberto.

## Temporal Contract

- Semana epidemiológica brasileira: domingo a sábado.
- `generated_at`: instante UTC da execução.
- `as_of` padrão: maior data válida de início dos sintomas no snapshot SIVEP.
- `as_of` solicitado após esse watermark: request rejeitado.
- Semana de referência: última semana completa cujo sábado terminou ao menos
  14 dias antes de `as_of`.
- Períodos de fontes diferentes permanecem separados.
- A janela de notícias pertence ao SDD 03 e termina em `generated_at`.

## Required Metrics

### Case Growth

```text
growth = (reference_week_cases - previous_week_cases)
         / previous_week_cases * 100
```

As semanas são completas, consecutivas e encerradas no cutoff estabilizado.
Com denominador positivo, o percentual pode ser positivo, zero ou negativo.
Se ambas forem zero, estado `stable_zero` e valor `0`. Se a anterior for zero
e a atual positiva, estado `new_activity` e nenhum infinito. O numerador
matemático é `delta_cases`, acompanhado de `current_cases` e `previous_cases`.

### Population Mortality

```text
mortality_per_100k =
  SRAG_deaths_in_latest_4_stabilized_epi_weeks
  / official_population * 100_000
```

Conta somente óbitos classificados como decorrentes de SRAG cuja data de
evolução esteja nas quatro semanas. Óbito por outra causa não entra. O
denominador é a população oficial IBGE aplicável. A unidade é
`óbitos por 100 mil habitantes`.

## Supplementary Indicators

### Hospital Case Fatality

```text
fatality =
  SRAG_deaths
  / hospitalizations_with_known_outcome * 100
```

A coorte usa internações com início dos sintomas nas quatro semanas completas
encerradas ao menos 28 dias antes de `as_of`. Evoluções desconhecidas saem do
denominador, são quantificadas e aparecem como limitação. O rótulo inclui
“letalidade hospitalar suplementar”, nunca apenas “mortalidade”.

### ICU Use

```text
icu_use =
  SRAG_hospitalizations_with_ICU_use
  / SRAG_hospitalizations_with_known_ICU_status * 100
```

É somente indicador suplementar e nunca recebe o rótulo de ocupação.

## Required ICU Proxy

```text
icu_pressure =
  valid_SRAG_ICU_patient_days
  / compatible_CNES_existing_ICU_bed_days * 100
```

O período é a competência mensal completa mais recente comum a SIVEP e CNES.
Paciente-dias são a interseção de entrada/saída válidas com o mês; saída
desconhecida é excluída e contada. O denominador usa leitos existentes das
categorias adultas, pediátricas ou neonatais verificadas no contrato, sem
confundir leito SUS com disponibilidade.

O rótulo obrigatório é “pressão estimada de SRAG sobre a capacidade registrada
de UTI”. O relatório declara que não é ocupação observada por todas as causas.
Resultado acima de 100% fica `unavailable` por incompatibilidade; não é
truncado nem publicado como percentual válido.

```text
influenza_coverage =
  valid_influenza_doses_for_target_groups
  / official_target_population * 100
```

Usa a observação oficial mais recente da campanha 2026 publicada até `as_of`.
Preserva campanha, grupos-alvo, residência, numerador, denominador, cobertura
publicada, atualização e fonte. Não usa população geral inventada nem
reconstrói esquemas a partir do SIVEP.

Cada observação inclui `population_scope` explícito com as regiões cobertas
(p. ex.: `NE,CO,S,SE` para a campanha de março–maio de 2026; `N` para a
campanha do segundo semestre). Escopo menor que Brasil inteiro nunca recebe
rótulo `nationwide`, mas pode compor o golden como indicador suplementar
limitado. As outras cinco métricas do pacote permanecem nacionais e sem escopo.

Se nenhuma observação elegível foi publicada até `as_of`, o resultado fica
`unavailable` com `reason` estruturado indicando "não publicada até cutoff".
Neste caso, numerador e denominador não são reportados.

## Series and Charts

- diário: 30 datas consecutivas terminando em `as_of`, por início dos
  sintomas; dias cobertos sem caso valem zero; os 14 dias mais recentes têm
  estado e marca visual `provisional`;
- mensal: 12 meses-calendário completos anteriores ao mês de `as_of`, por
  início dos sintomas; meses cobertos sem caso valem zero.

Períodos fora da cobertura não recebem zero. Série insuficiente fica
indisponível e seu gráfico não é renderizado.

## Interfaces and Data

```text
MetricResult:
  metric_id, label, value, state, reason, unit, numerator, denominator,
  period_start, period_end, geography, snapshot_id, formula_version,
  quality, source_ids, limitations

SeriesResult:
  series_id, granularity, points[{period, value, state}],
  period_start, period_end, geography, snapshot_id, quality, source_ids

ChartResult:
  chart_id, series_id, path, sha256, title, period, unit,
  source_ids, watermark, alt_text
```

`geography` é sempre `BR`. Campos numéricos podem ser ausentes apenas quando
`state` e `reason` explicarem o resultado não percentual ou indisponível.

## Quality and Failure Handling

- completude `>=90%`: disponível;
- completude `>=70%` e `<90%`: disponível com aviso;
- completude `<70%`: indisponível;
- coluna crítica, hash, fonte ou cobertura inválida sobrepõe a porcentagem;
- uma métrica indisponível não inventa substituto;
- o golden run exige as seis métricas e ambas as séries disponíveis; somente a cobertura de influenza pode ter `population_scope` regional explícito.

## Security and Compliance

As consultas são parametrizadas e somente leitura. Resultados não contêm
chaves técnicas nem registros individuais. Fórmulas e gráficos são código
determinístico; o LLM recebe somente resultados agregados validados.

## Acceptance Criteria

- **AC-MT-1 (FR-MT-1):** Calendário, `as_of`, cutoffs e períodos por fonte são
  reproduzíveis e solicitações posteriores ao watermark falham.
- **AC-MT-2 (FR-MT-2):** Aumento e estados de denominador zero seguem a fórmula.
- **AC-MT-3 (FR-MT-3):** Mortalidade populacional usa óbitos SRAG elegíveis,
  quatro semanas estabilizadas e população IBGE.
- **AC-MT-4 (FR-MT-4):** Letalidade suplementar usa a coorte madura e expõe
  desfechos desconhecidos.
- **AC-MT-5 (FR-MT-5):** Pressão UTI usa paciente-dias/leito-dias compatíveis,
  rótulo/limitação corretos e rejeita valor acima de 100%.
- **AC-MT-6 (FR-MT-6):** Uso de UTI aparece apenas como proporção suplementar.
- **AC-MT-7 (FR-MT-7):** Influenza usa a observação oficial elegível com
  população-alvo e `population_scope` explícitos; escopo regional permanece
  suplementar e não-nacional, e ausência de publicação até `as_of` produz
  estado indisponível com motivo estruturado.
- **AC-MT-8 (FR-MT-8, NFR-MT-5):** Série/gráfico diário têm 30 pontos fiéis e
  14 provisórios.
- **AC-MT-9 (FR-MT-9, NFR-MT-5):** Série/gráfico mensal têm 12 meses completos
  anteriores.
- **AC-MT-10 (FR-MT-10, NFR-MT-2):** Todo resultado possui contrato,
  proveniência, qualidade e motivo estruturado.
- **AC-MT-11 (NFR-MT-1, NFR-MT-3, NFR-MT-4):** Repetibilidade, acesso somente
  leitura, ausência de cálculo no LLM e limite da fixture são verificáveis.
- **AC-MT-12 (FR-MT-7, FR-MT-10):** Cobertura disponível sem
  `population_scope` é rejeitada; cobertura indisponível sem escopo continua
  válida, e escopo em métrica não-influenza é rejeitado no carregamento como
  `invalid_manifest_or_evidence`.

## Verification Plan

- unitários de fórmulas, períodos, calendários, denominadores e qualidade;
- fixtures para `stable_zero`, `new_activity`, crescimento negativo,
  mortalidade, letalidade, paciente-dias e `>100%`;
- integração somente leitura com DuckDB reduzido;
- comparação ponto a ponto entre séries e gráficos;
- medição do pacote completo na fixture.

## Open Questions

Os códigos SIVEP, categorias CNES, população e a evidência oficial PNI dependem
do anexo SDD 01. A política de escopo suplementar está fechada, mas este spec
permanece `DRAFT` enquanto contratos oficiais ainda estiverem `UNVERIFIED`.

## Change Log

- 2026-07-29 — v2.2: cenários executáveis distinguem escopo ausente em
  influenza disponível do resultado indisponível e fixam a rejeição de schema
  `invalid_manifest_or_evidence` para escopo não-influenza.

- 2026-07-29 — v2.1: cobertura PNI regional mantida como suplemento limitado,
  sem rótulo nacional; somente as outras cinco métricas exigem escopo nacional
  para o golden run.

- 2026-07-28 — v2.0: Brasil apenas; mortalidade populacional obrigatória;
  letalidade e uso de UTI suplementares; proxy UTI acima de 100% indisponível;
  influenza apenas; períodos estabilizados e gráficos exatos.
