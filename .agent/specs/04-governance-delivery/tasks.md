# Tarefas — Governança e entrega v2

> Must: 6 tarefas. Dias 4 e 5. Stretch fica em `../stretch-backlog.md`.
> Ledger 2026-07-28: evidência concluída para T-GD-2 e T-GD-4; T-GD-3 está parcial. T-GD-1, T-GD-5 e T-GD-6 permanecem abertas por PNI/OpenAI/golden/publicação, portanto nenhuma dependência foi promovida indevidamente.


- [ ] **T-GD-1 [P0, D4, CH-01, CH-03, CH-04, CH-05, CH-06, CH-07, CH-08, CH-09, CH-12, FR-GD-1, NFR-GD-1, NFR-GD-2, AC-GD-1, AC-GD-10, depends: T-AR-8]:** Construir e validar o golden estrito com valores reais nacionalmente elegíveis (não-scoped), notícia live, claims válidas e bundle sanitizado completo. Rejeitar observações com escopo geográfico. **Evidence:** relatório/bundle de referência e assertions verdes com exclusão de scoped.
- [ ] **T-GD-2 [P0, D4, CH-13, CH-15, FR-GD-2, NFR-GD-1, NFR-GD-2, AC-GD-2, AC-GD-10, depends: T-GD-1]:** Executar suítes separadas de degradação, injeção, privacidade, segurança, falha crítica e observações scoped/limitadas. **Evidence:** resultados esperados sem elegibilidade golden, incluindo rejeição de scoped.
- [ ] **T-GD-3 [P0, D4, CH-17, FR-GD-3, FR-GD-4, NFR-GD-3, AC-GD-3, AC-GD-4, AC-GD-5, depends: T-GD-1]:** Finalizar quickstarts determinístico/live, README completo e HTML sanitizado rotulado. **Evidence:** comandos reproduzidos e checklist documental verde.
- [ ] **T-GD-4 [P0, D4, CH-18, FR-GD-5, NFR-GD-4, AC-GD-6, depends: T-GD-3]:** Criar fonte do diagrama, compilar PDF e verificar visualmente componentes/limites. **Evidence:** fonte, PDF e checklist visual.
- [ ] **T-GD-5 [P0, D5, CH-15, CH-16, CH-17, CH-19, FR-GD-6, FR-GD-8, NFR-GD-2, NFR-GD-5, AC-GD-7, AC-GD-9, depends: T-GD-2, T-GD-3, T-GD-4]:** Passar CI, qualidade, Gitleaks, staged/history review, ignore policy e validação das 28 tarefas. **Evidence:** checks verdes e relatório de higiene.
- [ ] **T-GD-6 [P0, D5, CH-03, CH-17, CH-19, FR-GD-7, FR-GD-8, AC-GD-4, AC-GD-8, AC-GD-9, depends: T-GD-5]:** Executar smoke live, revisão visual, publicação e clone limpo não autenticado. **Evidence:** URL pública e checklist de release reproduzido.
