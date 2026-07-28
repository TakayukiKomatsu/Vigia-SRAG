@final @metrics
Feature: Métricas e gráficos epidemiológicos de SRAG
  Os cenários derivam do spec.md versão 1.0.

  Background:
    Given que existe um snapshot canônico publicado

  @fr-mt-1 @ac-mt-1
  Scenario Outline: Calcular pacote para geografia suportada
    When o pacote for solicitado para "<geography>" em uma data coberta
    Then todas as saídas devem identificar "<geography>"
    And todas as saídas devem identificar o snapshot e a data de referência

    Examples:
      | geography |
      | BR        |
      | SP        |

  @fr-mt-1 @ac-mt-1
  Scenario: Rejeitar UF inválida
    When o pacote for solicitado para "XX"
    Then a solicitação deve falhar antes de consultar métricas
    And nenhuma substituição silenciosa por Brasil deve ocorrer

  @fr-mt-2 @ac-mt-2
  Scenario: Calcular aumento com denominador positivo
    Given que houve 100 casos nos sete dias anteriores
    And houve 125 casos nos sete dias atuais
    When a taxa de aumento for calculada
    Then o valor deve ser 25 por cento
    And o estado deve ser "available"

  @fr-mt-2 @ac-mt-2
  Scenario: Representar ausência contínua de casos
    Given que houve zero casos nas duas janelas de sete dias
    When a taxa de aumento for calculada
    Then o valor deve ser zero por cento
    And o estado deve ser "stable_zero"

  @fr-mt-2 @ac-mt-2
  Scenario: Não produzir infinito quando surgem casos
    Given que houve zero casos na janela anterior
    And houve casos na janela atual
    When a taxa de aumento for calculada
    Then nenhum percentual infinito deve ser retornado
    And o estado deve ser "new_activity"

  @fr-mt-3 @ac-mt-3
  Scenario: Calcular letalidade somente com evoluções conhecidas
    Given 10 óbitos, 90 altas e 20 evoluções desconhecidas
    When a letalidade for calculada
    Then o valor deve ser 10 por cento
    And a qualidade deve informar 20 exclusões por evolução desconhecida
    And a definição deve identificar letalidade hospitalar

  @fr-mt-4 @fr-mt-10 @ac-mt-4
  Scenario: Calcular ocupação estimada de UTI por SRAG
    Given 150 paciente-dias válidos de SRAG em UTI
    And 1000 leito-dias compatíveis do CNES
    When a ocupação for calculada
    Then o valor deve ser 15 por cento
    And o numerador deve ser 150 paciente-dias
    And o denominador deve ser 1000 leito-dias
    And a proporção de uso de UTI não deve substituir esse resultado

  @fr-mt-4 @fr-mt-10 @ac-mt-4
  Scenario: Não chamar proporção de uso de UTI de ocupação
    Given que existem registros de uso de UTI
    And não existe capacidade CNES compatível
    When o pacote for calculado
    Then a ocupação deve estar indisponível com motivo
    And a proporção de uso pode aparecer como indicador auxiliar
    But ela não deve possuir o rótulo de ocupação de leitos

  @fr-mt-5 @ac-mt-5
  Scenario: Exibir as duas coberturas sem combiná-las
    Given cobertura válida de influenza para sua população-alvo
    And cobertura válida de COVID-19 para seu esquema e população elegível
    When o pacote for calculado
    Then devem existir indicadores independentes de influenza e COVID-19
    And cada indicador deve conter período, público-alvo, numerador, denominador e fonte
    And nenhuma média entre as coberturas deve ser calculada

  @fr-mt-5 @ac-mt-5
  Scenario: Manter uma cobertura quando a outra está ausente
    Given cobertura válida de influenza
    And nenhuma cobertura aplicável de COVID-19
    When o pacote for calculado
    Then influenza deve permanecer disponível
    And COVID-19 deve estar indisponível com motivo

  @fr-mt-6 @fr-mt-7 @ac-mt-6
  Scenario: Produzir séries temporais completas
    Given que o snapshot cobre os últimos 12 meses
    When as séries forem calculadas
    Then a série diária deve conter exatamente 30 datas consecutivas
    And a série mensal deve conter exatamente 12 meses consecutivos
    And períodos cobertos sem casos devem possuir valor zero

  @fr-mt-6 @fr-mt-7 @ac-mt-9
  Scenario: Não preencher período fora da cobertura do snapshot
    Given que o snapshot cobre somente 15 dos últimos 30 dias
    When as séries forem calculadas
    Then a série diária deve estar indisponível com motivo de cobertura insuficiente
    And pontos fora do watermark não devem receber valor zero
    And o renderer não deve produzir o gráfico diário com pontos artificiais

  @fr-mt-8 @ac-mt-7
  Scenario: Retornar proveniência e qualidade para cada métrica
    When um pacote de métricas for calculado
    Then cada métrica deve informar fórmula e versão
    And deve informar snapshot, período e geografia
    And deve informar numerador, denominador e qualidade quando disponível
    And deve informar motivo estruturado quando indisponível

  @fr-mt-9 @nfr-mt-5 @ac-mt-8
  Scenario: Gerar gráficos fiéis às séries
    When os gráficos forem renderizados
    Then devem existir um gráfico diário e um mensal
    And cada ponto desenhado deve corresponder à série estruturada
    And cada gráfico deve conter título, período, unidade, fonte e descrição textual
