@draft @governance-delivery
Feature: Governança, transparência e entrega da PoC SRAG
  Os cenários derivam do spec.md versão 2.2.

  @ch-01 @ch-03 @ch-04 @ch-05 @ch-06 @ch-07 @ch-08 @ch-09 @ch-12 @fr-gd-1 @nfr-gd-1 @nfr-gd-2 @ac-gd-1
  Scenario: Aprovar somente o golden run completo
    Given uma execução live candidata à referência
    When o gate golden for aplicado
    Then as quatro métricas obrigatórias devem possuir valores reais e disponíveis
    And os dois indicadores suplementares devem estar presentes
    And os gráficos de 30 dias e 12 meses devem estar completos
    And deve existir ao menos uma notícia live recente válida
    And devem existir claims válidas de provedor/modelo aprovado
    And fontes, métodos, watermarks, qualidade, limitações e run ID devem estar presentes
    And o run bundle completo deve possuir hashes válidos e estar sanitizado

  @ch-13 @ch-15 @fr-gd-2 @nfr-gd-1 @ac-gd-2
  Scenario Outline: Separar degradação do golden run
    Given uma execução com "<failure>"
    When a suíte correspondente for executada
    Then o resultado deve ser "<result>"
    And a execução não deve ser selecionada como golden

    Examples:
      | failure          | result                           |
      | notícia ausente  | relatório quantitativo degradado |
      | provedor ausente | comentário factual determinístico |
      | métrica ausente  | seção indisponível com motivo     |
      | auditoria crítica | publicação interrompida          |

  @ch-13 @ch-15 @fr-gd-1 @ac-gd-10
  Scenario: Aceitar PNI scoped somente como suplemento não-nacional
    Given uma execução com observação PNI de influenza com escopo regional
    When o gate golden for aplicado
    Then a métrica de vacinação deve ser marcada como limitada
    And pode permanecer elegível quando as outras cinco métricas forem nacionais e sem escopo
    And deve renderizar como seção explicitamente não-nacional e limitada

  @ch-13 @ch-15 @fr-gd-1 @ac-gd-10
  Scenario: Rejeitar escopo nas outras métricas do golden
    Given uma execução com aumento de casos e population_scope regional
    When o gate golden for aplicado
    Then a execução não deve ser elegível ao golden run

  @ch-13 @fr-gd-1 @ac-gd-1
  Scenario: Rejeitar modelo servido em branco
    Given uma execução candidata com modelo servido vazio ou somente espaços
    When o gate golden for aplicado
    Then a execução deve falhar com "unapproved_or_unserved_model"

  @ch-07 @ch-12 @fr-gd-1 @ac-gd-11
  Scenario: Manter execução SIVEP oficial honesta sem fontes de suporte
    Given evidência oficial SIVEP com URL, hash, licença, linhas e mapeamento
    And CNES e PNI ausentes ou não verificados
    When o relatório oficial for produzido
    Then as métricas dependentes devem ficar indisponíveis com limitações
    And a execução não deve ser promovida a golden

  @ch-17 @fr-gd-3 @nfr-gd-3 @ac-gd-3
  Scenario: Reproduzir o quickstart determinístico
    Given um clone limpo e não autenticado
    When o avaliador seguir o quickstart determinístico
    Then nenhum segredo ou edição de código deve ser necessário
    And adaptador fake e RSS fixo devem ser usados
    And nenhuma chamada live de provedor ou RSS deve ocorrer
    And o HTML deve estar marcado como demonstração não-live

  @ch-03 @ch-17 @fr-gd-3 @ac-gd-4
  Scenario: Executar o quickstart live com uma credencial
    Given um clone limpo e somente "OPEN_ROUTER_API_KEY"
    When o avaliador seguir o quickstart live padrão
    Then os modelos solicitado e servido devem ser usados e auditados
    And Google News RSS deve ser consultado no momento da execução
    And um candidato ao golden run deve ser produzido

  @ch-17 @fr-gd-4 @ac-gd-5
  Scenario: Documentar e exemplificar a solução
    Given README e HTML sanitizado candidatos ao release
    When README e HTML de referência forem revisados
    Then devem cobrir setup, arquitetura, fontes, fórmulas, períodos e qualidade
    And devem cobrir agente, tools, provedores, notícias, auditoria, guardrails e privacidade
    And devem cobrir testes, quickstarts, limitações e interpretação
    And o HTML deve estar sanitizado e rotulado live ou não-live

  @ch-18 @fr-gd-5 @nfr-gd-4 @ac-gd-6
  Scenario: Entregar diagrama conceitual em PDF
    Given a fonte do diagrama compilada para PDF
    When o PDF renderizado for aberto
    Then deve estar legível
    And deve mostrar fontes de saúde, RSS, DuckDB, tools, LangGraph e provedores
    And deve mostrar validador, renderer, AuditSink, bundle, fluxos e limites sensíveis

  @ch-15 @ch-16 @ch-17 @fr-gd-6 @nfr-gd-2 @nfr-gd-5 @ac-gd-7
  Scenario: Preparar repositório público seguro
    Given um commit candidato ao release público
    When qualidade, CI, Gitleaks, staged files, histórico e ignores forem verificados
    Then pytest, Ruff e mypy devem passar
    And nenhum segredo, dado bruto, snapshot completo ou run local deve aparecer
    And nenhum registro clínico, payload bruto ou artigo integral deve aparecer
    And o documento restrito do desafio não deve estar versionado

  @ch-17 @fr-gd-7 @ac-gd-8
  Scenario: Verificar a entrega pública
    Given a URL GitHub do commit de release
    When uma pessoa sem autenticação clonar o repositório
    Then o quickstart determinístico deve funcionar sem edição
    And o run ID, as evidências e o HTML de exemplo devem ser localizáveis
    And a evidência do golden live sanitizado deve estar disponível

  @ch-17 @fr-gd-6 @fr-gd-7 @ac-gd-12
  Scenario: Validar evidência externa de release por SHA imutável
    Given release GitHub v2.2, asset de evidência e resultado de clone anônimo
    When o verificador externo receber a SHA candidata
    Then tag, SHA, asset e clone aprovado devem corresponder
    And divergência deve falhar fechada

  @ch-19 @fr-gd-8 @ac-gd-9
  Scenario: Respeitar o plano de cinco dias
    Given os quatro backlogs v2 e o backlog Stretch
    When os quatro arquivos tasks.md forem inspecionados
    Then devem existir exatamente 7 tarefas de dados
    And devem existir exatamente 7 tarefas de métricas
    And devem existir exatamente 8 tarefas agentivas
    And devem existir exatamente 6 tarefas de entrega
    And toda tarefa deve ter prioridade, dia, CH, requisito, AC, dependências e evidência
    And Stretch deve estar em arquivo separado e bloqueado
