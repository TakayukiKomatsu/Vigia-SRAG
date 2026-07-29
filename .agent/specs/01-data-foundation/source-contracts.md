# Anexo de contratos de fontes oficiais

> Status: DRAFT
> Version: 2.2
> Owner: T-DF-1
> Last Updated: 2026-07-29

Este anexo é normativo para SDD 01. `UNVERIFIED` é um bloqueio explícito, não
um valor a ser completado por suposição. Nenhum spec dependente recebe
`FINAL` antes de todos os itens e a fixture reduzida estarem verificados.

## Execução oficial reproduzível (SIVEP obrigatório)

`scripts/acquire_official_sources.py` é a única etapa com rede. Ela baixa o
SIVEP 2026 fixado abaixo e, separadamente, tenta o IBGE opcional. O arquivo
ignorado `data/raw/acquisition.json` registra, para cada fonte, `status`, hora
real de recuperação, URL oficial de landing e de recurso (separadas),
declaração e URL de evidência de licença/reuso, SHA-256, tamanho, encoding,
linhas, versão do dicionário e mapeamento selecionado. Hash, tamanho e linhas
esperados são constantes de contrato e nunca são alterados para acomodar um
novo download. Falha de SIVEP também grava o bloqueio ignorado
`runs/official-source-blocked.json`; falha de IBGE fica atestada como
indisponível e não bloqueia SIVEP.

`scripts/prepare_official_snapshot.py` não faz rede: aceita somente uma
aquisição SIVEP verificada, revalida o arquivo local e normaliza-o em streaming
para JSONL antes de publicar o snapshot minimizado. Sem IBGE atestado, a tabela
IBGE é vazia e mortalidade por 100 mil fica `unavailable`; CNES e PNI também
são sempre tabelas vazias e deixam pressão/uso de UTI e cobertura influenza
`unavailable`. A execução segue com qualidade `warning`, mas declara
explicitamente `golden_eligible=false`. Dados brutos, JSONL intermediário,
snapshots e run bundles são ignorados; nenhum deles é evidência rastreada no
repositório.

## Source Inventory — Evidence Ledger

| Família | Entrada oficial | Seleção do MVP | Estado |
|---|---|---|---|
| SIVEP-Gripe | `https://dadosabertos.saude.gov.br/dataset/srag-2019-a-2026` | 2025/2026 CSVs, UTF-8, 194 cols, semicolon, ISO datas | `PARTIAL` |
| CNES | `https://cnes.datasus.gov.br/pages/downloads/arquivosBaseDados.jsp` | 202606 competência, 27 LT{UF}.dbc, categorias/licença bloqueadas | `PARTIAL` |
| IBGE | `https://ftp.ibge.gov.br/Estimativas_de_Populacao/Estimativas_2025/` | POP2025_20260113.ods, Brasil 213.421.037 (ref 2025-07-01) | `VERIFIED` |
| PNI influenza | `https://www.gov.br/saude/pt-br/composicao/seidigi/demas/campanhas-de-vacinacao/vacinacao-contra-a-influenza` | Painel 2026-07-29 06:31:04, NE/CO/S/SE, 46,55% | `INELIGIBLE` |

---

## SIVEP-Gripe 2025 — Artefato Verificado

### Identidade Oficial
- **Portal**: https://dadosabertos.saude.gov.br/dataset/srag-2019-a-2026
- **ID Recurso**: `20c49de3-ddc3-4b76-a942-1518eaae9c91`
- **Licença**: CC BY-ND 3.0 BR (VERIFIED)
- **URL Resolvida**: https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG/2025/INFLUD25-27-07-2026.csv

