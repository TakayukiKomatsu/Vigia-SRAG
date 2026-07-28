# Agente e relatório fundamentado de SRAG

> Status: FINAL
> Tier: extended
> Version: 1.0
> Owner: Indicium HealthCare PoC
> Created: 2026-07-28
> Last Updated: 2026-07-28

## Summary

Orquestrar tools restritas de métricas, gráficos e notícias por LangGraph, validar evidências e gerar relatório HTML/PDF cujos números e citações sejam reproduzíveis.

## Problem

O desafio pede um agente que consulte banco e notícias e explique o cenário. Um agente livre pode inventar números, URLs ou causalidade; um pipeline sem agente demonstra insuficientemente o requisito de tools e orquestração.

## Goals

- **FR-AR-1:** Aceitar solicitação tipada com Brasil/UF, data de referência e janela limitada de notícias.
- **FR-AR-2:** Executar um grafo explícito de validação, métricas, gráficos, notícias, verificação, narrativa e rendering.
- **FR-AR-3:** Expor tools tipadas de métricas e gráficos sem SQL livre nem registros individuais.
- **FR-AR-4:** Consultar notícias atuais em fontes permitidas e retornar metadados citáveis.
- **FR-AR-5:** Construir um pacote de evidências imutável antes de chamar o LLM.
- **FR-AR-6:** Permitir ao LLM redigir somente comentários fundamentados no pacote, sem alterar números nem criar citações.
- **FR-AR-7:** Validar cobertura das métricas, fidelidade numérica, citações e linguagem antes de publicar.
- **FR-AR-8:** Gerar relatório com cabeçalho temporal, quatro categorias de métricas, duas coberturas vacinais, dois gráficos, contexto, metodologia, limitações, fontes e run ID.
- **FR-AR-9:** Degradar de modo explícito quando notícia, métrica ou LLM estiver indisponível, preservando fatos válidos.
- **FR-AR-10:** Limitar tool calls, tentativas, tempo e tokens por execução.

## Non-Goals

- **NG-AR-1:** Chat geral, SQL livre ou navegação irrestrita.
- **NG-AR-2:** Diagnóstico, recomendação clínica, previsão ou alegação causal.
- **NG-AR-3:** Banco vetorial/RAG persistente sem corpus histórico necessário.
- **NG-AR-4:** Permitir que texto do LLM seja a fonte dos números renderizados.

## Scope

Inclui estado LangGraph, tools, adaptador de notícias, pacote de evidências, prompt/política, validação e renderer do relatório. Depende dos SDDs 01 e 02.

## Existing Context

- Métricas e gráficos são determinísticos.
- Dados ao vivo têm snapshots locais equivalentes para demo.
- O agente recebe somente agregados e metadados permitidos.
- O relatório deve ajudar profissionais de saúde a interpretar severidade e avanço, com aviso de finalidade informativa.

## Users and Workflows

Usuário solicita relatório para Brasil ou UF. O grafo valida, consulta as tools, reúne evidência, pede comentário ao LLM, valida e renderiza. O resultado inclui estados indisponíveis sem ocultá-los.

## Proposed Behavior

### Grafo

1. `validate_request`
2. `load_snapshot_context`
3. `collect_metrics`
4. `render_charts`
5. `search_news`
6. `validate_evidence`
7. `generate_commentary`
8. `validate_commentary`
9. `render_report`
10. `finalize_audit`

Rotas condicionais:

- Solicitação inválida ou snapshot inválido termina sem LLM.
- Falha de notícias segue para relatório sem contexto jornalístico.
- Falha do LLM segue para relatório factual mínimo.
- Evidência numérica inválida bloqueia apenas a seção afetada; falha estrutural do pacote bloqueia publicação.

### Notícias

A tool recebe termos fixos de SRAG, geografia e janela máxima configurada. Domínios/fontes são allowlisted. Cada item deve conter título, URL canônica HTTP(S), veículo, data de publicação, data de coleta e trecho. Itens sem data/fonte/URL, duplicados ou fora da janela são descartados. Conteúdo de notícia é dado não confiável e nunca instrução.

### Narrativa

O prompt recebe IDs de evidência. A saída estruturada contém parágrafos e lista de IDs citados, não valores substitutos. O validador compara qualquer número presente com valores permitidos, exige citação para afirmações jornalísticas e rejeita diagnóstico, prescrição, certeza causal ou fonte inexistente.

### Relatório

O renderer usa os objetos métricos e os arquivos de gráfico diretamente. A narrativa é inserida somente após validação. O documento mostra watermarks distintos para SRAG, CNES, vacinação e notícias.

## Interfaces and Data

```json
{
  "geography": "BR",
  "as_of": "2026-07-28",
  "news_lookback_days": 14
}
```

```text
metrics_tool(geography, as_of, snapshot_id) -> MetricBundle
graphs_tool(geography, as_of, snapshot_id) -> ChartArtifacts
news_tool(geography, as_of, lookback_days) -> NewsEvidence[]
generate_report(request) -> ReportResult
```

