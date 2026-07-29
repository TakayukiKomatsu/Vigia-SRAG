# Redesenho compliance-first do SDD da PoC de SRAG

> Status: aprovado para reescrita dos SDDs  
> Data: 2026-07-28  
> Prazo controlador: cinco dias  
> Escopo geográfico do MVP: Brasil  
> Artefatos derivados a revisar: `.agent/specs/01-*` até `.agent/specs/04-*`

## 1. Decisão executiva

A PoC será uma fatia vertical pequena, reproduzível e completa, otimizada para
demonstrar todos os requisitos obrigatórios do desafio em cinco dias. Nenhuma
funcionalidade opcional pode começar antes de o relatório de referência passar
por todos os critérios de aceitação obrigatórios.

O MVP mantém:

- dados reais e oficiais tratados e carregados em DuckDB;
- quatro métricas obrigatórias com valor disponível;
- dois gráficos obrigatórios;
- um orquestrador LangGraph com tools tipadas;
- consulta de notícias no momento da execução;
- comentários gerados pela API da OpenAI e vinculados às evidências;
- guardrails, trilha de auditoria e proteção de dados;
- relatório HTML, README, PDF conceitual de arquitetura e repositório público.

O MVP remove ou adia:

- filtro por UF;
- segundo indicador vacinal;
- ingestão ao vivo de todas as fontes epidemiológicas;
- paridade live/local, migração de schema e rollback;
- abstração para múltiplos provedores;
- PDF do relatório;
- consulta avançada de auditoria.

Esses itens ficam em um backlog de extensão e não aparecem como tarefas
obrigatórias dos cinco dias.

## 2. Rastreabilidade do desafio

Os SDDs versão 2.0 usarão estes IDs estáveis como requisitos de origem:

| ID | Obrigação do desafio | Evidência obrigatória no MVP |
|---|---|---|
| CH-01 | Gerar relatório automatizado com dados, notícias e explicações | `report.html` produzido pelo LangGraph |
| CH-02 | Agente consultar banco de dados | tool tipada de métricas consulta DuckDB somente leitura |
| CH-03 | Agente consultar notícias de SRAG em tempo real | tool consulta Google News RSS durante a execução |
| CH-04 | Taxa de aumento de casos | comparação de duas semanas epidemiológicas estabilizadas |
| CH-05 | Taxa de mortalidade | óbitos por SRAG por 100 mil habitantes |
| CH-06 | Taxa de ocupação de UTI | proxy explicitamente rotulado de pressão de SRAG sobre capacidade registrada |
| CH-07 | Taxa de vacinação da população | cobertura de influenza na população-alvo oficial da campanha 2026 |
| CH-08 | Gráfico diário de 30 dias | 30 pontos diários, com período recente marcado provisório |
| CH-09 | Gráfico mensal de 12 meses | 12 meses-calendário completos |
| CH-10 | Tratar dados reais problemáticos | allowlist, normalização, deduplicação, quarentena e qualidade quantificada |
| CH-11 | Escolha de arquitetura | módulos pequenos, DuckDB, tools tipadas e LangGraph controlado |
| CH-12 | Governança e transparência | run bundle reproduzível e eventos de decisão |
| CH-13 | Guardrails | validações de entrada, tools, evidência, linguagem e limites |
| CH-14 | Uso de tools | tools separadas de métricas, gráficos e notícias |
| CH-15 | Tratamento de dados sensíveis | apenas agregados chegam ao agente, LLM, relatório e logs |
| CH-16 | Clean Code | pacote Python tipado, módulos focados, lint, type-check e testes |
| CH-17 | Repositório público e documentação | URL pública verificada e README completo |
| CH-18 | PDF conceitual da arquitetura | PDF mostra orquestrador, tools, LLM, banco e fontes |
| CH-19 | Entrega em cinco dias | tarefas Must priorizadas por dia; Stretch isolado |

O arquivo `.agent/specs/traceability.md` mapeará cada `CH-*` para `FR-*`,
`AC-*` e `T-*`. Referências por intervalo, como `FR-X-1..FR-X-4`, não serão
permitidas.

## 3. Fontes e contrato de dados

### 3.1 Fontes do MVP

O MVP usa snapshots locais obtidos de fontes oficiais:

1. SIVEP-Gripe/Open DataSUS: CSVs dos anos epidemiológicos 2025 e 2026,
   necessários para cobrir os últimos 12 meses.
2. CNES: competência mensal completa mais recente com leitos de UTI
   compatíveis.
3. IBGE: estimativa oficial de população do Brasil aplicável ao ano de
   referência.
4. PNI/Ministério da Saúde: observação oficial mais recente da cobertura da
   campanha de influenza 2026 para a população-alvo.

A consulta de notícias é a única aquisição ao vivo durante a geração do
relatório.

### 3.2 Gate antes de `FINAL`

Os SDDs 01–03 voltam a `DRAFT`. Antes de receberem status `FINAL`, um anexo de
contratos de fonte deve registrar para cada entrada:

- URL oficial e identificador do recurso;
- licença, data de recuperação e watermark;
- versão do dicionário/schema;
- tamanho e SHA-256 do arquivo;
- contagem de linhas;
- encoding e delimitador;
- campos de origem e seus campos canônicos;
- semântica geográfica e temporal;
- códigos válidos, desconhecidos e ignorados;
- regra de deduplicação;
- política de falha e staleness.

O anexo e uma fixture real reduzida devem ser verificados antes do primeiro
commit de implementação. O SDD 04 recebe status `FINAL` somente depois de seus
três contratos upstream estarem congelados.

### 3.3 Modelo canônico mínimo

O modelo preserva apenas os campos necessários:

- SRAG: chave de notificação, data de atualização, início dos sintomas,
  internação, entrada e saída de UTI, evolução, data da evolução, UF de
  residência e UF da internação;
- CNES: competência, UF do estabelecimento, código/categoria de UTI, leitos
  existentes compatíveis;
- população: ano, geografia e população oficial;
- vacinação: campanha, imunobiológico, grupos-alvo, período, geografia de
  residência, numerador, denominador, cobertura publicada, atualização e
  fonte.

O runtime do agente não recebe a chave técnica nem qualquer linha clínica.

## 4. Qualidade e minimização

As regras obrigatórias são:

- desconhecido e ignorado nunca viram resposta negativa;
- valores clínicos ausentes não são imputados;
- datas impossíveis, futuras ou com ordem temporal inválida são anuladas ou
  rejeitadas conforme matriz de campo, sempre com código de motivo;
- registros estruturalmente inválidos vão para quarentena;
- duplicatas são resolvidas pela chave de notificação, atualização mais
  recente, maior completude e, por fim, um desempate estável;
- todas as exclusões são contadas por fonte, campo, métrica e motivo;
- o agente, a OpenAI, os logs e o relatório recebem somente agregados.

Cada métrica calcula a completude dos campos dos quais depende:

- `>= 90%`: valor publicado normalmente;
- `>= 70%` e `< 90%`: valor publicado com aviso proeminente;
- `< 70%`: métrica indisponível.

Coluna obrigatória ausente, período não coberto ou hash inválido bloqueia o
snapshot ou a seção afetada independentemente da porcentagem. Esses limiares
são guardrails da PoC, não padrões epidemiológicos oficiais. O snapshot da
demonstração de referência deve deixar disponíveis todas as métricas e séries.

## 5. Contrato temporal

`as_of` é a data solicitada para o relatório. O sistema registra separadamente
`generated_at`, `as_of`, watermark de cada fonte e período efetivo de cada
resultado.

- A semana epidemiológica segue o calendário epidemiológico brasileiro,
  domingo a sábado.
- `generated_at` é o instante UTC da execução.
- `as_of` usa por padrão a maior data válida de início dos sintomas no snapshot
  SIVEP. Uma data solicitada posterior a esse watermark é rejeitada.
- A semana estabilizada de referência é a última semana completa cujo término
  ocorreu pelo menos 14 dias antes de `as_of`.
- Pontos recentes continuam visíveis no gráfico diário, mas recebem estado
  `provisional`.
- Dados de fontes com competências diferentes não são forçados a compartilhar
  o mesmo período.
- A janela de notícias termina em `generated_at`, não no watermark
  epidemiológico, para que o contexto jornalístico seja atual.

## 6. Métricas

### 6.1 Aumento de casos

Usa a data válida de início dos sintomas:

```text
growth = (cases_reference_week - cases_previous_week)
         / cases_previous_week * 100
```

A semana de referência e a anterior são semanas epidemiológicas completas e
consecutivas, encerradas no cutoff estabilizado.