### Metadados Físicos — Verificados
- **Tamanho**: 381.900.544 bytes
- **SHA-256**: `b5def80ae35092c5f64b4766d6d2e5785bdd63978a9aae51cc90521a91a6aaaa`
- **Linhas de dados**: 336.260 (excluindo cabeçalho; verificado via wc -l)
- **Colunas**: 194 (idêntico a 2026)
- **Encoding**: UTF-8 (sem BOM; verificado via hex inspection)
- **Delimitador**: ponto-e-vírgula (`;`); todos campos entre aspas duplas
- **Datas**: ISO 8601 timestamps (AAAA-MM-DDTHH:MM:SS.000Z) no CSV
- **S3 Download**: 2026-07-27T03:38:40Z (last_modified no portal)
- **Máximo DT_SIN_PRI Observado (Snapshot 2026-07-27)**: 2026-01-03 (VERIFIED via profiling exhaustivo)

### Schema — Dicionário Oficial e Campos Verificados
- **Fonte Dicionário**: `dicionario-de-dados-2019-a-2025.pdf` (last updated 2026-01-29)
- **Cobertura**: Notificações SRAG 2019–2025; versão 2026 usa schema idêntico (194 colunas, byte-for-byte header match)
- **Campos MVP Verificados**:

| Campo Canônico | Campo Origem (OFICIAL) | Col | Tipo | Semântica |
|---|---|---|---|---|
| notification_key | `NU_NOTIFIC` | 1 | varchar | System-generated ID; único por ano; digit 1=form type (3=SRAG hospitalizado) |
| notification_date | `DT_NOTIFIC` | 2 | date | Data preenchimento formulário; ≤ DT_DIGITA |
| symptom_onset | `DT_SIN_PRI` | 4 | date | Primeira data de sintoma; base para Semana Epidemiológica; <= DT_NOTIFIC |
| hospitalization_flag | `HOSPITAL` | 69 | code | 1=Sim, 2=Não, 9=Ignorado |
| hospitalization_date | `DT_INTERNA` | 70 | date | Data internação (se HOSPITAL=1); ≥ DT_SIN_PRI |
| hospitalization_uf | `SG_UF_INTE` | 71 | char(2) | UF de internação (onde paciente foi hospitalizado) |
| icu_flag | `UTI` | 77 | code | 1=Sim, 2=Não, 9=Ignorado |
| icu_entry_date | `DT_ENTUTI` | 78 | date | Data entrada UTI (se UTI=1); ≥ DT_SIN_PRI |
| icu_exit_date | `DT_SAIDUTI` | 79 | date | Data saída UTI (se UTI=1); ≥ DT_ENTUTI |
| evolution | `EVOLUCAO` | 111 | code | **1=Cura, 2=Óbito SRAG, 3=Óbito outras causas, 9=Ignorado** |
| evolution_date | `DT_EVOLUCA` | 112 | date | Data alta (EVOLUCAO=1) ou óbito (EVOLUCAO=2). **CRÍTICO: campo NÃO disponível quando EVOLUCAO=3** |
| closure_date | `DT_ENCERRA` | 113 | date | Data encerramento de caso (quando preenchida); não é proxy de data de óbito por outras causas |
| digitization_date | `DT_DIGITA` | 114 | datetime | Data entrada no sistema SIVEP. **Explicitamente NÃO atualizado em edições posteriores** |
| residence_uf | `SG_UF` | 22 | char(2) | UF de residência (distinto de SG_UF_NOT e SG_UF_INTE) |

### Semântica e Blocadores

**Óbito por SRAG — VERIFIED**:
- Campo `EVOLUCAO = 2` codifica explicitamente "Óbito — SRAG/causa respiratória" (VERIFIED death from SRAG/respiratory cause)
- Campo `EVOLUCAO = 3` codifica "Óbito por outras causas" (death from other cause)
- **CRÍTICO**: Quando `EVOLUCAO = 3`, o campo `DT_EVOLUCA` está desabilitado (não preenchido); `DT_ENCERRA` é data de encerramento de caso, não proxy de data de óbito (óbito por outras causas não tem data conhecida em dados públicos)
- Código `9 = Ignorado` deve permanecer distinto de código `2 = Não`

**Timestamp de Atualização — NÃO EXISTE em dados públicos**:
- `DT_DIGITA` registra apenas a entrada inicial no SIVEP
- Dicionário explicitamente documenta: "Não é atualizada se houver alterações posteriores de dados"
- **Bloqueador Hard**: Não existe `DT_ATUALIZA`, `DT_ALTERACAO`, ou equivalente na schema pública (194 colunas)
- **Arquivo Anual**: Dentro de um arquivo anual (2025 ou 2026), `NU_NOTIFIC` é o identificador estável para deduplicação, mas não há precedência de atualização entre versões

