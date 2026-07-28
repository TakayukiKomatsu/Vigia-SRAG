# Fundação de dados SRAG

> Status: FINAL
> Tier: extended
> Version: 1.0
> Owner: Indicium HealthCare PoC
> Created: 2026-07-28
> Last Updated: 2026-07-28

## Summary

Ingerir dados públicos do SIVEP-Gripe/Open DATASUS, capacidade de UTI do CNES e coberturas oficiais de influenza e COVID-19; validar, minimizar e materializar snapshots reproduzíveis em Parquet e DuckDB.

## Problem

As fontes são heterogêneas, extensas, sujeitas a atraso, duplicidade, códigos ignorados e campos ausentes. O agente não pode operar diretamente sobre arquivos brutos nem receber registros individualizados.

## Goals

- **FR-DF-1:** Ingerir fontes por download ao vivo ou por arquivo local usando o mesmo contrato.
- **FR-DF-2:** Validar schema e normalizar códigos, datas, geografia e tipos sem transformar desconhecido em negativo.
- **FR-DF-3:** Deduplicar registros SIVEP-Gripe por regra documentada e contabilizar descartes.
- **FR-DF-4:** Minimizar dados antes da camada analítica, preservando apenas campos necessários às métricas e uma chave técnica não exposta ao agente.
- **FR-DF-5:** Produzir snapshots Parquet imutáveis e um DuckDB somente analítico.
- **FR-DF-6:** Gerar manifesto com origem, timestamps, hashes, schema, contagens, rejeições, completude e data máxima válida.
- **FR-DF-7:** Quarentenar entradas estruturalmente inválidas sem impedir o processamento de registros válidos.
- **FR-DF-8:** Impedir a publicação de snapshot quando faltarem colunas críticas ou o arquivo não puder ser verificado.

## Non-Goals

- **NG-DF-1:** Corrigir manualmente registros clínicos.
- **NG-DF-2:** Persistir nomes, documentos, endereços ou atributos sem uso analítico.
- **NG-DF-3:** Oferecer acesso do LLM ao dado bruto ou linha a linha.
- **NG-DF-4:** Executar carga incremental complexa; a PoC usa snapshots substituíveis e imutáveis.

## Scope

Inclui adaptadores de fonte, schema canônico, regras de qualidade, quarentena, snapshots, manifesto e construção do DuckDB. Não inclui fórmulas epidemiológicas nem geração do relatório.

## Existing Context

- Repositório greenfield; o enunciado é o único artefato inicial.
- Fontes-alvo: SIVEP-Gripe/Open DATASUS, CNES e dados oficiais de vacinação para influenza e COVID-19.
- O identificador exato de cada arquivo/API é configuração versionada no manifesto, não constante espalhada no código.
- Dados reais podem conter cerca de 100 colunas e 165 mil ou mais registros.

## Users and Workflows

O operador executa `ingest` em modo `live` ou `snapshot`. A aplicação valida cada fonte, publica um conjunto consistente quando os contratos mínimos são satisfeitos e informa qualidade e watermark temporal.

## Proposed Behavior

1. Receber configuração de fontes e diretório de saída.
2. Baixar para área temporária ou abrir arquivo local.
3. Calcular hash do bruto e capturar metadados de origem.
4. Validar encoding, delimitador, colunas críticas e tipos conversíveis.
5. Projetar para schema canônico, normalizar e aplicar regras temporais/geográficas.
6. Deduplicar e separar rejeições com código de motivo.
7. Remover campos não permitidos.
8. Materializar Parquet e DuckDB em diretório identificado pelo snapshot ID.
9. Escrever manifesto por último; sua presença marca publicação atômica bem-sucedida.

## Interfaces and Data

### Comando lógico

```text
ingest(mode, source_config, output_dir) -> SnapshotManifest
```

### Manifesto mínimo

```json
{
  "snapshot_id": "sha256:...",
  "created_at": "ISO-8601",
  "sources": [{"name": "sivep", "uri": "...", "sha256": "...", "retrieved_at": "..."}],
  "watermarks": {"srag": "YYYY-MM-DD", "cnes": "YYYY-MM", "influenza": "...", "covid19": "..."},
  "tables": [{"name": "srag_cases", "rows": 1, "schema_version": "1"}],
  "quality": {"accepted": 1, "rejected": 0, "duplicates": 0, "field_completeness": {}},
  "status": "published"
}
```

### Campos canônicos mínimos

- SRAG: chave técnica, data de sintomas, data de internação, entrada/saída de UTI, evolução, data de evolução e UF.
- CNES: competência, UF, categoria de leito UTI, quantidade disponível aplicável.
- Vacinação: vacina, esquema/dose, período, UF, numerador, denominador, população-alvo, data de atualização e fonte.

