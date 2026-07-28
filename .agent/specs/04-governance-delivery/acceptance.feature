@final @governance-delivery
Feature: Governança, transparência e entrega da PoC SRAG
  Os cenários derivam do spec.md versão 1.0.

  @fr-gd-1 @fr-gd-2 @ac-gd-1
  Scenario: Auditar uma execução bem-sucedida
    Given uma solicitação válida e fontes disponíveis
    When um relatório for publicado
    Then deve existir um run ID único
    And a trilha deve conter início, validação, snapshot, nós, tools, guardrails, evidências e publicação
    And deve vincular parâmetros, versões, snapshots, notícias e hashes dos artefatos

  @fr-gd-3 @nfr-gd-2 @ac-gd-2
  Scenario: Sanitizar a trilha de auditoria
    Given dados internos que possuem chave técnica e configuração com segredo
    When eventos forem persistidos
    Then somente campos permitidos por tipo de evento devem ser gravados
    And nenhum segredo, chave técnica, registro clínico ou payload bruto deve aparecer

  @fr-gd-4 @ac-gd-3
  Scenario: Consultar decisões por run ID
    Given uma execução concluída
    When o avaliador consultar sua trilha pelo run ID
    Then os eventos devem aparecer em ordem temporal
    And cada decisão deve identificar componente e versão
    And a integridade dos artefatos deve ser validada por hash

  @fr-gd-1 @nfr-gd-1 @ac-gd-10
  Scenario: Não publicar relatório sem evento crítico
    Given que o store de auditoria não consegue persistir um evento crítico
    When o grafo tentar avançar para o LLM ou publicação
    Then a execução deve ser interrompida
    And nenhum relatório deve ser marcado como auditável e publicado

  @fr-gd-5 @fr-gd-9 @nfr-gd-3 @ac-gd-4
  Scenario: Reproduzir a demonstração pelo quickstart
    Given um ambiente limpo com Python suportado
    And as dependências e configurações documentadas
    When o avaliador seguir o quickstart com snapshots demonstrativos
    Then um relatório deve ser gerado sem editar o código
    And o relatório deve mostrar watermarks dos snapshots usados

  @fr-gd-6 @ac-gd-5
  Scenario: Documentar decisões e limitações avaliadas
    When o README for revisado
    Then deve explicar arquitetura, instalação, configuração e fluxo de dados
    And deve explicar fórmulas, fontes, qualidade, guardrails e tratamento sensível
    And deve explicar auditoria, testes, limitações e reprodução da demo

  @fr-gd-7 @nfr-gd-4 @ac-gd-6
  Scenario: Entregar o diagrama conceitual em PDF
    When o PDF de arquitetura for aberto
    Then ele deve estar legível
    And deve mostrar orquestrador, tools, LLM, DuckDB e auditoria
    And deve mostrar fontes SRAG, CNES, vacinação e notícias
    And deve mostrar interações e o limite de dados sensíveis

  @fr-gd-8 @ac-gd-7
  Scenario: Preparar repositório público sem material indevido
    When os arquivos preparados para Git forem inspecionados
    Then nenhum segredo deve estar presente
    And dados brutos, snapshots completos, logs e saídas locais devem estar ignorados
    And configurações de exemplo não devem conter credenciais reais

  @fr-gd-10 @ac-gd-8
  Scenario Outline: Validar relatório fim a fim
    Given fontes ou snapshots válidos para "<geography>"
    When o smoke test gerar o relatório
    Then devem existir aumento, letalidade e ocupação estimada de UTI
    And devem existir coberturas independentes de influenza e COVID-19
    And devem existir os gráficos diário de 30 dias e mensal de 12 meses
    And devem existir fontes, limitações, run ID e trilha íntegra
    And qualquer indisponibilidade deve possuir motivo verificável

    Examples:
      | geography |
      | BR        |
      | SP        |

  @nfr-gd-5 @ac-gd-9
  Scenario: Passar verificações de qualidade do projeto
    When estilo, tipagem e testes documentados forem executados
    Then todas as verificações devem terminar sem erro