**Deduplicação Oficial Indisponível**:
- CGCOVID internamente usa `NU_CPF` e `NU_CNS` para agrupar + nome + data nascimento + sexo; dentro do grupo, remove registros com DT_SIN_PRI dentro de 30 dias, mantendo maior completude
- Dados públicos CSV: `NU_CPF` e `NU_CNS` são REMOVIDOS antes de publicação (anonymization per LGPD 13.709/2018)
- **Bloqueador**: Algoritmo oficial de deduplicação não pode ser replicado com dados públicos

**Status de Bloqueadores Críticos SIVEP**:
- Fixture reduzida + redistributível legal (CC BY-ND restringe derivadas): `UNVERIFIED` — requer permissão escrita CGCOVID/SVSA
- Update precedence among versions 2025/2026: NU_NOTIFIC non-recurrence VERIFIED (zero overlap between files; no record appears in both 2025 and 2026 snapshots)

## SIVEP-Gripe 2026 — Artefato Verificado

### Identidade Oficial
- **Portal**: https://dadosabertos.saude.gov.br/dataset/srag-2019-a-2026
- **ID Recurso**: `74091efc-3f75-42e8-a6fa-6b79a8d30582`
- **Licença**: CC BY-ND 3.0 BR (VERIFIED)
- **URL Resolvida**: https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG/2026/INFLUD26-27-07-2026.csv

### Metadados Físicos — Verificados
- **Tamanho**: 198.233.708 bytes
- **SHA-256**: `5b1de50c4ca58b1c7068d61f58b42772d1634a06917d41443443fff1fdd359fb`
- **Linhas de dados**: 177.445 (excluindo cabeçalho; verificado via wc -l)
- **Colunas**: 194 (idêntico a 2025)
- **Encoding**: UTF-8 (sem BOM)
- **Delimitador**: ponto-e-vírgula (`;`); todos campos entre aspas duplas
- **Datas**: ISO 8601 timestamps (AAAA-MM-DDTHH:MM:SS.000Z) no CSV
- **S3 Download**: 2026-07-27T03:38:43Z (last_modified no portal)
- **Cobertura de Dados**: Notificações SRAG janeiro–julho 27, 2026 (data do snapshot)
- **Máximo DT_SIN_PRI Observado (Snapshot 2026-07-27)**: 2026-07-26 (VERIFIED via profiling exhaustivo)

### Schema — Idêntico a 2025
- Mesmo dicionário oficial (`dicionario-de-dados-2019-a-2025.pdf`)
- Mesmos 194 campos (byte-for-byte header match confirmado)
- Todos campos MVP idênticos (NU_NOTIFIC, DT_SIN_PRI, HOSPITAL, UTI, DT_ENTUTI, DT_SAIDUTI, EVOLUCAO, DT_EVOLUCA, SG_UF, SG_UF_INTE)

### Bloqueadores — Idênticos a 2025
- Deduplicação oficial (CPF/CNS) indisponível em dados públicos
- `DT_DIGITA` não atualizado em edições; nenhum campo de update timestamp na schema
- Precedência entre registros 2025/2026: `UNVERIFIED`
- Fixture redistributível legal: `UNVERIFIED`

---

## IBGE — Estimativas de População 2025 (VERIFIED)

### Identidade Oficial
- **Landing Page**: https://www.ibge.gov.br/estatisticas/sociais/populacao/9103-estimativas-de-populacao.html
- **Diretório FTP**: https://ftp.ibge.gov.br/Estimativas_de_Populacao/Estimativas_2025/
- **Artefato Selecionado**: `POP2025_20260113.ods` (versão TCU/corrigida, 2026-01-13)

