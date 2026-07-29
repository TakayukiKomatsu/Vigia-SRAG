# Rastreabilidade do desafio para o SDD v2.2

> Status: DRAFT
> Version: 2.2
> Last Updated: 2026-07-29

Este arquivo parafraseia as obrigações usadas na validação local. O documento
restrito original não é reproduzido nem versionado.

`Covered by contract` significa que o SDD possui requisito, aceitação, tarefa
e evidência planejada. Não significa que a aplicação já foi implementada.

| CH | Obrigação resumida | Requirements | Acceptance | Mandatory tasks | Evidência esperada |
|---|---|---|---|---|---|
| `CH-01` | Relatório automatizado com dados, notícias e explicação | `FR-AR-2`, `FR-AR-3`, `FR-AR-4`, `FR-AR-6`, `FR-AR-8` | `AC-AR-1`, `AC-AR-4`, `AC-AR-6`, `AC-AR-8` | `T-AR-2`, `T-AR-3`, `T-AR-4`, `T-AR-5`, `T-AR-6` | `report.html`, `evidence.json`, notícias validadas e claims estruturadas |
| `CH-02` | Consulta do banco pelo agente | `FR-DF-6`, `FR-AR-3` | `AC-DF-5`, `AC-AR-2` | `T-DF-4`, `T-AR-2` | evento da tool e query DuckDB somente leitura |
| `CH-03` | Notícias SRAG consultadas ao vivo | `FR-AR-4` | `AC-AR-3` | `T-AR-3`, `T-AR-8` | itens RSS com publicação/coleta e evento live |
| `CH-04` | Taxa de aumento de casos | `FR-MT-2` | `AC-MT-2` | `T-MT-2`, `T-MT-6` | `MetricResult` com duas semanas e delta |
| `CH-05` | Taxa de mortalidade | `FR-MT-3` | `AC-MT-3` | `T-MT-2`, `T-MT-6` | óbitos por SRAG por 100 mil com fonte IBGE |
| `CH-06` | Taxa de ocupação de UTI | `FR-MT-5` | `AC-MT-5` | `T-MT-3`, `T-MT-6` | proxy rotulado e limitação de não ocupação observada |
| `CH-07` | Taxa de vacinação com escopo elegível | `FR-MT-7`, `FR-AR-9`, `FR-GD-1` | `AC-MT-7`, `AC-AR-10`, `AC-GD-10` | `T-MT-4`, `T-MT-6`, `T-AR-7`, `T-GD-1`, `T-GD-2` | cobertura oficial influenza 2026 com `population_scope` explícito; escopo regional é suplemento não-nacional elegível, enquanto escopo nas outras cinco métricas reprova o golden |
| `CH-08` | Gráfico diário de 30 dias | `FR-MT-8`, `FR-MT-10` | `AC-MT-8` | `T-MT-5`, `T-MT-6` | série de 30 pontos e gráfico/hash |
| `CH-09` | Gráfico mensal de 12 meses | `FR-MT-9`, `FR-MT-10` | `AC-MT-9` | `T-MT-5`, `T-MT-6` | série de 12 meses completos e gráfico/hash |
| `CH-10` | Tratamento de dados reais problemáticos | `FR-DF-1`, `FR-DF-2`, `FR-DF-3`, `FR-DF-4`, `FR-DF-7` | `AC-DF-1`, `AC-DF-2`, `AC-DF-3`, `AC-DF-6`, `AC-DF-7`, `AC-DF-8` | `T-DF-1`, `T-DF-2`, `T-DF-3`, `T-DF-5`, `T-DF-6`, `T-DF-7` | contratos, fixture, qualidade, quarentena e benchmark |
| `CH-11` | Arquitetura justificável | `FR-DF-6`, `FR-MT-1`, `FR-MT-10`, `FR-AR-2`, `FR-AR-3`, `FR-AR-10` | `AC-DF-5`, `AC-MT-1`, `AC-MT-10`, `AC-AR-1`, `AC-AR-2`, `AC-AR-10`, `AC-AR-11` | `T-DF-4`, `T-MT-1`, `T-AR-1`, `T-AR-2`, `T-AR-4`, `T-AR-6` | módulos, contratos tipados, tools, grafo, DuckDB e limites/auditoria |
| `CH-12` | Governança, transparência e decisões | `FR-DF-1`, `FR-DF-6`, `FR-DF-8`, `FR-AR-10`, `FR-GD-1` | `AC-DF-1`, `AC-DF-5`, `AC-DF-7`, `AC-AR-10`, `AC-AR-11`, `AC-GD-1` | `T-DF-1`, `T-DF-5`, `T-DF-7`, `T-AR-1`, `T-AR-6`, `T-GD-1` | `audit.jsonl`, manifests, eventos, hashes, run ID e limites críticos |
| `CH-13` | Guardrails | `FR-DF-7`, `FR-DF-8`, `FR-AR-1`, `FR-AR-4`, `FR-AR-5`, `FR-AR-7`, `FR-AR-9`, `FR-AR-10`, `FR-GD-1` | `AC-DF-6`, `AC-DF-7`, `AC-AR-4`, `AC-AR-5`, `AC-AR-7`, `AC-AR-9`, `AC-AR-10`, `AC-AR-11`, `AC-GD-10` | `T-DF-5`, `T-DF-6`, `T-AR-1`, `T-AR-4`, `T-AR-5`, `T-AR-7`, `T-GD-2` | eventos de bloqueio, testes adversariais, exceção scoped exclusiva para PNI influenza, rejeição scoped nas demais métricas e limites críticos |
| `CH-14` | Uso de tools | `FR-AR-3`, `FR-AR-4` | `AC-AR-2`, `AC-AR-3` | `T-AR-2`, `T-AR-3` | schemas e tool-call events |
| `CH-15` | Dados sensíveis minimizados | `FR-DF-5`, `NFR-DF-3`, `NFR-AR-5`, `NFR-GD-2`, `FR-AR-9` | `AC-DF-4`, `AC-AR-5`, `AC-AR-10`, `AC-GD-7`, `AC-GD-10` | `T-DF-4`, `T-AR-4`, `T-AR-7`, `T-GD-2`, `T-GD-5` | varredura de campos, artefatos sanitizados e observações scoped com limitação explícita |
| `CH-16` | Clean Code | `NFR-DF-1`, `NFR-MT-1`, `NFR-MT-3`, `NFR-AR-3`, `FR-GD-6` | `AC-DF-5`, `AC-MT-11`, `AC-AR-12`, `AC-GD-7` | `T-DF-6`, `T-MT-6`, `T-AR-7`, `T-GD-5` | pytest, Ruff, mypy e módulos tipados |
| `CH-17` | Repositório público e documentação | `FR-GD-3`, `FR-GD-4`, `FR-GD-6`, `FR-GD-7` | `AC-GD-3`, `AC-GD-4`, `AC-GD-5`, `AC-GD-7`, `AC-GD-8` | `T-GD-3`, `T-GD-5`, `T-GD-6` | README, sample, CI e URL pública |
| `CH-18` | PDF conceitual da arquitetura | `FR-GD-5` | `AC-GD-6` | `T-GD-4` | fonte e PDF visualmente verificado |
| `CH-19` | Entrega em cinco dias | `FR-GD-8` | `AC-GD-9` | `T-DF-7`, `T-MT-7`, `T-AR-8`, `T-GD-6` | 28 tarefas D1–D5 e checklist de release |

