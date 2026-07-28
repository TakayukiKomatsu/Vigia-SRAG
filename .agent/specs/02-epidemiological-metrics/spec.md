# Métricas e gráficos epidemiológicos de SRAG

> Status: FINAL
> Tier: extended
> Version: 1.0
> Owner: Indicium HealthCare PoC
> Created: 2026-07-28
> Last Updated: 2026-07-28

## Summary

Calcular, para Brasil ou uma UF, métricas reproduzíveis de aumento de casos, letalidade, ocupação estimada de UTI por SRAG e coberturas vacinais de influenza e COVID-19, além das séries de 30 dias e 12 meses exigidas.

## Problem

Os nomes do desafio são ambíguos sem fórmula, denominador e tratamento de ausentes. Delegar os cálculos ao LLM comprometeria precisão e auditoria.

## Goals

- **FR-MT-1:** Aceitar geografia Brasil ou UF oficial e uma data de referência limitada ao snapshot.
- **FR-MT-2:** Calcular aumento percentual comparando sete dias encerrados na referência com os sete dias anteriores.
- **FR-MT-3:** Calcular letalidade entre internações SRAG com evolução conhecida e expor exclusões.
- **FR-MT-4:** Calcular ocupação estimada de leitos UTI por pacientes SRAG usando paciente-dias e leito-dias CNES.
- **FR-MT-5:** Calcular separadamente cobertura de influenza e cobertura de COVID-19 conforme público-alvo/esquema oficial.
- **FR-MT-6:** Produzir série diária dos 30 dias encerrados na referência, incluindo dias sem casos com valor zero.
- **FR-MT-7:** Produzir série mensal dos 12 meses encerrados no mês da referência, incluindo meses sem casos com valor zero.
- **FR-MT-8:** Retornar cada métrica como objeto estruturado com fórmula, valor/estado, numerador, denominador, unidade, período, geografia, snapshot, versão e qualidade.
- **FR-MT-9:** Gerar dois gráficos a partir das séries estruturadas, sem usar o LLM.
- **FR-MT-10:** Disponibilizar a proporção de internações com uso de UTI apenas como indicador auxiliar, nunca como ocupação.

## Non-Goals

- **NG-MT-1:** Inferir causalidade ou prever surtos.
- **NG-MT-2:** Calcular ocupação geral de UTI por todas as causas.
- **NG-MT-3:** Somar ou tirar média das coberturas de influenza e COVID-19.
- **NG-MT-4:** Imputar valores clínicos ausentes para produzir uma métrica.

## Scope

Inclui domínio das fórmulas, consultas DuckDB parametrizadas, qualidade, séries e rendering dos dois gráficos. Não inclui ingestão, notícias ou narrativa.

## Existing Context

Depende do manifesto e das tabelas canônicas de `01-data-foundation`. A data epidemiológica principal é início dos sintomas válido. Brasil é agregação das UFs disponíveis; UF usa sigla oficial.

## Users and Workflows

O orquestrador ou a CLI solicita um pacote de métricas com `geography` e `as_of`. O serviço fixa o snapshot, valida a referência, executa fórmulas versionadas e devolve um `EvidenceBundle` quantitativo.

## Proposed Behavior

### Aumento de casos

$$growth = \frac{current_7d - previous_7d}{previous_7d} \times 100$$

- `previous_7d > 0`: valor percentual, que pode ser negativo.
- ambos zero: estado `stable_zero` e valor 0%.
- anterior zero e atual positivo: estado `new_activity`, sem percentual infinito.

### Letalidade hospitalar

$$fatality = \frac{deaths}{known_outcomes} \times 100$$

O objeto deve expor total de internações, evoluções conhecidas e desconhecidas. O relatório apresenta definição explícita, embora corresponda à “taxa de mortalidade” pedida.

### Ocupação estimada de UTI por SRAG

$$occupancy = \frac{SRAG\ ICU\ patientDays}{available\ ICU\ bedDays} \times 100$$

Paciente-dias usa intervalo inclusivo de permanência sobreposto ao período consultado. Alta ausente não autoriza permanência ilimitada: aplica-se a data de referência apenas quando o caso continua internado segundo regra canônica; caso indeterminado é excluído e contado. Capacidade CNES usa competência aplicável e categorias configuradas. Resultado acima de 100% é mantido e marcado como anomalia de compatibilidade/qualidade, não truncado.

### Vacinação

Cada indicador usa numerador, denominador, população-alvo, esquema e período publicados pela fonte oficial. O sistema seleciona a observação mais recente com período aplicável até `as_of`; nunca combina campanhas distintas nem substitui uma UF ausente pelo Brasil.

### Séries

- Diária: 30 datas consecutivas terminando em `as_of`.
- Mensal: 12 meses-calendário terminando no mês de `as_of`.
- Lacunas temporais explícitas recebem zero somente quando o snapshot cobre o período; fora do watermark/cobertura, recebem estado de indisponibilidade.

## Interfaces and Data

```text
get_metric_bundle(geography, as_of, snapshot_id) -> MetricBundle
get_case_series(geography, as_of, snapshot_id) -> CaseSeriesBundle
render_charts(series_bundle, output_dir) -> ChartArtifacts
```