### Metadados Físicos — Verificados
- **Tamanho**: 212.846 bytes
- **SHA-256**: `33dc6f79def9522e282cd69b87a9ce75327a81239d6060d9c8f9f5a49bd2a1b5`
- **Formato**: ODS (Open Document Spreadsheet)
- **Linhas de Dados**: ~5.599 (1 Brasil + 27 UFs + 5.571 municípios)
- **Retrieval**: 2026-07-29 (data/raw/ibge/POP2025_20260113.ods)

### Valor Brasil — VERIFIED
| Atributo | Valor | Fonte Confirmada |
|---|---|---|
| População | 213.421.037 | IBGE Agência de Notícias 2025-08-28; SIDRA API; FTP PDF |
| Geografia | Brasil (N1) | Agregado nacional |
| Data de Referência | 2025-07-01 | Estimativa meio de ano (padrão IBGE) |

### Semântica Temporal
- **Referência**: 2025-07-01 (midyear estimate)
- **Publicação DOU**: 2025-08-28 (Portaria IBGE 1.098/2025)
- **Atualização TCU**: 2026-01-13 (correções judiciais)
- **Periodicidade**: Anual (sempre 1º de julho do ano estimado)
- **Próximas Estimativas**: Estimativas 2026 (ref 2026-07-01) esperadas ~2026-08-31; ainda não publicadas em 2026-07-29

### Mapeamento Canônico
| Campo Origem | Campo Canônico | Tipo | Valor |
|---|---|---|---|
| BRASIL | year | INT | 2025 |
| BRASIL | geography | CHAR(2) | BR |
| POPULAÇÃO ESTIMADA | population_official | INT | 213421037 |
| ref 2025-07-01 | reference_date | DATE | 2025-07-01 |

### Legal e Reuso — VERIFIED
- **Base Legal**: Decreto nº 8.777/2016 (Política de Dados Abertos); Lei nº 12.527/2011 (LAI); IN SLTI nº 4/2012 (INDA)
- **Licença de Dados**: Domínio público (Decreto 8.777/2016)
- **Atribuição Requerida**: IBGE, Diretoria de Pesquisas (DPE), Coordenação de População e Indicadores Sociais (COPIS)
- **Reuso**: Dados agregados não-pessoais, livremente reutilizáveis

---

## CNES — Cadastro Nacional de Estabelecimentos de Saúde (PARTIAL)

### Identidade Oficial
- **Portal**: https://cnes.datasus.gov.br/pages/downloads/arquivosBaseDados.jsp
- **FTP Base**: ftp://ftp.datasus.gov.br/dissemin/publicos/CNES/200508_/Dados/LT/
- **Formato Arquivo**: `LT{UF}{AAAAMM}.dbc`
- **Competência Selecionada**: **202606** (junho 2026) — LATEST CONFIRMED
- **Tabela Base**: LFCES002 / RL_ESTAB_COMPLEMENTAR (complementary/ICU beds)

### Cobertura — Verificada
- **27 Arquivos Presentes**: AC, AL, AM, AP, BA, CE, DF, ES, GO, MA, MG, MS, MT, PA, PB, PE, PI, PR, RJ, RN, RO, RR, RS, SC, SE, SP, TO
- **Localização Local**: data/raw/cnes/202606/ (total ~680 KB)
- **Formato**: DBC (compressed DBF, proprietary DATASUS)
- **Encoding**: ISO-8859-1

### Schema DBC — Declarado (UNVERIFIED para decodificação)
| Campo | Tipo | Semântica |
|---|---|---|
| CNES | CHAR(7) | Código nacional estabelecimento |
| CODUFMUN | CHAR(6) | IBGE estado(2) + município(4) |
| TP_LEITO | CHAR(2) | '03' = complementar/UTI |
| COD_LEITO | CHAR(2) | Código específico subtipo leito |
| QT_EXIST | NUMBER(6) | Leitos ativos existentes |
| QT_SUS | NUMBER(6) | Leitos SUS habilitados |
| QT_NSUS | NUMBER(6) | Leitos não-SUS (derivado) |

### ICU Codes — Allowlist Conservador Exato (Congelado)