## Alternatives Considered

- **Pandas + CSV em runtime:** simples, mas repete limpeza e expõe detalhe demais ao agente.
- **PostgreSQL:** robusto, porém adiciona infraestrutura desnecessária à PoC.
- **Parquet + DuckDB:** escolhido pela execução local, consultas analíticas e snapshots portáveis.

## Edge Cases and Failure Handling

- Coluna crítica ausente: falhar sem publicar snapshot.
- Coluna opcional ausente: publicar com completude zero e limitação registrada.
- Data inválida/invertida: anular o campo ou rejeitar conforme matriz versionada; sempre contabilizar.
- UF inválida: quarentena.
- Código ignorado: mapear para desconhecido, não para “não”.
- Duplicata: manter registro conforme precedência de atualização definida e contabilizar removidos.
- Download interrompido/hash divergente: descartar temporário e manter último snapshot publicado.
- Uma fonte vacinal indisponível: publicar as demais somente se o manifesto marcar explicitamente a ausência; nunca reutilizar dado antigo sem sua data.

## Risks and Constraints

- **NFR-DF-1:** Processar o volume descrito em uma estação local sem carregar colunas descartadas na camada analítica.
- **NFR-DF-2:** Execuções com as mesmas entradas e versão de regras devem produzir os mesmos hashes de tabelas normalizadas.
- **NFR-DF-3:** Nenhum artefato consumido pelo agente deve conter PII ou campos não listados no schema canônico.
- **NFR-DF-4:** O último snapshot válido deve permanecer utilizável após falha de atualização.

## Threats and Security Considerations

Validar URL/configuração contra allowlist, limitar tamanho de download, impedir path traversal, não executar conteúdo das fontes e evitar fórmulas CSV. Segredos, se necessários, vêm do ambiente e não entram no manifesto.

## Rollout, Migration, and Rollback

Primeira versão cria o schema `v1`. Nova versão de schema gera novo snapshot e mantém o anterior. Rollback seleciona explicitamente um snapshot publicado anterior; nunca sobrescreve artefatos.

## Observability

- Contagens por fonte, aceitos, rejeitados, duplicados e duração por etapa.
- Completude dos campos críticos.
- Watermarks e idade das fontes.
- Erros estruturados por código, sem conteúdo sensível.

## Capacity and Operations

Arquivos temporários são removidos após sucesso ou falha. O pipeline aceita snapshots pequenos de fixture para testes e snapshot completo para demo.

## Compliance

Dados públicos de saúde ainda exigem minimização e prevenção de reidentificação. A PoC publica somente agregados e não constrói perfis individuais.

## Acceptance Criteria

- **AC-DF-1 (FR-DF-1):** Modo ao vivo e modo local produzem o mesmo schema canônico para conteúdo equivalente.
- **AC-DF-2 (FR-DF-2, FR-DF-7):** Valores ignorados, datas inválidas e UF inválida são tratados e contabilizados conforme regra.
- **AC-DF-3 (FR-DF-3):** Duplicatas de fixture produzem uma linha canônica e contador de remoção correto.
- **AC-DF-4 (FR-DF-4, NFR-DF-3):** Tabelas analíticas não contêm campos fora da allowlist.
- **AC-DF-5 (FR-DF-5, FR-DF-6):** Snapshot publicado contém Parquet, DuckDB e manifesto verificável por hash.
- **AC-DF-6 (FR-DF-8, NFR-DF-4):** Falha estrutural não publica parcial nem remove o último snapshot válido.
- **AC-DF-7 (FR-DF-6):** Manifesto informa watermarks e completude das quatro famílias de dados.
- **AC-DF-8 (NFR-DF-2):** Duas execuções com entradas e versão de regras idênticas produzem hashes idênticos das tabelas normalizadas.

## Verification Plan

- Unit: parsers, normalizadores, datas, códigos e deduplicação.
- Integration: ingestão de fixtures de todas as fontes e inspeção do DuckDB.
- End-to-end: dois modos de entrada com conteúdo equivalente geram tabelas canônicas equivalentes.
- Operational: simular download truncado e comprovar preservação do snapshot anterior.

## Open Questions

Nenhuma questão bloqueadora. Identificadores concretos de distribuição/API pertencem à configuração da fonte e devem ser validados na primeira tarefa de implementação sem alterar este contrato.

## Change Log

| Version | Date | Summary |
|---|---|---|
| 1.0 | 2026-07-28 | Contrato inicial aprovado |
