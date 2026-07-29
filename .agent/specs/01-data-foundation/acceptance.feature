@draft @data-foundation
Feature: Fundação de dados públicos fixados para relatórios Brasil de SRAG
  Os cenários derivam do spec.md versão 2.0.

  @ch-10 @ch-12 @fr-df-1 @nfr-df-2 @ac-df-1
  Scenario: Bloquear finalização sem contratos e fixture verificados
    Given que uma das quatro fontes possui metadado ou recurso não verificado
    When a prontidão do SDD for avaliada
    Then o spec deve permanecer com status "DRAFT"
    And o bloqueio e sua evidência devem constar no anexo de contratos
    But nenhum valor pode ser inferido para completar o contrato

  @ch-10 @fr-df-2 @ac-df-2
  Scenario: Carregar somente snapshots oficiais fixados
    Given recursos locais verificados de SIVEP 2025 e 2026, CNES, IBGE e PNI influenza 2026
    When a preparação de dados for executada
    Then cada saída deve identificar recurso, recuperação, watermark e SHA-256
    And nenhuma fonte de saúde deve ser consultada ao vivo pelo runtime do relatório

  @ch-10 @fr-df-3 @fr-df-4 @ac-df-3
  Scenario: Normalizar e deduplicar sem inventar valores
    Given registros com código ignorado, data impossível e chave duplicada
    When a preparação de dados for executada
    Then o código ignorado deve permanecer desconhecido e não negativo
    And a data inválida deve seguir a matriz de campo e possuir código de motivo
    And deve vencer a atualização mais recente, depois a maior completude e o desempate estável
    And exclusões e duplicatas devem ser contabilizadas

  @ch-10 @fr-df-4 @ac-df-3
  Scenario: Quarentenar somente falhas estruturais
    Given um registro sem estrutura mínima e outro com campo não crítico inválido
    When a preparação de dados for executada
    Then o registro estrutural deve ir para quarentena
    And o campo não crítico deve ser anulado quando a matriz assim determinar
    And ambos os motivos devem ser contabilizados separadamente

  @ch-15 @fr-df-5 @nfr-df-3 @ac-df-4
  Scenario: Minimizar antes da fronteira agentiva
    Given entradas que contêm chaves técnicas e campos clínicos linha a linha
    When o DuckDB analítico for publicado
    Then nenhuma chave técnica ou linha clínica deve estar disponível ao agente
    And somente agregados e metadados permitidos devem atravessar a fronteira

  @ch-02 @ch-12 @ch-16 @fr-df-6 @nfr-df-1 @nfr-df-2 @ac-df-5
  Scenario: Publicar DuckDB e manifestos determinísticos
    Given entradas idênticas e as mesmas versões de regra
    When duas preparações forem concluídas
    Then o DuckDB deve ser consultável somente leitura
    And o conteúdo normalizado e seus hashes devem ser idênticos
    And timestamps de execução não devem alterar os hashes analíticos

  @ch-10 @ch-13 @fr-df-7 @ac-df-6
  Scenario Outline: Aplicar o estado de completude
    Given uma métrica com "<completeness>" por cento de campos dependentes válidos
    When sua qualidade for avaliada
    Then seu estado deve ser "<state>"

    Examples:
      | completeness | state       |
      | 95           | available   |
      | 80           | warning     |
      | 65           | unavailable |

  @ch-10 @ch-13 @fr-df-7 @fr-df-8 @ac-df-6 @ac-df-7
  Scenario: Bloqueio estrutural sobrepor porcentagem
    Given um último snapshot válido
    And um candidato com 95 por cento de completude e coluna crítica ausente
    When a publicação for tentada
    Then o candidato deve ser rejeitado por schema incompatível
    And nenhum snapshot parcial deve ser selecionado
    And o último snapshot válido deve permanecer selecionável

  @ch-10 @ch-16 @ch-19 @nfr-df-4 @ac-df-8
  Scenario: Medir o volume representativo
    Given uma entrada SIVEP com pelo menos 165000 linhas
    When o benchmark de preparação for executado
    Then a execução deve concluir sem perda silenciosa
    And deve registrar tempo, pico de memória e contexto da máquina