**Allowlist Exacto Aceito — T-DF-2 e Subsequentes**:
Somente os seguintes códigos `COD_LEITO` são aceitos em CNES 202606:

| Código | Categoria | Status | Basis | Motivo |
|---|---|---|---|---|
| 61 | UTI Adulto | **ACEITO** | CNES/CONASS | Domain table; sem ambiguidade em 202606 |
| 62 | UTI Infantil/Pediátrica | **ACEITO** | CNES/CONASS | Domain table; sem ambiguidade em 202606 |
| 63 | UTI Neonatal | **ACEITO** | CNES/CONASS | Domain table; sem ambiguidade em 202606 |
| 75 | UTI Adulto (Tipo II) | **ACEITO** | Portaria SAES 3511/2025 | Sem ambiguidade em jan-2026+ |
| 76 | UTI Adulto (Tipo III) | **ACEITO** | Portaria SAES 3511/2025 | Sem ambiguidade em jan-2026+ |
| 79 | UTI Pediátrica (Tipo III) | **ACEITO** | Portaria SAES 3511/2025 | Sem ambiguidade em jan-2026+ |
| 80 | UTI Neonatal (Tipo I) | **ACEITO** | Portaria SAES 3511/2025 | Sem ambiguidade em jan-2026+ |
| 81 | UTI Neonatal (código 81; subtipo não usado no MVP) | **ACEITO** | CNES/CONASS | Conservative label; domain table |
| 82 | UTI Neonatal (Tipo III) | **ACEITO** | Portaria SAES 3511/2025 | Sem ambiguidade em jan-2026+ |

**Códigos Excluídos — Bloqueadores até Verificação Explícita**:

| Código | Categoria | Motivo Exclusão |
|---|---|---|
| 74 | UTI Adulto I → Pediátrica (ambígua) | Significado muda dez-2025 vs jan-2026+; time-series ambígua |
| 78 | UTI Pediátrica II (status incerto) | Não em Annex I Portaria 3511/2025; status `UNVERIFIED` |
| 51 | UTI II ... SRAG COVID-19 | Pós-pandemia; status classificação `UNVERIFIED` |
| 52 | UTI II ... SRAG COVID-19 | Pós-pandemia; status classificação `UNVERIFIED` |
| 96 | Suporte ventilatório pulmonar COVID-19 | Pós-pandemia; status classificação `UNVERIFIED` |
| 64–65 | Intermediárias/UCI | Intermediárias (não UTI); fora do escopo |
| 83 | Unidade Coronariana (UCO) | Unidade coronariana; fora do escopo |
| 85–86 | Unidade Coronariana (UCO) | Unidade coronariana; fora do escopo |
| 77 | UTI Pediátrica I (deletada) | Deletada/repurposada pré-jan-2026; não consta em dados atuais |
| 92–95 | Intermediárias/UCI | Intermediárias (não UTI); fora do escopo |

**Status CNES-202606**:
- Allowlist aplicável **somente à competência 202606** (junho 2026)
- Mudança para competência distinta reabre mapeamento de códigos
- Ambiguidades históricas (74, 78) bloqueadas até evidência explícita
- COVID-19 (51/52/96) bloqueado até reclassificação oficial pós-pandemia

### Bloqueadores Críticos — CNES
1. **B1 — Código 74 Ambiguidade**: dez-2025 (Adulto) vs jan-2026+ (Pediátrico); time-series ambígua
2. **B2 — Categoria 78 Status**: Deletada ou não-mapeada pós-Portaria 3511?
3. **B3 — DBC Decodificação**: Raw arquivo não decodificado; COMPETEN campo status `UNVERIFIED`
4. **B4 — Licença CC BY-ND**: Derivadas (filtrados para leitos UTI) requerem revisão legal
5. **B5 — QT_EXIST Plenitude**: Sempre preenchido? Lacunas históricas?

---

## PNI — Influenza 2026 (NÃO-ELEGÍVEL para as_of=2026-07-26)

