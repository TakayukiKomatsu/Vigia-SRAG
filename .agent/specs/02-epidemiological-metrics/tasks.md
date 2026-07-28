# Tarefas — Métricas e gráficos epidemiológicos

> Derivado de spec.md versão 1.0

## Preparação

- [ ] **T-MT-1 [FR-MT-2..FR-MT-5]:** Formalizar matriz de fórmulas, campos canônicos, períodos, estados e versões.
- [ ] **T-MT-2 [FR-MT-4]:** Validar categorias CNES compatíveis e regra paciente-dia/leito-dia com fixtures de fronteira.
- [ ] **T-MT-3 [FR-MT-5]:** Validar definições oficiais de público-alvo/esquema para influenza e COVID-19 e registrá-las em configuração versionada.

## Implementação

- [ ] **T-MT-4 [FR-MT-1, NFR-MT-3]:** Implementar tipos de geografia/data e repositório analítico DuckDB somente leitura.
- [ ] **T-MT-5 [FR-MT-2]:** Implementar taxa de aumento e estados de denominador zero.
- [ ] **T-MT-6 [FR-MT-3]:** Implementar letalidade e contabilização de evoluções desconhecidas.
- [ ] **T-MT-7 [FR-MT-4, FR-MT-10]:** Implementar paciente-dias, leito-dias, ocupação estimada e indicador auxiliar de uso de UTI.
- [ ] **T-MT-8 [FR-MT-5]:** Implementar seleção e cálculo independente das duas coberturas vacinais.
- [ ] **T-MT-9 [FR-MT-6, FR-MT-7]:** Implementar calendário completo das séries diária e mensal com cobertura temporal explícita.
- [ ] **T-MT-10 [FR-MT-8]:** Implementar modelos estruturados de métricas, qualidade, proveniência e indisponibilidade.
- [ ] **T-MT-11 [FR-MT-9, NFR-MT-5]:** Implementar renderer dos dois gráficos e descrições textuais.

## Verificação

- [ ] **T-MT-12 [AC-MT-1, AC-MT-2, AC-MT-3]:** Verificar geografias, fronteiras da taxa de aumento e denominador da letalidade.
- [ ] **T-MT-13 [AC-MT-4, AC-MT-5]:** Verificar ocupação, fallback corretamente rotulado e independência das coberturas.
- [ ] **T-MT-14 [AC-MT-6, AC-MT-7, AC-MT-9]:** Verificar cardinalidade/calendário das séries, cobertura temporal insuficiente e contrato de proveniência/qualidade.
- [ ] **T-MT-15 [AC-MT-8]:** Comparar artefatos gráficos com séries conhecidas e inspecionar título, fonte e descrição.
- [ ] **T-MT-16 [NFR-MT-4]:** Medir o pacote em fixture e no snapshot completo disponível; registrar resultado real no README.