- denominador positivo: percentual, inclusive negativo;
- ambas as semanas com zero: `stable_zero`, valor `0`;
- anterior zero e atual positiva: `new_activity`, sem percentual infinito.

O objeto expõe `current_cases`, `previous_cases` e `delta_cases`; o campo
`numerator` matemático, quando presente, é `delta_cases`.

### 6.2 Mortalidade populacional por SRAG

É a métrica obrigatória de mortalidade:

```text
mortality = SRAG_deaths_in_latest_4_stabilized_epi_weeks
            / official_population * 100_000
```

Conta apenas óbitos classificados como decorrentes de SRAG e com data de
evolução dentro das quatro semanas. Óbito por outra causa não entra no
numerador. O relatório mostra período, população, unidade, numerador,
denominador e fonte IBGE.

### 6.3 Letalidade hospitalar suplementar

O indicador suplementar usa internações com início dos sintomas nas quatro
semanas epidemiológicas completas encerradas pelo menos 28 dias antes de
`as_of`:

```text
fatality = SRAG_deaths / hospitalizations_with_known_outcome * 100
```

Evoluções desconhecidas ficam fora do denominador, são quantificadas e
aparecem como limitação. O indicador nunca recebe o rótulo simples
“mortalidade”.

### 6.4 Pressão estimada de SRAG sobre capacidade de UTI

É o proxy obrigatório para o item de ocupação:

```text
icu_pressure = valid_SRAG_ICU_patient_days
               / compatible_CNES_existing_ICU_bed_days * 100
```

O período é a competência completa mais recente coberta por SIVEP e CNES.
Paciente-dias resultam da interseção entre entrada/saída válidas e o mês.
Permanência com saída desconhecida é excluída e contada. O denominador usa
leitos existentes das categorias adultas, pediátricas ou neonatais definidas
no anexo, sem misturar “leito SUS” como sinônimo de disponibilidade.

O relatório chama o resultado de “pressão estimada de SRAG sobre a capacidade
registrada de UTI” e explica que não representa ocupação observada por todas as
causas. Valor acima de 100% torna a métrica indisponível por incompatibilidade,
em vez de publicar um percentual válido.

O percentual de internações SRAG com uso de UTI é exibido somente como
indicador suplementar.

### 6.5 Cobertura vacinal contra influenza

A métrica obrigatória usa a observação oficial mais recente da campanha 2026,
publicada até `as_of`:

```text
coverage = valid_influenza_doses_for_target_groups
           / official_target_population * 100
```

O sistema não inventa um denominador de população geral e não recalcula
esquemas a partir de linhas clínicas. O relatório identifica campanha,
grupos-alvo, residência, numerador, denominador, data de atualização e fonte.
Cobertura de COVID-19 fica no backlog Stretch.

## 7. Séries e gráficos

- Diário: exatamente 30 dias consecutivos terminando em `as_of`, por início dos
  sintomas. Dias cobertos sem caso recebem zero. Os 14 dias anteriores a
  `as_of` recebem marca visual e textual de provisórios.
- Mensal: exatamente os 12 meses-calendário completos anteriores ao mês de
  `as_of`, por início dos sintomas.

Gráficos são gerados deterministicamente a partir das séries estruturadas e
contêm título, período, unidade, fonte, watermark e descrição textual. Não há
preenchimento com zero fora de períodos comprovadamente cobertos.

## 8. Arquitetura do código

O pacote Python usa módulos pequenos orientados por responsabilidade:

```text
srag_report/
  config.py
  domain/
  data/
  metrics/
  tools/
  agent/
  reporting/
  audit/
  cli.py
```

- `domain`: requests, métricas, séries, evidências e eventos;
- `data`: contratos, limpeza, qualidade, manifestos e DuckDB;
- `metrics`: fórmulas e consultas determinísticas;
- `tools`: interfaces estreitas para métricas, gráficos e notícias;
- `agent`: estado e nós LangGraph, OpenAI e validação;
- `reporting`: HTML, gráficos e apresentação factual;
- `audit`: `AuditSink` e implementação JSONL;
- `cli.py`: preparação dos dados, geração do relatório e inspeção da execução.

Domínio não depende de infraestrutura. Tools não aceitam SQL, tabela, coluna,
URL ou prompt arbitrário.