### Identidade Oficial
- **Landing Page**: https://www.gov.br/saude/pt-br/composicao/seidigi/demas/campanhas-de-vacinacao/vacinacao-contra-a-influenza
- **Painel Dashboard**: https://infoms.saude.gov.br/extensions/SEIDIGI_DEMAS_ESTRATEGIA_INFLUENZA_RESIDENCIA/index.html?regiao=nacional
- **Dataset Aberto**: https://dadosabertos.saude.gov.br/dataset/doses-aplicadas-pelo-programa-de-nacional-de-imunizacoes-pni-2026
- **ID Dataset**: `9a25b796-80e3-444a-a4e7-405f5596d8ab`

### Campanha 2026 — Estrutura
- **Período Principal (NE/CO/S/SE)**: 2026-03-28 a 2026-05-30
- **Período Norte**: 2º semestre 2026 (campanha separada)
- **Estratégia PDF**: ISBN 978-85-334-2950-5, 1ª edição 2026
- **Imunobiológico**: INF3 (co_vacina=33), Butantan, ANVISA 1.2234.0020
- **Cepas**: A/Missouri/11/2025 (H1N1), A/Singapore/GP20238/2024 (H3N2), B/Austria/1359417/2021

### Grupos-Alvo Rotina (Meta ≥90%) — NE/CO/S/SE Apenas
| Grupo | Denominador | Fonte |
|---|---|---|
| Crianças 6m–<6 anos | 12.541.191 | SINASC 2024 |
| Idosos ≥60 anos | 33.290.252 | Estimativas MS/IBGE 2025 |
| Gestantes | 261.817 | SINASC 2024 |
| Puérperas ≤45 dias | 625.214 | SINASC 2024 |
| **Subtotal Rotina** | **46.718.474** | — |

### Observação Painel — Capturada 2026-07-29 [INELIGÍVEL para as_of=2026-07-26]

| Atributo | Valor | Observação |
|---|---|---|
| **Timestamp Captura** | 2026-07-29 06:31:04 | **POSTERIOR ao as_of=2026-07-26** |
| **Numerador** | 22.074.844 | Doses INF3, Rotina, NE/CO/S/SE |
| **Denominador** | 47.424.778 | Rotina target com ajustes |
| **Cobertura %** | 46,55% | 22.074.844 ÷ 47.424.778 |
| **Abrangência** | NE/CO/S/SE | Norte campanha separada |
| **Caveat Norte** | 2º semestre 2026 | Não incluída nesta observação |
| **Fonte Captura** | Painel JavaScript infoms.saude.gov.br | Requer browser JS |
| **Método Acesso** | Dinâmico, atualização diária | Não é CSV estável |

**CRÍTICO — Ineligibilidade Temporal**:
- Observação publicada: **2026-07-29 06:31:04**
- Data padrão as_of: **2026-07-26**
- Relação: **Posterior** ao as_of (violaria contrato temporal)
- **Ação**: Elevar `as_of` para ≥2026-07-29 ou manter a métrica `unavailable` para `as_of=2026-07-26`; nunca retroagir o cutoff.

### Bloqueadores — PNI
1. **B1 — Ineligibilidade Temporal**: Posterior a as_of=2026-07-26
2. **B2 — Discrepância Denominador**: 47.424.778 vs estratégia ~46.718.474
3. **B3 — Campanha Norte**: Ainda não finalizada em 2026-07-29
4. **B4 — CSV Raw**: SHA-256, tamanho, row count, encoding não verificados
5. **B5 — Deduplicação**: Regra oficial `st_documento`/`co_troca_documento`/`dt_deleted` não confirmada
6. **B6 — Códigos Grupo-Atendimento**: Valores `co_vacina_grupo_atendimento` não mapeados
7. **B7 — Licença Fixture**: CC BY-ND 3.0 vs Lei 12.527/2011 — supersessão `UNVERIFIED`


### PNI Elegibilidade Condicional — Regra de as_of