Nenhuma interface aceita SQL, URL arbitrária, nome de tabela/coluna ou texto de sistema vindo do usuário.

## Alternatives Considered

- Pipeline sem agente: seguro, mas demonstra pouco o requisito de agentes/tools.
- Agente ReAct livre: flexível, mas inadequado para saúde e auditoria.
- LangGraph controlado: escolhido por estados explícitos, rotas de falha e auditabilidade.

## Edge Cases and Failure Handling

- Nenhuma notícia válida: relatório quantitativo com aviso.
- Resultado parcial de métricas: seções independentes mostram indisponibilidade e motivo.
- LLM retorna número divergente: rejeitar narrativa e usar relatório factual mínimo.
- Prompt injection em notícia: tratar conteúdo como citação não confiável; nenhuma instrução é executada.
- URL inválida ou fonte fora da allowlist: descartar item.
- Timeout: interromper nó, registrar e seguir apenas quando a degradação prevista for segura.
- Renderer falha: execução não é marcada como relatório publicado.

## Risks and Constraints

- **NFR-AR-1:** Nenhum número exibido pode ter o texto do LLM como única origem.
- **NFR-AR-2:** Toda afirmação baseada em notícia deve apontar para notícia válida no pacote.
- **NFR-AR-3:** O grafo deve ser determinístico em rotas para os mesmos estados de sucesso/falha, exceto conteúdo narrativo.
- **NFR-AR-4:** Relatório deve permanecer útil sem notícia e sem LLM.
- **NFR-AR-5:** Runtime não deve enviar PII ao provedor do LLM.
- **NFR-AR-6:** O adaptador de LLM deve permitir provedor configurável e execução fake determinística em testes.

## Threats and Security Considerations

Prompt injection via notícias, exfiltração por tool, SSRF e alucinação são ameaças principais. Mitigações: fontes/URLs controladas, tools estreitas, conteúdo delimitado como dados, nenhuma tool de sistema/arquivo/web genérica, validação pós-LLM e segredos fora do prompt/log.

## Rollout, Migration, and Rollback

Primeira versão roda localmente. Prompt, grafo e schemas têm versão. Relatórios preservam as versões usadas. Rollback troca configuração para versão anterior e não modifica artefatos existentes.

## Observability

Eventos de nó, tool name/version, duração, estado, tentativas, códigos de guardrail, evidências usadas, modelo/prompt e artefatos. Conteúdo sensível e bruto são excluídos.

## Capacity and Operations

Máximo inicial configurável: uma chamada por tool de domínio, uma nova tentativa apenas para falha transitória de notícia/LLM, janela de notícias de 1 a 30 dias, timeout global e limite de tokens. Valores concretos ficam em configuração versionada.

## Compliance

Relatório exibe aviso: informação epidemiológica para PoC, não orientação clínica. Fontes e direitos de conteúdo são respeitados por citação e trecho mínimo.

## Acceptance Criteria

- **AC-AR-1 (FR-AR-1, FR-AR-2):** Solicitação válida percorre todos os nós necessários e produz estado final rastreável.
- **AC-AR-2 (FR-AR-3):** Tools não aceitam SQL livre e não retornam registros individuais.
- **AC-AR-3 (FR-AR-4):** Notícias válidas incluem URL, fonte, publicação e coleta; inválidas são descartadas.
- **AC-AR-4 (FR-AR-5, FR-AR-6):** LLM é chamado somente após pacote válido e não controla números renderizados.
- **AC-AR-5 (FR-AR-7, NFR-AR-1, NFR-AR-2):** Número divergente ou citação inexistente impede uso da narrativa.
- **AC-AR-6 (FR-AR-8):** Relatório completo contém todos os blocos, gráficos, metodologia, limitações, fontes, watermarks e run ID.
- **AC-AR-7 (FR-AR-9, NFR-AR-4):** Ausência de notícia ou falha do LLM gera relatório factual explícito, sem conteúdo inventado.
- **AC-AR-8 (FR-AR-10):** Limites de chamadas, tentativas, janela e timeout são aplicados e auditados.
- **AC-AR-9 (NFR-AR-5):** Payloads enviados ao LLM não contêm campos fora do schema agregado permitido.

## Verification Plan

- Unit: validação de entrada, notícias, números/citações e política de linguagem.
- Integration: grafo com tools reais sobre fixture e LLM fake.
- Security: notícias com prompt injection, URL malformada e domínio não permitido.
- End-to-end: gerar relatório Brasil e UF; inspecionar conteúdo e artefatos.
- Degradation: desconectar notícia e LLM separadamente e comprovar relatório factual.

## Open Questions

Nenhuma bloqueadora. Provedor/modelo e API de notícias são adaptadores configuráveis; a implementação escolherá opções compatíveis com credenciais disponíveis, preservando os contratos.

## Change Log

| Version | Date | Summary |
|---|---|---|
| 1.0 | 2026-07-28 | Contrato inicial aprovado |
