@final @data-foundation
Feature: Fundação de dados públicos para relatórios de SRAG
  Os cenários derivam do spec.md versão 1.0.

  @fr-df-1 @ac-df-1
  Scenario: Produzir o mesmo contrato a partir de fonte ao vivo ou snapshot local
    Given que uma fonte ao vivo e um arquivo local possuem conteúdo equivalente
    When o operador executar a ingestão em cada modo
    Then os dois resultados devem possuir o mesmo schema canônico
    And as tabelas normalizadas devem possuir conteúdo equivalente
    And cada manifesto deve identificar o modo e a origem utilizados

  @fr-df-2 @fr-df-7 @ac-df-2
  Scenario: Tratar códigos ignorados e registros inválidos sem inventar valores
    Given um arquivo SRAG com código ignorado, data impossível e UF inválida
    When a ingestão for executada
    Then o código ignorado deve ser normalizado como desconhecido
    And não deve ser normalizado como resposta negativa
    And a data inválida deve ser contabilizada pelo código de qualidade correspondente
    And o registro com UF inválida deve ser enviado para quarentena

  @fr-df-3 @ac-df-3
  Scenario: Deduplicar registros segundo precedência documentada
    Given dois registros com a mesma chave técnica e atualizações diferentes
    When a ingestão for executada
    Then somente o registro vencedor pela regra de precedência deve permanecer
    And o manifesto deve contabilizar uma duplicata removida

  @fr-df-4 @nfr-df-3 @ac-df-4
  Scenario: Minimizar dados antes do consumo pelo agente
    Given um arquivo bruto que contém colunas identificáveis e colunas analíticas
    When o snapshot for publicado
    Then as tabelas analíticas devem conter somente campos da allowlist canônica
    And nenhum nome, documento ou endereço deve estar presente

  @fr-df-5 @fr-df-6 @ac-df-5
  Scenario: Publicar snapshot reproduzível
    Given que todas as fontes mínimas satisfazem seus contratos
    When a ingestão terminar
    Then devem existir arquivos Parquet normalizados
    And deve existir um banco DuckDB analítico
    And o manifesto deve ser escrito com status "published"
    And hashes, contagens, schemas e watermarks devem ser verificáveis

  @fr-df-8 @nfr-df-4 @ac-df-6
  Scenario: Preservar último snapshot após falha estrutural
    Given que existe um snapshot publicado
    And a nova fonte não contém uma coluna crítica
    When o operador tentar atualizar os dados
    Then a execução deve falhar com código de schema incompatível
    And nenhum snapshot parcial deve ser publicado
    And o snapshot anterior deve continuar selecionável

  @fr-df-6 @ac-df-7
  Scenario: Expor qualidade e atualização de todas as famílias de dados
    Given uma ingestão concluída com dados SRAG, CNES, influenza e COVID-19
    When o manifesto for consultado
    Then ele deve informar o watermark de cada família
    And deve informar completude dos campos críticos
    And deve informar quantidades aceitas, rejeitadas e deduplicadas

  @nfr-df-2 @ac-df-8
  Scenario: Produzir hashes determinísticos para entradas idênticas
    Given entradas idênticas e a mesma versão das regras de normalização
    When a ingestão for executada duas vezes
    Then os hashes das tabelas normalizadas devem ser idênticos
    And timestamps de execução não devem alterar o conteúdo normalizado
