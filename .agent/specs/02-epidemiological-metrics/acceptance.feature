# Document Status: DRAFT
# Release Status: EXTERNAL-BLOCKED
# Version: 2.2
# Date: 2026-07-29

@draft @metrics
Feature: Métricas e gráficos epidemiológicos Brasil de SRAG
  Os cenários derivam do spec.md versão 2.2.

  Background:
    Given que existe um snapshot canônico Brasil com contratos verificados

  @ch-13 @fr-mt-1 @ac-mt-1
  Scenario: Derivar a data de referência e os cutoffs
    Given que a maior data válida de início dos sintomas é 2026-07-28
    When o pacote for solicitado sem data de referência
    Then "as_of" deve ser 2026-07-28
    And "generated_at" deve ser registrado separadamente em UTC
    And a semana de referência deve terminar em um sábado pelo menos 14 dias antes
    And a coorte de letalidade deve terminar pelo menos 28 dias antes

  @ch-13 @fr-mt-1 @ac-mt-1
  Scenario: Rejeitar data posterior ao watermark
    Given que a maior data válida de início dos sintomas é 2026-07-28
    When o pacote for solicitado para 2026-07-29
    Then a solicitação deve falhar antes de calcular métricas
    And nenhuma substituição silenciosa de data deve ocorrer

  @ch-04 @fr-mt-2 @nfr-mt-1 @ac-mt-2
  Scenario: Calcular aumento com numerador correto
    Given 100 casos na semana epidemiológica anterior
    And 125 casos na semana epidemiológica de referência
    When o aumento for calculado
    Then o valor deve ser 25 por cento
    And "previous_cases" deve ser 100
    And "current_cases" deve ser 125
    And "numerator" e "delta_cases" devem ser 25

  @ch-04 @fr-mt-2 @ac-mt-2
  Scenario Outline: Tratar denominador zero sem infinito
    Given "<previous>" casos na semana anterior
    And "<current>" casos na semana de referência
    When o aumento for calculado
    Then o estado deve ser "<state>"
    And o valor deve ser "<value>"

    Examples:
      | previous | current | state        | value       |
      | 0        | 0       | stable_zero  | 0           |
      | 0        | 4       | new_activity | unavailable |

  @ch-05 @fr-mt-3 @ac-mt-3
  Scenario: Calcular mortalidade populacional por SRAG
    Given 20 óbitos por SRAG nas quatro semanas estabilizadas
    And 3 óbitos por outra causa no mesmo período
    And população oficial de 1000000 habitantes
    When a mortalidade for calculada
    Then o valor deve ser 2 óbitos por 100 mil habitantes
    And o numerador deve ser 20
    And o denominador deve ser 1000000
    And os óbitos por outra causa devem ser excluídos

  @fr-mt-4 @ac-mt-4
  Scenario: Calcular letalidade hospitalar suplementar
    Given 10 óbitos, 90 altas e 20 evoluções desconhecidas na coorte madura
    When a letalidade for calculada
    Then o valor deve ser 10 por cento
    And 20 evoluções desconhecidas devem ser expostas como exclusões
    And o rótulo deve informar "letalidade hospitalar suplementar"

  @ch-06 @fr-mt-5 @ac-mt-5
  Scenario: Calcular pressão estimada de SRAG sobre UTI
    Given 150 paciente-dias SRAG válidos
    And 1000 leito-dias CNES compatíveis existentes
    When a pressão de UTI for calculada
    Then o valor deve ser 15 por cento
    And o rótulo deve informar "pressão estimada de SRAG sobre a capacidade registrada de UTI"
    And a limitação deve negar ocupação observada por todas as causas

  @ch-06 @ch-13 @fr-mt-5 @ac-mt-5
  Scenario: Tornar incompatibilidade acima de 100 por cento indisponível
    Given 1100 paciente-dias SRAG válidos
    And 1000 leito-dias CNES compatíveis existentes
    When a pressão de UTI for calculada
    Then o estado deve ser "unavailable"
    And o motivo deve indicar incompatibilidade de numerador e denominador
    But 110 por cento não deve ser publicado como valor válido

  @fr-mt-6 @ac-mt-6
  Scenario: Manter uso de UTI como indicador suplementar
    Given 30 internações com uso de UTI entre 100 com estado conhecido
    When o uso de UTI for calculado
    Then o valor deve ser 30 por cento
    And o rótulo deve informar proporção suplementar
    But não deve informar ocupação de leitos

  @ch-07 @fr-mt-7 @ac-mt-7
  Scenario: Selecionar cobertura oficial de influenza elegível com escopo de população explícito
    Given duas observações oficiais da campanha de influenza 2026
    And a primeira foi publicada até "as_of" com população_scope = "NE,CO,S,SE"
    And a segunda seria publicada após "as_of"
    When a cobertura for selecionada
    Then a primeira observação deve ser retornada
    And campanha, grupos-alvo, numerador, denominador, atualização, fonte e população_scope devem aparecer
    And population_scope deve ser "NE,CO,S,SE" e nunca rotulado como "nationwide"
    And nenhuma cobertura de COVID-19 deve integrar o pacote MVP

  @ch-07 @fr-mt-7 @ac-mt-7
  Scenario: Influenza indisponível quando não publicada até "as_of"
    Given nenhuma observação oficial da campanha de influenza 2026 foi publicada até "as_of"
    When a cobertura for selecionada
    Then o estado deve ser "unavailable"
    And o motivo deve indicar "não publicada até cutoff"
    But numerador, denominador e valor não devem ser reportados
    And population_scope deve estar ausente ou não deve ser "BR"

  @ch-07 @fr-mt-7 @ac-mt-7
  Scenario: Manter observação 2026 regional como suplemento do golden
    Given uma observação elegível da campanha 2026 com population_scope = "NE,CO,S,SE"
    When o golden run exigir as seis métricas e ambas as séries
    Then a observação deve permanecer explicitamente regional e suplementar
    And nunca deve ser rotulada como "nationwide"
    And o golden run pode passar quando as outras cinco métricas forem nacionais e sem escopo

  @ch-07 @ch-13 @fr-mt-7 @fr-mt-10 @ac-mt-12
  Scenario: Rejeitar cobertura disponível sem escopo e preservar indisponibilidade válida
    Given cobertura de influenza disponível sem population_scope
    When o manifesto for validado
    Then a execução deve falhar com "influenza_scope_missing"
    Given cobertura de influenza indisponível sem population_scope
    Then o resultado indisponível deve continuar válido

  @ch-07 @ch-13 @fr-mt-10 @ac-mt-12
  Scenario: Rejeitar escopo em métrica nacional no carregamento
    Given evidência serializada de case_growth com population_scope
    When o manifesto for carregado
    Then deve falhar com "invalid_manifest_or_evidence"

  @ch-08 @fr-mt-8 @fr-mt-10 @nfr-mt-5 @ac-mt-8
  Scenario: Produzir série e gráfico diário fiéis
    Given que o snapshot cobre os 30 dias encerrados em "as_of"
    When a série diária for calculada e renderizada
    Then deve conter exatamente 30 datas consecutivas terminando em "as_of"
    And exatamente os 14 pontos mais recentes devem estar provisórios
    And dias cobertos sem casos devem possuir zero
    And cada ponto do gráfico deve corresponder à série
    And o gráfico deve conter título, período, unidade, fonte, watermark e descrição

  @ch-09 @fr-mt-9 @fr-mt-10 @nfr-mt-5 @ac-mt-9
  Scenario: Produzir série e gráfico mensal fiéis
    Given que o snapshot cobre os 12 meses completos anteriores
    When a série mensal for calculada e renderizada
    Then deve conter exatamente os 12 meses-calendário completos anteriores ao mês de "as_of"
    And meses cobertos sem casos devem possuir zero
    And cada ponto do gráfico deve corresponder à série

  @ch-10 @ch-13 @fr-mt-10 @nfr-mt-2 @ac-mt-10
  Scenario Outline: Propagar qualidade e proveniência
    Given completude "<completeness>" sem falha estrutural
    When uma métrica for empacotada
    Then o estado de qualidade deve ser "<state>"
    And fórmula, período, snapshot, watermark e fontes devem estar presentes

    Examples:
      | completeness | state       |
      | 95           | available   |
      | 80           | warning     |
      | 65           | unavailable |

  @ch-02 @ch-16 @nfr-mt-1 @nfr-mt-3 @nfr-mt-4 @ac-mt-11
  Scenario: Executar o pacote deterministicamente e somente leitura
    Given uma fixture conhecida e uma conexão DuckDB somente leitura
    When a fixture conhecida for calculada duas vezes
    Then os resultados analíticos devem ser idênticos
    And nenhuma consulta deve escrever no DuckDB
    And nenhum cálculo deve ser delegado ao LLM
    And cada execução deve concluir em até 5 segundos no ambiente documentado
