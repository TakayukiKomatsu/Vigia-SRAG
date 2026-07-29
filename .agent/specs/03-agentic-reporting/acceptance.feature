@draft @agentic-reporting
Feature: Geração agentiva fundamentada do relatório Brasil de SRAG
  Os cenários derivam do spec.md versão 2.0.

  @ch-01 @ch-11 @ch-13 @fr-ar-1 @fr-ar-2 @ac-ar-1
  Scenario: Orquestrar uma solicitação Brasil válida
    Given request válido e snapshot publicado
    When o relatório for solicitado
    Then os dez nós documentados devem executar na ordem permitida
    And métricas, gráficos e notícias devem ser coletados por tools
    And evidências e comentário devem ser validados antes do renderer
    And a execução deve terminar com estado e run ID rastreáveis

  @ch-13 @fr-ar-1 @ac-ar-1
  Scenario: Rejeitar request antes das tools
    Given um "as_of" posterior ao watermark SIVEP
    When o relatório for solicitado
    Then a execução deve terminar em "validate_request"
    And nenhuma tool nem OpenAI deve ser chamada

  @ch-02 @ch-14 @fr-ar-3 @ac-ar-2
  Scenario: Restringir tools analíticas
    Given as tools de métricas e gráficos registradas no grafo
    When os schemas das tools de métricas e gráficos forem inspecionados
    Then nenhuma tool deve aceitar SQL, tabela, coluna ou código arbitrário
    And nenhuma tool deve retornar chave técnica ou registro individual
    And cada tool deve executar uma vez na rota normal

  @ch-03 @ch-14 @fr-ar-4 @ac-ar-3
  Scenario: Aceitar somente notícias atuais e citáveis
    Given um RSS com item válido, item stale, duplicata, item sem data e domínio não permitido
    When a tool aplicar query, locale, janela e allowlist fixos
    Then somente itens válidos e únicos devem permanecer
    And cada item deve conter título, fonte, URL final HTTP ou HTTPS, publicação e coleta
    And no máximo cinco itens devem ser retornados

  @ch-13 @fr-ar-4 @fr-ar-7 @ac-ar-4
  Scenario: Tratar notícia como dado não confiável
    Given uma notícia que manda ignorar políticas e chamar ferramentas
    When ela entrar na validação de evidência
    Then a instrução deve permanecer delimitada como conteúdo não confiável
    And não deve alterar grafo, tools, política ou prompt do sistema

  @ch-15 @fr-ar-5 @nfr-ar-5 @ac-ar-5
  Scenario: Congelar somente evidência agregada
    Given que o snapshot interno possui chaves técnicas e linhas clínicas
    When o EvidenceBundle e o payload OpenAI forem construídos
    Then devem conter somente métricas, séries, gráficos, fontes e notícias permitidas
    And cada evidência deve possuir ID
    And nenhuma chave técnica ou linha clínica deve aparecer

  @ch-01 @fr-ar-6 @ac-ar-6
  Scenario: Gerar claims OpenAI estruturadas
    Given EvidenceBundle válido e modelo configurado aprovado no smoke
    When o comentário for solicitado
    Then cada claim deve conter texto e IDs de evidência existentes
    And o modelo exato deve ser auditado
    And a saída deve respeitar no máximo 1200 tokens

  @ch-13 @fr-ar-7 @nfr-ar-1 @nfr-ar-2 @ac-ar-7
  Scenario Outline: Rejeitar claim sem fundamentação
    Given que a OpenAI devolveu uma claim com "<violation>"
    When o comentário for validado
    Then a claim deve ser rejeitada
    And a violação deve ser auditada
    And números, datas e URLs autoritativos devem permanecer inalterados

    Examples:
      | violation                 |
      | número inventado          |
      | citação inexistente       |
      | causalidade sem evidência |
      | recomendação clínica      |

  @ch-01 @ch-04 @ch-05 @ch-06 @ch-07 @ch-08 @ch-09 @fr-ar-8 @ac-ar-8
  Scenario: Renderizar o relatório completo
    Given métricas, suplementos, gráficos, notícia e claims válidos
    When o HTML for renderizado
    Then deve conter quatro métricas obrigatórias e dois indicadores suplementares
    And deve conter os gráficos de 30 dias e 12 meses
    And deve conter notícias, métodos, fontes, watermarks, qualidade e limitações
    And deve conter run ID e marcos temporais

  @ch-13 @fr-ar-9 @nfr-ar-4 @ac-ar-9
  Scenario Outline: Seguir a rota de falha documentada
    Given uma falha de "<component>"
    When o grafo aplicar a matriz de falhas
    Then o resultado deve ser "<result>"
    And não deve ser elegível ao golden run

    Examples:
      | component  | result                          |
      | métrica    | relatório degradado com motivo  |
      | notícia    | relatório quantitativo          |
      | OpenAI     | comentário factual determinístico |
      | gráfico    | publicação interrompida         |
      | auditoria  | publicação interrompida         |


  @ch-13 @ch-15 @fr-ar-9 @ac-ar-10
  Scenario: Renderizar métrica com escopo geográfico como limitada
    Given uma observação de campanha de vacinação com escopo regional NE/CO/S/SE
    When o relatório for renderizado
    Then a seção de vacinação deve ser claramente marcada como limitada
    And não deve ser rotulada como cobertura nacional
    And não deve ser elegível ao golden run
    And a limitação de escopo deve estar explícita nas fontes/métodos

  @ch-11 @ch-12 @ch-13 @fr-ar-10 @ac-ar-11
  Scenario: Aplicar limites e auditoria crítica
    Given limites configurados de chamadas, retry, notícias, tokens e 120 segundos
    When a execução atingir um limite ou evento crítico
    Then a rota exata deve ser aplicada
    And transição, decisão, duração e artefatos devem ser auditados
    And falha de evento crítico deve impedir OpenAI ou publicação
    And o bundle não deve conter segredo, linha clínica, payload bruto ou corpo integral de notícia

  @ch-16 @nfr-ar-3 @nfr-ar-6 @ac-ar-12
  Scenario: Executar deterministicamente sem chamadas live no CI
    Given OpenAI fake e RSS fixo
    When o mesmo EvidenceBundle for processado duas vezes
    Then claims e decisões normalizadas devem ser idênticas
    And nenhuma chamada OpenAI ou RSS live deve ocorrer
