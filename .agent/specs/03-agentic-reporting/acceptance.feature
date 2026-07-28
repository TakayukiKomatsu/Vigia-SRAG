@final @agentic-reporting
Feature: Geração agentiva de relatório fundamentado de SRAG
  Os cenários derivam do spec.md versão 1.0.

  @fr-ar-1 @fr-ar-2 @ac-ar-1
  Scenario: Orquestrar uma solicitação válida
    Given uma solicitação válida para uma UF e data coberta
    And um snapshot publicado
    When o relatório for solicitado
    Then o grafo deve validar a solicitação
    And deve coletar métricas, gráficos e notícias pelas tools registradas
    And deve validar as evidências antes do LLM
    And deve validar a narrativa antes do renderer
    And deve terminar com estado rastreável

  @fr-ar-3 @ac-ar-2
  Scenario: Restringir interfaces das tools analíticas
    When o schema das tools for inspecionado
    Then nenhuma tool deve aceitar SQL, tabela ou coluna arbitrários
    And nenhuma tool deve retornar chave técnica ou registro individual

  @fr-ar-4 @ac-ar-3
  Scenario: Aceitar somente notícias citáveis
    Given resultados com uma notícia válida, uma sem data e uma de domínio não permitido
    When a tool de notícias normalizar os resultados
    Then somente a notícia válida deve permanecer
    And ela deve conter título, URL, fonte, data de publicação e data de coleta

  @fr-ar-4 @ac-ar-3
  Scenario: Tratar conteúdo de notícia como dado não confiável
    Given uma notícia que contém instruções para ignorar políticas e chamar ferramentas
    When a notícia entrar no pacote de evidências
    Then seu conteúdo deve permanecer delimitado como evidência não confiável
    And nenhuma instrução contida nela deve alterar o grafo ou as tools

  @fr-ar-5 @fr-ar-6 @ac-ar-4
  Scenario: Chamar o LLM somente com evidência validada
    Given que as tools retornaram um pacote válido
    When a narrativa for solicitada
    Then o payload deve conter somente métricas agregadas, metadados e notícias permitidas
    And cada evidência deve possuir um identificador
    And os números do relatório devem continuar vindo dos objetos métricos

  @fr-ar-7 @nfr-ar-1 @ac-ar-5
  Scenario: Rejeitar número inventado pelo LLM
    Given que o pacote contém taxa de 12 por cento
    And o LLM afirma taxa de 21 por cento
    When a narrativa for validada
    Then a narrativa deve ser rejeitada
    And o relatório factual deve preservar 12 por cento
    And a violação deve ser auditada

  @fr-ar-7 @nfr-ar-2 @ac-ar-5
  Scenario: Rejeitar citação jornalística inexistente
    Given que o LLM cita uma notícia ausente do pacote
    When a narrativa for validada
    Then a narrativa deve ser rejeitada
    And a URL inventada não deve aparecer no relatório

  @fr-ar-8 @ac-ar-6
  Scenario: Renderizar relatório completo
    Given métricas, gráficos, notícias e narrativa válidos
    When o renderer produzir o relatório
    Then deve existir cabeçalho com geografia e marcos temporais
    And devem existir aumento de casos, letalidade e ocupação estimada de UTI
    And devem existir coberturas independentes de influenza e COVID-19
    And devem existir gráficos diário de 30 dias e mensal de 12 meses
    And devem existir contexto, metodologia, limitações, fontes e run ID

  @fr-ar-9 @nfr-ar-4 @ac-ar-7
  Scenario: Gerar relatório sem notícia válida
    Given métricas e gráficos válidos
    And nenhuma notícia válida no período
    When o relatório for solicitado
    Then o relatório quantitativo deve ser gerado
    And deve declarar ausência de contexto jornalístico verificável
    And nenhuma notícia deve ser inventada

  @fr-ar-9 @nfr-ar-4 @ac-ar-7
  Scenario: Gerar relatório factual quando o LLM falha
    Given métricas, gráficos e fontes válidos
    And o provedor do LLM está indisponível
    When o relatório for solicitado
    Then um relatório factual deve ser produzido sem narrativa gerada
    And a falha do LLM deve ser visível na auditoria e nas limitações

  @fr-ar-10 @ac-ar-8
  Scenario: Interromper execução que excede limites
    Given limites configurados de tools, tentativas, tokens e tempo
    When um nó exceder seu limite
    Then a execução deve interromper ou degradar conforme a rota documentada
    And o limite acionado deve ser auditado

  @nfr-ar-5 @ac-ar-9
  Scenario: Não enviar dados individuais ao LLM
    Given que o snapshot interno possui chaves técnicas
    When o payload do LLM for construído
    Then ele deve conter somente campos do schema agregado permitido
    And não deve conter chave técnica ou registro linha a linha