**Observação PNI 2026 NE/CO/S/SE**:
- População-alvo elegível (population_scope): NE, CO, S, SE (regional, não nacional)
- Nunca rotulada como nacional; quando elegível pelo cutoff, permanece suplemento limitado
- **Elegível somente se publicada ≤ as_of solicitado**
- Painel atual (2026-07-29 06:31:04) > as_of padrão (2026-07-26) → `INELIGIBLE`
- Para `as_of` ≥2026-07-29: pode participar do golden como suplemento scoped, desde que os bloqueadores de evidência estejam resolvidos
- Para `as_of` <2026-07-29: fica indisponível e não satisfaz a métrica

**Política de golden rebaselined**: PNI influenza é a única métrica autorizada
a carregar `population_scope` regional. Ela nunca satisfaz um requisito
nacional, mas pode integrar o golden como suplemento não-nacional. As outras
cinco métricas devem permanecer nacionais e sem escopo.

---

## Fixture Types — Definição Explícita

**Synthetic Public Fixtures** (determinísticas, reproducíveis):
- Dados minimizados, anonymizados, conformes a contratos verificados
- Cenários de normalização, deduplicação, invalidade e quarentena inclusos
- Compatíveis com CC BY-ND (nenhuma derivação de dados reais)
- Utilizados em T-DF-2 até T-DF-6 para testes de determinismo, reproduzibilidade e privacidade
- Versão git autorizada

**Real Reduced Fixture** (snapshot reduzido, gate T-DF-1):
- Minimização verificada de SIVEP 2025 ou 2026 (campos humanitários apenas)
- Estado de elegibilidade correspondente definido em source-contracts.md
- **Requer permissão legal explícita** para redistribuição (CC BY-ND vs LGPD)
- Utilizado somente após resolução de TODOS bloqueadores em source-contracts.md
- Spec permanece `DRAFT` enquanto real-fixture estiver `UNVERIFIED`
- Manifest, hash, schema e row counts armazenados em versionamento (sem dados clínicos)
---

## Required Record Per Artifact — Status Completude

| Campo | SIVEP 2025 | SIVEP 2026 | IBGE | CNES | PNI |
|---|---|---|---|---|---|
| landing/resource | ✓ | ✓ | ✓ | ✓ | ✓ |
| legal | ✓ (CC BY-ND 3.0 BR VERIFIED) | ✓ (CC BY-ND 3.0 BR VERIFIED) | ✓ | ✗ `UNVERIFIED` (CC BY-ND reuso) | ✗ `UNVERIFIED` |
| retrieval | ✓ (2026-07-27) | ✓ (2026-07-27) | ✓ (2026-07-29) | ✓ (202606) | ✗ `INELIGIBLE` |
| watermark | ✓ (até 2026-07-27) | ✓ (até 2026-07-27) | ✓ (ref 2025-07-01) | ✓ (202606) | ✗ `INELIGIBLE` |
| schema | ✓ (dicionário verificado) | ✓ (dicionário verificado) | ✓ | ✗ `UNVERIFIED` (DBC) | ✓ |
| physical | ✓ (SHA-256 verificado) | ✓ (SHA-256 verificado) | ✓ | ✓ (local) | ✗ `UNVERIFIED` |
| mapping | ✓ (NU_NOTIFIC, DT_SIN_PRI, UTI, EVOLUCAO, etc.) | ✓ (campos idênticos a 2025) | ✓ | ✗ `UNVERIFIED` (74/78) | ✗ `UNVERIFIED` |
| semantics | ✓ (EVOLUCAO=2 SRAG; DT_DIGITA inserção, não update) | ✓ (idêntico a 2025) | ✓ (ref 2025-07-01) | ✗ `UNVERIFIED` | ✗ `UNVERIFIED` |
| codes | ✓ (EVOLUCAO: 1=Cura, 2=SRAG, 3=outras, 9=Ignorado; HOSPITAL/UTI: 1/2/9) | ✓ (idêntico a 2025) | N/A | ✗ `UNVERIFIED` (74/78) | ✗ `UNVERIFIED` |
| duplicates | ✗ `UNVERIFIED` (NU_NOTIFIC estável/ano; sem campo update) | ✗ `UNVERIFIED` (NU_NOTIFIC estável/ano; sem campo update) | N/A | N/A | ✗ `UNVERIFIED` |
| failure | ✗ VERIFIED non-recurrence (2025↔2026 disjoint keys); ✗ dedup official unavailable | ✗ VERIFIED non-recurrence (2025↔2026 disjoint keys); ✗ dedup official unavailable | N/A | ✗ `UNVERIFIED` | ✗ `UNVERIFIED` |
| fixture | ✗ `UNVERIFIED` (CC BY-ND proíbe derivadas; transformação requer permissão) | ✗ `UNVERIFIED` (CC BY-ND proíbe derivadas; transformação requer permissão) | N/A | ✗ `UNVERIFIED` | ✗ `UNVERIFIED` |