## 9. Fluxo agentivo

O grafo controlado executa:

1. `validate_request`;
2. `select_snapshot`;
3. `collect_metrics`;
4. `render_charts`;
5. `search_news`;
6. `validate_evidence`;
7. `generate_commentary`;
8. `validate_commentary`;
9. `render_report`;
10. `finalize_run`.

A auditoria participa desde o primeiro nó por uma interface `AuditSink`; não
é implementada em uma especificação posterior ao grafo.

### 9.1 Tools

- metrics tool: Brasil, `as_of` e snapshot tipados; retorna métricas e qualidade;
- charts tool: recebe somente séries validadas; retorna artefatos e hashes;
- news tool: consulta Google News RSS no momento da execução.

A consulta RSS usa locale português/Brasil e a consulta fixa
`("SRAG" OR "síndrome respiratória aguda grave") when:14d`. A allowlist inicial
aceita Ministério da Saúde, Fiocruz, Agência Brasil, G1, Estadão e Folha de
S.Paulo, identificados pelo domínio final ou pelo campo `source` do feed. Cada
item aceito possui título, fonte, URL HTTP(S), publicação e coleta. Redirects
são resolvidos apenas para destinos HTTP(S) e um domínio fora da allowlist
descarta o item. O golden run exige ao menos um item válido.

### 9.2 OpenAI e fundamentação

Há um único adaptador da API da OpenAI. O nome exato do modelo vem da
configuração e é registrado na auditoria. O SDD 03 só recebe status `FINAL`
depois de registrar um modelo padrão que tenha passado por um smoke test de
saída estruturada. Testes usam um fake determinístico.

A OpenAI recebe apenas o `EvidenceBundle` agregado e devolve claims
estruturados. Cada claim referencia IDs de métricas e notícias. Ela não fornece
URLs, não substitui números renderizados e não controla gráficos.

O validador rejeita:

- ID ausente;
- número sem associação à evidência correta;
- citação inexistente;
- diagnóstico ou recomendação clínica;
- causalidade não sustentada;
- instrução vinda do conteúdo de notícia.

Números, gráficos, URLs e datas no documento vêm dos objetos validados. Falha
de geração ou validação usa texto factual determinístico.

### 9.3 Limites

- uma chamada normal por tool;
- uma tentativa adicional apenas para falha transitória de notícia ou OpenAI;
- no máximo cinco notícias aceitas;
- no máximo 1.200 tokens de saída da OpenAI;
- timeout global de 120 segundos;
- janela de notícias fixa de 14 dias no MVP.

## 10. Auditoria

Cada execução cria:

```text
runs/<run_id>/
  request.json
  evidence.json
  audit.jsonl
  charts/
  report.html
  manifest.json
```

Eventos registram transições, tool calls, entradas e saídas resumidas,
guardrails, evidências, versões, decisões, falhas, duração, URLs, hashes e
artefatos. `evidence.json` preserva exatamente os agregados usados para aceitar
a narrativa.

Não são persistidos:

- registros clínicos ou chaves técnicas;
- segredos;
- payload bruto de fonte;
- corpo integral de notícia;
- objetos arbitrários fora da allowlist de cada evento.

Falha ao persistir evento crítico antes da OpenAI ou da publicação interrompe
a execução.

## 11. Falhas e aceitação

Em execução normal:

- métrica indisponível produz seção explícita com motivo;
- notícia indisponível produz relatório quantitativo;
- OpenAI indisponível ou inválida produz comentário factual determinístico.

Falhas de request, hash, snapshot ou estrutura de evidência terminam antes da
OpenAI. Falha de gráfico, renderer ou auditoria crítica impede publicação.

O relatório de referência da entrega tem regra mais estrita. Ele só passa se
contiver:

- as quatro métricas obrigatórias com valores reais;
- letalidade e uso de UTI suplementares;
- os dois gráficos completos;
- ao menos uma notícia recente coletada ao vivo;
- claims válidos produzidos pela OpenAI;
- fontes, métodos, watermarks, limitações e run ID;
- run bundle íntegro e sanitizado.

Testes de degradação são separados e não podem substituir o golden run.

## 12. Verificação

A suíte inclui:

