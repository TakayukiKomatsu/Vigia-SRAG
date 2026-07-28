# Governança, transparência e entrega da PoC SRAG

> Status: FINAL
> Tier: extended
> Version: 1.0
> Owner: Indicium HealthCare PoC
> Created: 2026-07-28
> Last Updated: 2026-07-28

## Summary

Tornar cada execução auditável, a aplicação reproduzível e o repositório avaliável por meio de logs estruturados, guardrails verificáveis, documentação, demonstração local e diagrama conceitual em PDF.

## Problem

Uma PoC pode produzir um relatório plausível sem permitir verificar origem, decisões ou falhas. O desafio avalia explicitamente governança, transparência, guardrails, dados sensíveis, clean code, README e PDF de arquitetura.

## Goals

- **FR-GD-1:** Atribuir run ID único e registrar eventos estruturados de cada nó/tool/guardrail.
- **FR-GD-2:** Vincular relatório a parâmetros, snapshots, versões de fórmula, grafo, prompt, modelo e notícias.
- **FR-GD-3:** Registrar decisões e falhas sem persistir PII, segredos ou registros individuais.
- **FR-GD-4:** Permitir consultar uma trilha de auditoria por run ID e reconstruir as entradas autorizadas.
- **FR-GD-5:** Disponibilizar execução local documentada para atualização de dados e geração de relatório Brasil/UF.
- **FR-GD-6:** Documentar arquitetura, fontes, fórmulas, qualidade, guardrails, privacidade, limitações, testes e decisões no README/relatórios.
- **FR-GD-7:** Incluir PDF legível do diagrama conceitual com orquestrador, tools, LLM, banco, fontes de dados/notícias e fluxos.
- **FR-GD-8:** Manter configuração exemplo sem segredo e ignorar artefatos sensíveis/volumosos do Git.
- **FR-GD-9:** Fornecer demo reproduzível com snapshots pequenos ou instruções de obtenção, sem publicar dados proibidos.
- **FR-GD-10:** Validar fim a fim que relatórios Brasil e UF atendem às exigências do desafio.

## Non-Goals

- **NG-GD-1:** Observabilidade de produção, SIEM ou autenticação multiusuário.
- **NG-GD-2:** Publicar chaves de API ou o CSV bruto quando termos/tamanho não permitirem.
- **NG-GD-3:** Alegar conformidade clínica, regulatória ou disponibilidade em tempo real estrita.
- **NG-GD-4:** Ocultar limitações para melhorar aparência da demo.

## Scope

Inclui store de auditoria, política de logging, CLI/app local, README, arquivo de configuração exemplo, diagrama-fonte e PDF, checklist de segurança e smoke tests de entrega.

## Existing Context

Depende dos SDDs 01–03. O repositório começou sem estrutura e deve ser público ao final. O desafio prevê cinco dias e aceita PoC, mas todos os itens obrigatórios precisam de evidência ou limitação explícita.

## Users and Workflows

- Desenvolvedor instala dependências, configura fontes/LLM e executa ingestão.
- Avaliador pode usar snapshot demonstrativo, gerar relatório e consultar auditoria por run ID.
- Usuário escolhe Brasil/UF e recebe artefato com fontes e limitações.

## Proposed Behavior

### Auditoria

Eventos append-only em JSONL ou banco local com schema versionado:

- `run_started`, `request_validated`, `snapshot_selected`;
- `node_started/completed/failed`;
- `tool_called/completed/failed` com entradas/saídas resumidas;
- `guardrail_passed/blocked`;
- `evidence_validated`, `narrative_validated`;
- `report_published` ou `run_failed`.

Cada evento contém run ID, timestamp UTC, tipo, componente/versão, duração quando aplicável e payload sanitizado. Hashes podem provar vínculo com artefatos sem copiar conteúdo.

### Repositório e execução

README apresenta quickstart, arquitetura, data flow, configuração, comandos, relatório de exemplo, metodologias, fontes e limitações. `.env.example` lista variáveis sem valores secretos. `.gitignore` cobre `.env`, bruto, snapshots completos, logs e saídas locais, mantendo fixtures permitidas.

### PDF de arquitetura

O diagrama-fonte versionado gera PDF determinístico e legível. O PDF mostra o Agente Principal, tools de métricas/gráficos/notícias, LLM, DuckDB, ingestão, fontes SIVEP-Gripe/CNES/vacinação/notícias, renderer e auditoria, com setas de fluxo e limite de dados sensíveis.

## Interfaces and Data

```text
audit(event_type, run_id, component, sanitized_payload) -> AuditEventId
show_audit(run_id) -> AuditTrail
generate_report --uf SP --as-of YYYY-MM-DD
ingest --mode live|snapshot
```