## Hardening v2.2

| Evidence | Requirements | Acceptance | Task | Executable proof | Status |
|---|---|---|---|---|---|
| Contrato local de comentário, modelos, retries, fallback e auditoria | `FR-AR-4`, `FR-AR-6`, `FR-AR-9`, `FR-AR-10` | `AC-AR-13` | `T-AR-5`, `T-AR-7` | `tests/test_commentary.py`, `tests/test_graph.py` | Implementação local; evidência pública aberta |
| Redirect, DNS e limites RSS | `FR-AR-4` | `AC-AR-14` | `T-AR-3`, `T-AR-7` | `tests/test_news.py` | Implementação local |
| Escopo de influenza e schema nacional | `FR-MT-7`, `FR-MT-10` | `AC-MT-12` | `T-MT-6` | `tests/test_governance.py` | Implementação local |
| SIVEP oficial sem suporte CNES/PNI | `FR-GD-1` | `AC-GD-11` | `T-GD-1` | `tests/test_prepare_official_snapshot.py` | Aberto até execução oficial |
| Metadados, conteúdo, histórico e release público | `FR-GD-6`, `FR-GD-7` | `AC-GD-12` | `T-GD-6` | `tests/test_release_checks.py`, `scripts/check_external_release.py` | Público/clone continuam bloqueados |

## Review Result

- Cobertura documental v2.2: `COVERED BY CONTRACT`.
- Implementação: `IMPLEMENTED LOCALLY`; suíte, smoke OpenRouter/RSS e gate estrito sobre fixture permitida possuem evidência reproduzida.
- Finalização: `BLOCKED` pelos contratos oficiais ainda `UNVERIFIED`, bundle de referência baseado integralmente em dados oficiais, URL pública e clone não autenticado.
