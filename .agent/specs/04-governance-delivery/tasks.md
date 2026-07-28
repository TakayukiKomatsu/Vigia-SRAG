# Tarefas — Governança, transparência e entrega

> Derivado de spec.md versão 1.0

## Preparação

- [ ] **T-GD-1 [FR-GD-1..FR-GD-4]:** Definir schema versionado, criticidade e allowlist de payload para cada evento de auditoria.
- [ ] **T-GD-2 [FR-GD-6, FR-GD-7]:** Definir sumário do README e inventário obrigatório do diagrama/PDF.

## Implementação

- [ ] **T-GD-3 [FR-GD-1, FR-GD-2]:** Implementar run context e store append-only com timestamps, versões e hashes.
- [ ] **T-GD-4 [FR-GD-3, NFR-GD-2]:** Implementar sanitização por allowlist e assertions contra PII/segredos.
- [ ] **T-GD-5 [FR-GD-4]:** Implementar consulta e verificação de integridade por run ID.
- [ ] **T-GD-6 [FR-GD-5, FR-GD-9]:** Implementar CLI/app local, configuração exemplo e caminho de demo com snapshots permitidos.
- [ ] **T-GD-7 [FR-GD-8]:** Configurar ignore de segredos, dados brutos, snapshots completos, logs e outputs; manter fixtures mínimas.
- [ ] **T-GD-8 [FR-GD-6]:** Escrever README com arquitetura, quickstart, dados, métricas, agente, auditoria, guardrails, segurança, testes e limitações.
- [ ] **T-GD-9 [FR-GD-7]:** Criar diagrama-fonte e exportar PDF conceitual legível com todos os componentes exigidos.
- [ ] **T-GD-10 [FR-GD-10]:** Implementar smoke path Brasil e UF e produzir relatório de exemplo sanitizado.

## Verificação

- [ ] **T-GD-11 [AC-GD-1, AC-GD-2, AC-GD-3, AC-GD-10]:** Verificar sequência, sanitização, consulta, hashes e bloqueio quando um evento crítico não puder ser persistido.
- [ ] **T-GD-12 [AC-GD-4]:** Executar quickstart em ambiente limpo sem edição de código.
- [ ] **T-GD-13 [AC-GD-5, AC-GD-6]:** Revisar todas as seções do README e abrir/inspecionar PDF e relatório.
- [ ] **T-GD-14 [AC-GD-7]:** Executar scanner de segredos e inspecionar arquivos preparados para Git.
- [ ] **T-GD-15 [AC-GD-8]:** Rodar smoke tests Brasil e SP e validar requisitos obrigatórios e indisponibilidades justificadas.
- [ ] **T-GD-16 [AC-GD-9]:** Executar formatador em modo check, lint, type-check e suíte de testes definidos pelo projeto.
