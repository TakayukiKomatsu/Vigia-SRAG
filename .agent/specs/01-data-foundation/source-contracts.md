# Anexo de contratos de fontes oficiais

> Status: DRAFT
> Version: 2.0
> Owner: T-DF-1
> Last Updated: 2026-07-28

Este anexo é normativo para SDD 01. `UNVERIFIED` é um bloqueio explícito, não
um valor a ser completado por suposição. Nenhum spec dependente recebe
`FINAL` antes de todos os itens e a fixture reduzida estarem verificados.

## Source Inventory

| Família | Entrada oficial | Seleção do MVP | Estado |
|---|---|---|---|
| SIVEP-Gripe | `https://dadosabertos.saude.gov.br/dataset/srag-2019-a-2026` | CSVs epidemiológicos 2025 e 2026 resolvidos a partir do catálogo oficial | `UNVERIFIED` |
| CNES | `https://cnes.datasus.gov.br/pages/downloads/arquivosBaseDados.jsp` | competência completa mais recente com categorias compatíveis de leitos UTI existentes | `UNVERIFIED` |
| IBGE | `https://ftp.ibge.gov.br/Estimativas_de_Populacao/Estimativas_2025/` | estimativa oficial do Brasil aplicável ao período de mortalidade | `UNVERIFIED` |
| PNI influenza | `https://www.gov.br/saude/pt-br/composicao/seidigi/demas/campanhas-de-vacinacao/vacinacao-contra-a-influenza` | observação oficial mais recente da campanha 2026 publicada até `as_of` | `UNVERIFIED` |

## Required Record Per Artifact

Cada CSV, arquivo ou observação selecionada precisa registrar:

| Campo | Regra |
|---|---|
| landing/resource | URL oficial, URL resolvida e identificador do recurso |
| legal | licença, termo de uso ou nota de reutilização aplicável |
| retrieval | timestamp UTC e método de recuperação |
| watermark | data/competência máxima coberta pela fonte |
| schema | versão/data do dicionário e campos obrigatórios |
| physical | tamanho em bytes, SHA-256, linhas, encoding e delimitador |
| mapping | campo de origem para campo canônico e tipo |
| semantics | geografia, residência/estabelecimento, evento e calendário |
| codes | válidos, negativos, desconhecidos, ignorados e excluídos |
| duplicates | chave e ordem determinística de precedência |
| failure | staleness, incompatibilidade, rejeição e substituição |
| fixture | método de redução, licença/reuso e SHA-256 da fixture |

## Canonical Mapping Gate

O mapeamento final deve cobrir:

- SIVEP: notificação, atualização, início dos sintomas, internação, entrada e
  saída de UTI, evolução, data da evolução e UFs necessárias à validação;
- CNES: competência, UF, código/categoria UTI e leitos existentes;
- IBGE: ano, geografia Brasil e população oficial;
- PNI: campanha, imunobiológico, grupos-alvo, período, residência, numerador,
  denominador, cobertura publicada, atualização e fonte.

## Verification Procedure

1. Resolver o recurso a partir da entrada oficial.
2. Baixar em diretório ignorado por Git.
3. Registrar metadados físicos sem alterar o arquivo.
4. Confrontar campos/códigos com o dicionário oficial.
5. Validar semântica temporal e geográfica com uma amostra real.
6. Gerar fixture mínima permitida, minimizada e sem identificadores.
7. Recalcular hashes e verificar leitura determinística.
8. Trocar `UNVERIFIED` por `VERIFIED` somente com evidência versionada.

## Current Blockers

- Recursos resolvidos, hashes, tamanhos, linhas, encodings e delimitadores:
  `UNVERIFIED`.
- Categorias CNES compatíveis e regra de leitos existentes: `UNVERIFIED`.
- Campo/código SIVEP de óbito por SRAG e datas usadas pelas métricas:
  `UNVERIFIED`.
- Numerador, denominador, grupos-alvo e data da observação PNI 2026:
  `UNVERIFIED`.
- Fixture real reduzida e permitida: `UNVERIFIED`.

Enquanto esta seção contiver `UNVERIFIED`, SDDs 01–04 permanecem `DRAFT`.