`geography` é `BR` ou uma UF oficial. O serviço não aceita SQL, coluna ou fórmula enviados pelo chamador.

Objeto mínimo:

```json
{
  "id": "case_growth_7d",
  "status": "available",
  "value": 12.3,
  "unit": "%",
  "numerator": 1123,
  "denominator": 1000,
  "period": {"start": "...", "end": "..."},
  "geography": "SP",
  "snapshot_id": "sha256:...",
  "formula_version": "1.0",
  "quality": {"included": 2123, "excluded": 25, "completeness": 0.98, "warnings": []}
}
```

## Alternatives Considered

- SQL gerado pelo LLM: rejeitado por baixa governança.
- Proporção de internações com UTI como ocupação: rejeitada por denominador incorreto; preservada como auxiliar.
- Ocupação por contagem de pacientes: rejeitada em favor de paciente-dias/leito-dias.

## Edge Cases and Failure Handling

- UF inválida/data futura ao snapshot: erro de validação antes da consulta.
- Base sem 14 dias cobertos: aumento indisponível.
- Denominador anterior zero: estados definidos acima.
- Sem evolução conhecida: letalidade indisponível.
- Permanência/capacidade incompatíveis: ocupação indisponível ou disponível com warning quantificado conforme gravidade.
- Cobertura vacinal ausente: indicador específico indisponível; o outro permanece independente.
- Saída gráfica sem 30/12 pontos: falha do renderer, não preenchimento silencioso.

## Risks and Constraints

- **NFR-MT-1:** Fórmulas não dependem do LLM e são determinísticas para snapshot/parâmetros fixos.
- **NFR-MT-2:** Toda métrica disponível possui proveniência e denominador verificáveis.
- **NFR-MT-3:** Consultas são parametrizadas, somente leitura e limitadas a Brasil/UF.
- **NFR-MT-4:** Um pacote completo sobre fixture deve ser calculado em até 5 segundos em estação local; o snapshot completo será medido, não prometido sem evidência.
- **NFR-MT-5:** Gráficos são legíveis, possuem título, período, unidade, fonte e texto alternativo/descrição tabular.

## Threats and Security Considerations

Evitar query injection por enums e parâmetros, não retornar chave técnica, suprimir células pequenas não é necessário quando o relatório só apresenta contagens agregadas nacionais/UF e séries gerais; se um filtro futuro aumentar granularidade, nova avaliação será obrigatória.

## Rollout, Migration, and Rollback

Fórmulas têm versão. Alteração cria versão nova e mantém fixtures da versão anterior. Rollback seleciona versão anterior sem reescrever relatórios já auditados.

## Observability

Registrar duração, linhas lidas, fórmula/versão, denominadores, estados de indisponibilidade, warnings e artefatos gráficos por run ID.

## Capacity and Operations

Pré-agregações podem ser materializadas somente se profiling demonstrar necessidade. A primeira implementação usa DuckDB sobre Parquet e evita cópias em memória.

## Compliance

Resultados são epidemiológicos agregados e devem conter aviso de não uso clínico. As definições metodológicas são parte obrigatória do relatório.

## Acceptance Criteria

- **AC-MT-1 (FR-MT-1):** Brasil e uma UF produzem resultados com geografia e data corretas; entrada inválida é rejeitada.
- **AC-MT-2 (FR-MT-2):** As três condições de denominador do aumento produzem percentual, `stable_zero` ou `new_activity` conforme definido.
- **AC-MT-3 (FR-MT-3):** Letalidade exclui evolução desconhecida e expõe a exclusão.
- **AC-MT-4 (FR-MT-4, FR-MT-10):** Ocupação usa paciente-dias/leito-dias; uso de UTI aparece apenas como auxiliar.
- **AC-MT-5 (FR-MT-5):** Influenza e COVID-19 aparecem separadas com público-alvo e fonte, sem média.
- **AC-MT-6 (FR-MT-6, FR-MT-7):** Séries possuem exatamente 30 dias e 12 meses ordenados quando o período está coberto.
- **AC-MT-7 (FR-MT-8):** Toda métrica contém proveniência, fórmula, denominador e qualidade ou motivo estruturado de indisponibilidade.
- **AC-MT-8 (FR-MT-9, NFR-MT-5):** Dois gráficos correspondem ponto a ponto às séries e contêm metadados de leitura.
- **AC-MT-9 (FR-MT-6, FR-MT-7):** Período sem cobertura temporal suficiente deixa séries indisponíveis e impede o renderer de criar pontos ou gráficos artificiais.

## Verification Plan

- Unit: fórmulas e todos os estados de denominador/fronteira.
- Integration: consultas sobre fixture DuckDB com Brasil, UF e lacunas.
- End-to-end: gerar pacote e gráficos e comparar valores/contagens conhecidos.
- Operational: medir execução em fixture e snapshot completo disponível.

## Open Questions

Nenhuma bloqueadora. Categorias CNES e definições oficiais de esquema vacinal são dados de configuração versionados, validados contra a documentação da fonte durante a implementação.

## Change Log

| Version | Date | Summary |
|---|---|---|
| 1.0 | 2026-07-28 | Contrato inicial aprovado |