O schema de auditoria mantém allowlist por evento; serialização arbitrária de objetos é proibida.

## Alternatives Considered

- Logs de texto: fáceis, mas difíceis de consultar e validar.
- Tracing SaaS: útil, porém cria dependência e possível exposição de saúde; não necessário para a PoC.
- Store local estruturado: escolhido por portabilidade e controle.

## Edge Cases and Failure Handling

- Falha ao gravar evento crítico antes do LLM: interromper para não produzir relatório sem auditoria.
- Falha ao gravar evento não crítico após artefato: marcar execução como incompleta e não alegar publicação auditável.
- Artefato ausente/hash divergente: `show_audit` sinaliza integridade inválida.
- Segredo detectado em configuração versionada: verificação falha.
- PDF ilegível/sem componente exigido: entrega falha.
- Fonte ao vivo indisponível: quickstart oferece snapshot demonstrativo com watermark explícito.

## Risks and Constraints

- **NFR-GD-1:** Eventos críticos devem ser persistidos antes da transição seguinte.
- **NFR-GD-2:** Auditoria não pode conter campos fora das allowlists nem payload bruto de notícia/dado clínico.
- **NFR-GD-3:** Uma pessoa com Python e as credenciais documentadas deve reproduzir a demo seguindo o README.
- **NFR-GD-4:** PDF deve abrir sem erro e permanecer legível em página A4 ou Letter.
- **NFR-GD-5:** Código deve separar domínio, infraestrutura e apresentação, usar tipagem e manter interfaces estreitas.

## Threats and Security Considerations

Principais riscos: segredos no Git, PII no log, artefatos brutos publicados, relatório manipulado e dependência comprometida. Usar allowlists, arquivos ignorados, scanning de segredos, hashes, lockfile e dependências mínimas.

## Rollout, Migration, and Rollback

Entrega local versionada. Mudança do schema de auditoria incrementa versão; leitor suporta apenas versões declaradas e falha explicitamente. Artefatos antigos são imutáveis.

## Observability

A própria auditoria é o mecanismo principal. Resumo por execução inclui duração, status, nós/tools, guardrails, evidências, artefatos e erros.

## Capacity and Operations

Rotação simples por arquivo/run ID; logs e relatórios locais não entram no Git. Fixtures e um relatório de exemplo sanitizado podem entrar no repositório.

## Compliance

README deve explicar minimização, finalidade, limitações, ausência de orientação médica e proveniência das fontes. Conteúdo do enunciado não deve ser reproduzido integralmente no repositório sem autorização.

## Acceptance Criteria

- **AC-GD-1 (FR-GD-1, FR-GD-2):** Execução bem-sucedida possui sequência completa de eventos vinculada a parâmetros, versões, snapshots e artefatos.
- **AC-GD-2 (FR-GD-3, NFR-GD-2):** Auditoria e payloads não contêm PII, segredos nem linhas brutas.
- **AC-GD-3 (FR-GD-4):** Consulta por run ID retorna ordem, decisões, evidências e integridade dos artefatos.
- **AC-GD-4 (FR-GD-5, FR-GD-9, NFR-GD-3):** Quickstart executado em ambiente limpo gera relatório demonstrativo.
- **AC-GD-5 (FR-GD-6):** README contém todas as seções exigidas e definições/limitações das métricas.
- **AC-GD-6 (FR-GD-7, NFR-GD-4):** PDF abre e contém todos os componentes e interações exigidos.
- **AC-GD-7 (FR-GD-8):** Repositório não rastreia segredos, dados brutos proibidos, snapshots completos ou logs locais.
- **AC-GD-8 (FR-GD-10):** Smoke tests Brasil e UF produzem quatro categorias de métricas, duas coberturas, dois gráficos, fontes e auditoria, admitindo indisponibilidade apenas com motivo verificável.
- **AC-GD-9 (NFR-GD-5):** Verificações de estilo, tipagem e testes do projeto passam.
- **AC-GD-10 (FR-GD-1, NFR-GD-1):** Falha ao persistir evento crítico interrompe a execução antes do LLM ou da publicação.

## Verification Plan

- Unit: sanitização e schema de eventos.
- Integration: trilha completa e consulta por run ID.
- Security: scanner de segredos e assertions negativas nos logs/payloads.
- Documentation: executar comandos do README em ambiente limpo.
- Visual: abrir PDF e relatório; confirmar legibilidade e componentes.
- End-to-end: relatório Brasil e SP com auditoria íntegra.

## Open Questions

Nenhuma bloqueadora. Hospedagem GitHub pública é ação externa final; o repositório local deve ficar pronto para publicação sem exigir mudança de código.

## Change Log

| Version | Date | Summary |
|---|---|---|
| 1.0 | 2026-07-28 | Contrato inicial aprovado |
