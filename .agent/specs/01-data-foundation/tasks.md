# Tarefas — Fundação de dados SRAG

> Derivado de spec.md versão 1.0

## Preparação

- [ ] **T-DF-1 [FR-DF-1, FR-DF-8]:** Validar distribuições oficiais atuais, dicionários e termos de uso do SIVEP-Gripe, CNES, influenza e COVID-19; registrar URLs e contratos em configuração versionada.
- [ ] **T-DF-2 [FR-DF-2, FR-DF-4]:** Definir schema canônico v1 e allowlist de campos com matriz de códigos, datas e nulabilidade.

## Implementação

- [ ] **T-DF-3 [FR-DF-1]:** Implementar interface de fonte e adaptadores live/local com download temporário, limites, hash e metadados.
- [ ] **T-DF-4 [FR-DF-2, FR-DF-7]:** Implementar normalização, validação, códigos de rejeição e quarentena.
- [ ] **T-DF-5 [FR-DF-3]:** Implementar deduplicação SIVEP-Gripe e contadores de precedência.
- [ ] **T-DF-6 [FR-DF-4, NFR-DF-3]:** Projetar dados para tabelas minimizadas e comprovar ausência de campos proibidos.
- [ ] **T-DF-7 [FR-DF-5]:** Materializar Parquet e construir DuckDB analítico em diretório imutável.
- [ ] **T-DF-8 [FR-DF-6]:** Gerar manifesto por último, com hashes, schemas, watermarks, qualidade e versões.
- [ ] **T-DF-9 [FR-DF-8, NFR-DF-4]:** Implementar publicação atômica e seleção/rollback para o último snapshot válido.

## Verificação

- [ ] **T-DF-10 [AC-DF-1, AC-DF-2, AC-DF-3]:** Criar fixtures mínimas e verificar equivalência live/local, normalização, quarentena e deduplicação.
- [ ] **T-DF-11 [AC-DF-4, AC-DF-5, AC-DF-7, AC-DF-8]:** Verificar allowlist, hashes determinísticos, tabelas, watermarks e métricas de qualidade do snapshot publicado.
- [ ] **T-DF-12 [AC-DF-6]:** Simular fonte truncada e schema incompatível; confirmar ausência de publicação parcial e preservação do snapshot anterior.