- unitários de fórmulas, períodos, denominadores, qualidade e datas;
- contratos de fontes e schemas das tools;
- integração sobre fixture DuckDB real reduzida;
- grafo com OpenAI fake e RSS fixo;
- prompt injection, SQL arbitrário, URL inválida, vazamento de campo e citação
  inventada;
- golden end-to-end com valores e artefatos conhecidos;
- degradação de notícia, OpenAI, métrica e audit sink;
- execução live manual antes da publicação;
- quickstart determinístico em clone limpo e não autenticado;
- quickstart live usando somente uma credencial `OPENAI_API_KEY`.

Chamadas live não rodam no CI determinístico.

## 13. Entrega

O repositório público inclui:

- pacote Python e `pyproject.toml` com dependências fixadas;
- configuração de exemplo sem segredo;
- fixtures pequenas permitidas;
- relatório HTML sanitizado de referência;
- README com quickstart, arquitetura, fontes, fórmulas, qualidade, agente,
  auditoria, guardrails, privacidade, testes e limitações;
- diagrama-fonte e PDF conceitual legível;
- `pytest`, Ruff, mypy, GitHub Actions e secret scan com Gitleaks.

O README separa dois caminhos. O quickstart determinístico usa OpenAI fake e
RSS fixo, não requer credencial e marca seu relatório como demonstração não
live. O quickstart live requer somente `OPENAI_API_KEY`, consulta notícias no
momento da execução e produz um candidato a golden run.

O release só termina depois que uma pessoa consegue clonar o repositório
publicamente, executar o caminho determinístico sem editar código, localizar o
run ID e suas evidências e verificar o relatório live de referência já
sanitizado no repositório.

Não entram no Git: documento restrito do desafio, `.env`, dados brutos,
snapshots completos, run bundles locais, segredos ou `.superpowers/`.

## 14. Reescrita dos SDDs

Os quatro pacotes existentes permanecem, mas recebem versão 2.0:

1. `01-data-foundation`: contratos oficiais, qualidade, minimização, manifesto
   e DuckDB; somente snapshot local no MVP.
2. `02-epidemiological-metrics`: quatro métricas obrigatórias, dois
   suplementares, períodos e gráficos Brasil.
3. `03-agentic-reporting`: tools, RSS, LangGraph, OpenAI, validação, audit sink,
   JSONL e HTML.
4. `04-governance-delivery`: golden run, testes transversais, README, CI,
   arquitetura PDF e publicação pública.

Cada tarefa Must terá:

- um ou mais IDs `CH-*`;
- IDs explícitos `FR-*` ou `AC-*`;
- prioridade;
- dependências;
- dia-alvo;
- resultado verificável.

O conjunto Must terá no máximo 30 tarefas pequenas. Itens Stretch ficam em
arquivo separado e não participam da aceitação do MVP.

## 15. Cronograma

- Dia 1: congelar contratos, criar pacote e carregar as quatro fontes no
  DuckDB.
- Dia 2: quatro métricas, dois suplementares, qualidade, séries e gráficos.
- Dia 3: tools, LangGraph, RSS, OpenAI, validação, JSONL e HTML.
- Dia 4: golden/degradação, README, exemplo e PDF da arquitetura.
- Dia 5: clone limpo, CI, secret scan, smoke live, revisão visual e publicação.

Stretch não começa antes de todos os critérios Must estarem verdes.

## 16. Decisões encerradas

- otimizar para entrega completa em cinco dias;
- Brasil apenas;
- snapshots oficiais fixados; notícias ao vivo;
- mortalidade populacional obrigatória e letalidade suplementar;
- proxy de pressão de SRAG em UTI, não ocupação observada total;
- cobertura de influenza da população-alvo;
- períodos compatíveis com cada fonte e cutoff estabilizado;
- LangGraph controlado;
- OpenAI como único provedor do MVP;
- Google News RSS sem credencial adicional;
- relatório HTML e PDF apenas para arquitetura;
- auditoria JSONL com bundle de evidência;
- specs voltam a `DRAFT` até contratos de fonte verificáveis;
- golden run completo; degradação separada;
- UF, COVID-19 e demais extensões fora do MVP.

## 17. Questões abertas

Não há decisão de produto aberta. A seleção dos recursos oficiais e códigos de
campo é uma atividade de verificação com critério de saída definido na seção
3.2; qualquer incompatibilidade encontrada reabre o contrato antes de
implementação, em vez de ser resolvida silenciosamente no código.
