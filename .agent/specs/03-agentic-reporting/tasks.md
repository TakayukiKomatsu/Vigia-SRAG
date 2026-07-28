# Tarefas — Agente e relatório fundamentado

> Derivado de spec.md versão 1.0

## Preparação

- [ ] **T-AR-1 [FR-AR-2]:** Definir estado tipado do LangGraph, nós, transições, rotas de degradação e versões.
- [ ] **T-AR-2 [FR-AR-4]:** Selecionar adaptador de busca atual e fontes permitidas; documentar contrato, credenciais e limites.
- [ ] **T-AR-3 [FR-AR-6, FR-AR-7]:** Definir schema do payload/saída LLM e política de fundamentação e linguagem.

## Implementação

- [ ] **T-AR-4 [FR-AR-1]:** Implementar modelo e guardrails da solicitação Brasil/UF, data e janela.
- [ ] **T-AR-5 [FR-AR-3]:** Implementar tools tipadas de métricas e gráficos sobre os serviços do SDD 02.
- [ ] **T-AR-6 [FR-AR-4]:** Implementar tool de notícias com allowlist, normalização, deduplicação, janela e metadados.
- [ ] **T-AR-7 [FR-AR-5]:** Implementar `EvidenceBundle` imutável e validação pré-LLM.
- [ ] **T-AR-8 [FR-AR-2, FR-AR-9]:** Implementar grafo e rotas de sucesso/falha/degradação.
- [ ] **T-AR-9 [FR-AR-6, NFR-AR-6]:** Implementar adaptador de LLM configurável e fake determinístico.
- [ ] **T-AR-10 [FR-AR-7]:** Implementar validação pós-LLM de números, IDs de evidência, citações e linguagem.
- [ ] **T-AR-11 [FR-AR-8]:** Implementar renderer HTML/PDF usando objetos métricos e gráficos como fontes autoritativas.
- [ ] **T-AR-12 [FR-AR-10]:** Aplicar limites de tools, tentativas, janela, tokens e timeout.

## Verificação

- [ ] **T-AR-13 [AC-AR-1, AC-AR-2]:** Verificar rota principal e schemas restritos das tools.
- [ ] **T-AR-14 [AC-AR-3]:** Verificar filtros de notícia, deduplicação, URL/fonte/data e prompt injection.
- [ ] **T-AR-15 [AC-AR-4, AC-AR-5, AC-AR-9]:** Inspecionar payload LLM e rejeitar número/citação inventados.
- [ ] **T-AR-16 [AC-AR-6]:** Gerar relatório completo em fixture e verificar todas as seções obrigatórias.
- [ ] **T-AR-17 [AC-AR-7, AC-AR-8]:** Simular indisponibilidade de notícia/LLM e estouro de limites; verificar degradação e auditoria.