---

## Canonical Mapping Gate — Progresso

- **SIVEP**: ✓ Notificação (NU_NOTIFIC), ✓ Sintomas (DT_SIN_PRI), ✓ Internação (HOSPITAL/DT_INTERNA/SG_UF_INTE), ✓ UTI (UTI/DT_ENTUTI/DT_SAIDUTI), ✓ Evolução (EVOLUCAO/DT_EVOLUCA), ✓ Óbito SRAG (EVOLUCAO=2 VERIFIED; EVOLUCAO=3 sem data; DT_DIGITA inserção), ✓ UF residência (SG_UF), ✗ Update timestamp (não existe; deduplicação oficial indisponível em dados públicos)
- **CNES**: ✓ Competência (202606), ✓ UF, ✗ Códigos (74/78), ✗ Leitos existentes
- **IBGE**: ✓ Ano, ✓ Geografia, ✓ População (213.421.037)
- **PNI**: ✓ Campanha, ✓ Imunobiológico, ✓ Grupos, ✓ Período, ✓ Residência, ✗ Numerador/Denominador elegível (painel não-elegível), ✗ Cobertura elegível, ✗ Atualização elegível, ✗ Fonte estável

---

## Current Blockers — Bloqueadores Explícitos

T-DF-1 permanece **DRAFT** enquanto os seguintes itens forem `UNVERIFIED` ou `INELIGIBLE`:

### SIVEP (2025/2026)
1. **Deduplicação oficial indisponível**: CGCOVID usa NU_CPF/NU_CNS (anonymized away em dados públicos); algoritmo não replicável
2. **Fixture redistributível legal**: CC BY-ND 3.0 BR proíbe derivadas; qualquer minimização (coluna drop, masking) é derivada; requer permissão escrita CGCOVID/SVSA
3. **Máximo DT_SIN_PRI observado**: VERIFIED via profiling — 2026-01-03 (2025 snapshot) e 2026-07-26 (2026 snapshot)
4. **NU_NOTIFIC recorrência entre 2025/2026**: VERIFIED zero overlap — no record appears in both snapshots

### CNES
5. **Código 74 ambiguidade**: Adulto (até dez-2025) vs Pediátrico (jan-2026+); time-series ambígua
6. **Código 78 status**: Deletada ou não-mapeada pós-Portaria 3511?
7. **Códigos COVID (51/52/96)**: Status pós-pandemia (revogados/ativos?)
8. **DBC decodificação**: Raw arquivo não decodificado; COMPETEN campo status `UNVERIFIED`
9. **QT_EXIST plenitude**: Sempre preenchido? Lacunas históricas?
10. **Licença CC BY-ND**: Derivadas permitidas?

### PNI
11. **Ineligibilidade temporal**: Painel 2026-07-29 > as_of=2026-07-26 — elevar `as_of` ou manter PNI indisponível
12. **Discrepância denominador**: 47.424.778 vs 46.718.474
13. **Campanha Norte 2º semestre**: Ainda pendente em 2026-07-29
14. **CSV raw**: SHA-256, tamanho, row count, encoding, delimiter
15. **Deduplicação**: Regra oficial de filtro
16. **Códigos grupo-atendimento**: Valores `co_vacina_grupo_atendimento`
17. **Licença fixture**: CC BY-ND vs Lei 12.527/2011

Nenhum spec dependente (SDDs 02–04) recebe `FINAL` até resolução destes bloqueadores e geração da fixture reduzida verificada.
