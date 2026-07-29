# SRAG SDD v2.0 Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` to implement this plan task-by-task.

**Goal:** Rewrite the four SRAG SDD packages so their requirements, acceptance scenarios, and five-day backlog are sufficient and explicitly traceable to every mandatory obligation in `Desafio de GenAI.txt`.

**Architecture:** Keep four bounded SDD packages. Treat each `spec.md` as the normative contract, each `acceptance.feature` as executable evidence, and each `tasks.md` as the future implementation backlog. Add one cross-package traceability matrix, one source-contract annex, and one isolated Stretch backlog. Exact IDs connect challenge obligations to requirements, acceptance criteria, tasks, and deliverable evidence.

**Tech Stack:** Markdown, Gherkin, Git, `rg`, and small read-only Python validation snippets.

**Global Constraints:**

- This plan rewrites planning artifacts only; it does not implement the Python application.
- All repository shell commands begin with `rtk`, per `/Users/takayuki/.codex/RTK.md`.
- Preserve unrelated and untracked work. In particular, do not add `.omc/`, `.superpowers/`, or `Desafio de GenAI.txt`.
- The challenge document is restricted material. Use it locally for verification, but do not quote or commit it to the public repository.
- Use Portuguese (Brazil) for the SDD content and English identifiers for machine-readable links.
- Keep the four existing package directories and rewrite them in place as version `2.0`.
- Keep all four specs at `DRAFT` during this documentation rewrite. Promotion is evidence-gated:
  - SDD 01 requires exact source contracts plus a verified reduced real fixture.
  - SDD 02 requires SDD 01 contracts to be frozen and its formula/period fixture to pass.
  - SDD 03 additionally requires the configured default OpenAI model to pass a structured-output smoke test.
  - SDD 04 requires SDDs 01–03 to be `FINAL`.
- The MVP is Brazil-only. UF reporting belongs only in Stretch.
- Health data inputs are pinned official snapshots. Only Google News RSS is live during report generation.
- The required vaccination metric is official 2026 influenza target-population coverage. COVID-19 vaccination belongs only in Stretch.
- The report is HTML. The only required PDF is the conceptual architecture diagram.
- OpenAI is the only live LLM provider in the MVP; deterministic tests use a fake.
- The mandatory backlog contains exactly 28 tasks: 7 data, 7 metrics, 8 agentic reporting, and 6 governance/delivery tasks.
- Every mandatory task carries explicit `CH-*`, `FR-*` or `NFR-*`, `AC-*`, priority, dependency, day, and verifiable result fields.
- Never use ID ranges such as `FR-MT-2..FR-MT-5`; enumerate every ID.
- Do not invent source metadata, resource IDs, field codes, hashes, or a default OpenAI model. Failed verification keeps the relevant status `DRAFT`.
- Commit only the files named by each plan task.

## Completion Contract

The rewrite is complete when:

1. `CH-01` through `CH-19` each map to at least one requirement, acceptance criterion, mandatory task, and concrete evidence.
2. Every `FR-*` and `NFR-*` has acceptance coverage.
3. Every `AC-*` is represented by at least one Gherkin scenario and at least one mandatory task.
4. Every mandatory task has a valid dependency chain and fits Days 1–5.
5. The mandatory task count is 28 and Stretch work is excluded from that count.
6. Brazil-only scope, four required metrics, two charts, live news, OpenAI commentary, auditability, public delivery, and architecture PDF are all explicit.
7. Normal degradation is distinct from the strict golden-run acceptance gate.
8. No spec claims `FINAL` before its evidence gate passes.

## Canonical Requirement Inventory

Use these IDs and meanings consistently; do not silently retain the v1 meanings.

### SDD 01 — Data Foundation

| ID | Normative meaning |
|---|---|
| `FR-DF-1` | Maintain a verified contract for each official SIVEP, CNES, IBGE, and PNI input. |
| `FR-DF-2` | Load only pinned local snapshots for SIVEP 2025/2026, latest complete CNES month, applicable IBGE population, and latest applicable 2026 influenza observation. |
| `FR-DF-3` | Normalize the minimal Brazil-level canonical schema without converting unknown or ignored values into negative values. |
| `FR-DF-4` | Apply deterministic deduplication, field-level invalidity handling, reason codes, and structural quarantine. |
| `FR-DF-5` | Expose only minimized analytical data; no row-level clinical data or technical keys may reach the agent-facing boundary. |
| `FR-DF-6` | Materialize a read-only analytical DuckDB plus immutable source/table manifests, hashes, counts, schemas, and watermarks. |
| `FR-DF-7` | Compute metric-specific completeness and enforce the `>=90`, `70–<90`, and `<70` quality states plus structural overrides. |
| `FR-DF-8` | Publish atomically and preserve the last valid snapshot when contract, hash, schema, or coverage checks fail. |
| `NFR-DF-1` | Identical source bytes and rule versions produce identical normalized content and hashes. |
| `NFR-DF-2` | Every output is traceable to source resource, retrieval, watermark, schema version, and transform version. |
| `NFR-DF-3` | Outputs, logs, fixtures, and agent boundaries contain no direct identifiers or row-level clinical records. |
| `NFR-DF-4` | A documented benchmark processes at least 165,000 SIVEP rows successfully and records elapsed time, peak memory, and machine context. |

Acceptance IDs: `AC-DF-1` source-contract gate; `AC-DF-2` pinned ingestion; `AC-DF-3` normalization/dedup/quarantine; `AC-DF-4` minimization; `AC-DF-5` DuckDB/manifest determinism; `AC-DF-6` quality thresholds and overrides; `AC-DF-7` atomic failure behavior; `AC-DF-8` representative-volume benchmark.

### SDD 02 — Epidemiological Metrics

| ID | Normative meaning |
|---|---|
| `FR-MT-1` | Derive `generated_at`, default/requested `as_of`, source watermarks, Brazilian epidemiological weeks, and all metric cutoffs explicitly. |
| `FR-MT-2` | Calculate case growth between consecutive complete stabilized epidemiological weeks. |
| `FR-MT-3` | Calculate required SRAG population mortality per 100,000 residents over the latest four stabilized epidemiological weeks. |
| `FR-MT-4` | Calculate supplementary hospital case fatality on the defined mature four-week cohort. |
| `FR-MT-5` | Calculate required SRAG ICU pressure from valid SRAG ICU patient-days over compatible CNES existing ICU bed-days. |
| `FR-MT-6` | Calculate supplementary proportion of SRAG hospitalizations that used ICU, never labeling it occupancy. |
| `FR-MT-7` | Select the latest official 2026 influenza target-population coverage observation published no later than `as_of`. |
| `FR-MT-8` | Produce the 30-day daily onset series ending at `as_of`, marking the latest 14 days provisional. |
| `FR-MT-9` | Produce the 12 complete calendar-month onset series before the month containing `as_of`. |
| `FR-MT-10` | Return typed metric, quality, provenance, series, and chart contracts; render both charts deterministically. |
| `NFR-MT-1` | Formulas, rounding, unavailable states, and zero-denominator states are deterministic and versioned. |
| `NFR-MT-2` | Every value and chart exposes its effective period, source, snapshot, watermark, formula version, and quality. |
| `NFR-MT-3` | Metrics query DuckDB read-only and never delegate arithmetic or chart data to the LLM. |
| `NFR-MT-4` | The documented reduced-fixture metric package completes within five seconds on the project test environment. |
| `NFR-MT-5` | Charts are faithful to structured series and include title, period, unit, source, watermark, and textual description. |

Acceptance IDs: `AC-MT-1` temporal contract; `AC-MT-2` growth; `AC-MT-3` population mortality; `AC-MT-4` supplementary fatality; `AC-MT-5` ICU pressure; `AC-MT-6` supplementary ICU use; `AC-MT-7` influenza coverage; `AC-MT-8` daily series/chart; `AC-MT-9` monthly series/chart; `AC-MT-10` quality/provenance contract; `AC-MT-11` determinism/read-only/performance.

### SDD 03 — Agentic Reporting

| ID | Normative meaning |
|---|---|
| `FR-AR-1` | Validate a Brazil-only report request, `as_of`, run ID, and allowed configuration before tool execution. |
| `FR-AR-2` | Execute a fixed LangGraph with explicit success, degradation, and terminal-failure routes. |
| `FR-AR-3` | Expose typed metrics and charts tools with no arbitrary SQL, table, column, or row-level output. |
| `FR-AR-4` | Query Google News RSS live with the fixed 14-day Portuguese/Brazil query, allowlist, freshness checks, and maximum five accepted items. |
| `FR-AR-5` | Freeze validated aggregated metrics, charts, news metadata, and evidence IDs in an immutable `EvidenceBundle`. |
| `FR-AR-6` | Call one OpenAI adapter for structured, evidence-linked commentary and record the exact configured model. |
| `FR-AR-7` | Reject unsupported IDs, numbers, citations, causality, diagnoses, recommendations, and instructions originating in news content. |
| `FR-AR-8` | Render deterministic HTML containing the required metrics, supplements, charts, context, methods, sources, watermarks, limitations, and run ID. |
| `FR-AR-9` | Apply an unambiguous failure matrix and deterministic factual fallback without letting a degraded report satisfy golden acceptance. |
| `FR-AR-10` | Own `AuditSink`, JSONL events, run-bundle creation, retry/call/token/news/time limits, and critical-event fail-closed behavior. |
| `NFR-AR-1` | LLM text cannot replace authoritative metric values, chart data, dates, or URLs. |
| `NFR-AR-2` | Every generated claim cites existing evidence IDs. |
| `NFR-AR-3` | Graph transitions and fallback text are deterministic for identical validated evidence and fake responses. |
| `NFR-AR-4` | News or OpenAI failure still yields a clearly degraded factual report when publication-critical components remain valid. |
| `NFR-AR-5` | OpenAI requests, audit events, evidence files, and reports contain aggregates only. |
| `NFR-AR-6` | Automated tests use deterministic fake OpenAI and fixed RSS; live smoke tests are manual and separately marked. |

Acceptance IDs: `AC-AR-1` request and graph route; `AC-AR-2` analytical tools; `AC-AR-3` live RSS selection; `AC-AR-4` untrusted-news handling; `AC-AR-5` evidence/privacy boundary; `AC-AR-6` structured OpenAI contract; `AC-AR-7` post-LLM validation; `AC-AR-8` complete report; `AC-AR-9` failure matrix; `AC-AR-10` audit/runtime limits; `AC-AR-11` deterministic fake execution.

### SDD 04 — Governance and Delivery

| ID | Normative meaning |
|---|---|
| `FR-GD-1` | Validate a strict golden run containing every mandatory metric, both supplements, both charts, live news, valid OpenAI claims, and a complete sanitized run bundle. |
| `FR-GD-2` | Maintain separate degradation and security suites that cannot substitute for the golden run. |
| `FR-GD-3` | Provide deterministic and live quickstarts; only the live path requires `OPENAI_API_KEY`. |
| `FR-GD-4` | Publish a complete README and sanitized reference HTML with explicit non-live/live labels. |
| `FR-GD-5` | Publish a legible conceptual architecture source and PDF showing orchestrator, tools, OpenAI, DuckDB, audit, health sources, and news. |
| `FR-GD-6` | Enforce pytest, Ruff, mypy, GitHub Actions, Gitleaks, `.gitignore`, and public-repository hygiene. |
| `FR-GD-7` | Verify a public GitHub URL from a clean unauthenticated clone and preserve release evidence. |
| `FR-GD-8` | Keep the 28-task Must plan within Days 1–5 and prohibit Stretch work until all mandatory gates are green. |
| `NFR-GD-1` | A missing critical audit event prevents publication. |
| `NFR-GD-2` | Released audit/report/sample artifacts contain no secret, restricted challenge file, row-level record, raw payload, or full article body. |
| `NFR-GD-3` | The deterministic quickstart works in a clean clone without code edits, credentials, or network-dependent OpenAI/RSS calls. |
| `NFR-GD-4` | The architecture PDF is visually legible and all required components and trust boundaries can be identified. |
| `NFR-GD-5` | CI quality and secret checks pass on the release commit. |

Acceptance IDs: `AC-GD-1` strict golden run; `AC-GD-2` degradation separation; `AC-GD-3` deterministic quickstart; `AC-GD-4` live quickstart; `AC-GD-5` README/sample; `AC-GD-6` architecture PDF; `AC-GD-7` CI/security/public hygiene; `AC-GD-8` clean-clone/public-release verification; `AC-GD-9` five-day/task-count/Stretch gate.

---

## Task 1: Establish Cross-Package Traceability and Stretch Boundaries

**Files:**

- Create: `.agent/specs/traceability.md`
- Create: `.agent/specs/stretch-backlog.md`
- Read only: `Desafio de GenAI.txt`
- Read only: `docs/superpowers/specs/2026-07-28-srag-compliance-first-sdd-remediation-design.md`

**Interfaces:**

- Consumes: the restricted challenge, the approved remediation design, and the canonical IDs above.
- Produces: the authoritative `CH-* -> FR/NFR-* -> AC-* -> T-* -> evidence` mapping used by all four packages.
- Public boundary: paraphrase obligations; never copy the challenge document or its confidentiality footer.

### Step 1: Confirm the edit baseline

Run:

```bash
rtk git status --short
```

Expected: only the pre-existing untracked `.omc/`, `.superpowers/`, and `Desafio de GenAI.txt`, plus this plan if it has not yet been committed.

### Step 2: Create the challenge inventory

Write `traceability.md` with metadata (`Status: DRAFT`, `Version: 2.0`), link the approved design, and define exactly:

| Challenge ID | Short obligation |
|---|---|
| `CH-01` | Automated report combining data, news, and explanations |
| `CH-02` | Agent-accessible database query |
| `CH-03` | Live SRAG news query |
| `CH-04` | Case-growth rate |
| `CH-05` | Mortality rate |
| `CH-06` | ICU occupancy requirement represented by the declared SRAG pressure proxy |
| `CH-07` | Vaccination rate |
| `CH-08` | Daily 30-day cases chart |
| `CH-09` | Monthly 12-month cases chart |
| `CH-10` | Real, incomplete, and invalid-data treatment |
| `CH-11` | Architecture choice |
| `CH-12` | Governance, transparency, audit, and decisions |
| `CH-13` | Guardrails |
| `CH-14` | Tool use |
| `CH-15` | Sensitive-data treatment |
| `CH-16` | Clean Code |
| `CH-17` | Public repository and documentation |
| `CH-18` | Conceptual architecture PDF |
| `CH-19` | Five-day delivery |

Add one row per ID with explicit requirement, acceptance, task, and evidence cells. Use these minimum mappings:

| CH | Requirements | Acceptance | Mandatory tasks |
|---|---|---|---|
| `CH-01` | `FR-AR-2`, `FR-AR-3`, `FR-AR-4`, `FR-AR-6`, `FR-AR-8` | `AC-AR-1`, `AC-AR-8` | `T-AR-2`, `T-AR-3`, `T-AR-4`, `T-AR-5`, `T-AR-6` |
| `CH-02` | `FR-DF-6`, `FR-AR-3` | `AC-DF-5`, `AC-AR-2` | `T-DF-4`, `T-AR-2` |
| `CH-03` | `FR-AR-4` | `AC-AR-3` | `T-AR-3` |
| `CH-04` | `FR-MT-2` | `AC-MT-2` | `T-MT-2`, `T-MT-6` |
| `CH-05` | `FR-MT-3` | `AC-MT-3` | `T-MT-2`, `T-MT-6` |
| `CH-06` | `FR-MT-5` | `AC-MT-5` | `T-MT-3`, `T-MT-6` |
| `CH-07` | `FR-MT-7` | `AC-MT-7` | `T-MT-4`, `T-MT-6` |
| `CH-08` | `FR-MT-8` | `AC-MT-8` | `T-MT-5`, `T-MT-6` |
| `CH-09` | `FR-MT-9` | `AC-MT-9` | `T-MT-5`, `T-MT-6` |
| `CH-10` | `FR-DF-1`, `FR-DF-2`, `FR-DF-3`, `FR-DF-4`, `FR-DF-7` | `AC-DF-1`, `AC-DF-2`, `AC-DF-3`, `AC-DF-6`, `AC-DF-7`, `AC-DF-8` | `T-DF-1`, `T-DF-2`, `T-DF-3`, `T-DF-5`, `T-DF-6`, `T-DF-7` |
| `CH-11` | `FR-DF-6`, `FR-AR-2`, `FR-AR-3`, `FR-AR-10` | `AC-DF-5`, `AC-AR-1`, `AC-AR-2`, `AC-AR-10` | `T-DF-4`, `T-AR-1`, `T-AR-2`, `T-AR-4`, `T-AR-6` |
| `CH-12` | `FR-DF-1`, `FR-DF-6`, `FR-DF-8`, `FR-AR-10`, `FR-GD-1` | `AC-DF-1`, `AC-DF-5`, `AC-DF-7`, `AC-AR-10`, `AC-GD-1` | `T-DF-1`, `T-DF-5`, `T-DF-7`, `T-AR-1`, `T-AR-6`, `T-GD-1` |
| `CH-13` | `FR-DF-7`, `FR-DF-8`, `FR-AR-1`, `FR-AR-5`, `FR-AR-7`, `FR-AR-9`, `FR-AR-10` | `AC-DF-6`, `AC-DF-7`, `AC-AR-5`, `AC-AR-7`, `AC-AR-9`, `AC-AR-10` | `T-DF-5`, `T-DF-6`, `T-AR-1`, `T-AR-4`, `T-AR-5`, `T-AR-7` |
| `CH-14` | `FR-AR-3`, `FR-AR-4` | `AC-AR-2`, `AC-AR-3` | `T-AR-2`, `T-AR-3` |
| `CH-15` | `FR-DF-5`, `NFR-DF-3`, `NFR-AR-5`, `NFR-GD-2` | `AC-DF-4`, `AC-AR-5`, `AC-GD-7` | `T-DF-4`, `T-AR-4`, `T-AR-7`, `T-GD-2`, `T-GD-5` |
| `CH-16` | `NFR-DF-1`, `NFR-MT-1`, `NFR-MT-3`, `NFR-AR-3`, `FR-GD-6` | `AC-DF-5`, `AC-MT-11`, `AC-AR-11`, `AC-GD-7` | `T-DF-6`, `T-MT-6`, `T-AR-7`, `T-GD-5` |
| `CH-17` | `FR-GD-3`, `FR-GD-4`, `FR-GD-6`, `FR-GD-7` | `AC-GD-3`, `AC-GD-4`, `AC-GD-5`, `AC-GD-7`, `AC-GD-8` | `T-GD-3`, `T-GD-5`, `T-GD-6` |
| `CH-18` | `FR-GD-5` | `AC-GD-6` | `T-GD-4` |
| `CH-19` | `FR-GD-8` | `AC-GD-9` | `T-DF-7`, `T-MT-7`, `T-AR-8`, `T-GD-6` |

Evidence cells must name concrete artifacts such as `report.html`, `evidence.json`, `audit.jsonl`, chart files, `manifest.json`, README sections, CI checks, the architecture PDF, or clean-clone/public-URL verification.

### Step 3: Isolate Stretch work

Create `stretch-backlog.md` with these explicitly non-MVP items:

- `ST-01`: UF filtering and regional rollups.
- `ST-02`: COVID-19 vaccination coverage.
- `ST-03`: live ingestion for health-data sources.
- `ST-04`: live/local health-source parity.
- `ST-05`: report PDF generation.
- `ST-06`: multiple LLM providers.
- `ST-07`: schema migration and rollback automation.
- `ST-08`: advanced audit querying.

State that none contributes to `CH-*` acceptance and none starts before all 28 Must tasks and the strict golden gate pass.

### Step 4: Verify the new cross-package contracts

Run:

```bash
rtk rg -n 'CH-(0[1-9]|1[0-9])' .agent/specs/traceability.md
```

Expected: all 19 IDs appear in the challenge table and all mapping rows have non-empty requirement, acceptance, task, and evidence cells.

Run:

```bash
rtk rg -n 'ST-0[1-8]' .agent/specs/stretch-backlog.md
```

Expected: eight isolated Stretch entries.

### Step 5: Commit the cross-cutting artifacts

```bash
rtk git add .agent/specs/traceability.md .agent/specs/stretch-backlog.md
rtk git commit -m "docs(sdd): add challenge traceability and stretch boundary"
```

---

## Task 2: Rewrite SDD 01 Around Verified Snapshot Contracts

**Files:**

- Modify: `.agent/specs/01-data-foundation/spec.md`
- Modify: `.agent/specs/01-data-foundation/acceptance.feature`
- Modify: `.agent/specs/01-data-foundation/tasks.md`
- Create: `.agent/specs/01-data-foundation/source-contracts.md`

**Interfaces:**

- Consumes: official SIVEP, CNES, IBGE, and PNI source metadata and pinned local files.
- Produces: minimized canonical tables, a read-only DuckDB, source/table manifests, quality results, and a verified fixture gate for SDD 02.
- Excludes: live health-source ingestion, UF output, COVID-19 coverage, raw data publication, and agent access to row-level records.

### Step 1: Replace the v1 metadata and scope

Set `Status: DRAFT`, `Version: 2.0`, and update the date. Rewrite the summary, problem, goals, non-goals, interfaces, failure policy, security, observability, capacity, compliance, acceptance table, verification plan, finalization gate, and changelog.

The spec must:

- use all `FR-DF-*` and `NFR-DF-*` meanings in the canonical inventory;
- state that SIVEP 2025 and 2026 are needed for 12 complete prior months;
- make local pinned snapshots the only MVP health-data ingestion mode;
- define the canonical field allowlist and source-to-canonical mapping as contract-owned, not implementation guesswork:
  - SIVEP: notification key, update date, symptom-onset date, hospitalization date, ICU entry/exit, evolution, evolution date, residence UF, and hospitalization UF;
  - CNES: competence, establishment UF, ICU code/category, and compatible existing-bed count;
  - population: year, geography, and official population;
  - vaccination: campaign, immunobiological, target groups, period, residence geography, numerator, denominator, published coverage, update date, and source;
- define deterministic deduplication as notification key, latest update, greatest completeness, then stable tie-break;
- distinguish field nullification from structural row quarantine using reason codes;
- prohibit clinical-value imputation;
- define quality thresholds and structural/hash/coverage overrides exactly;
- identify the thresholds as PoC guardrails, not official epidemiological standards;
- make the golden snapshot require all required metrics and series to remain available;
- make `AuditSink` an SDD 03 responsibility while SDD 01 supplies source and transformation evidence;
- include the benchmark requirement for at least 165,000 SIVEP rows without inventing a challenge SLA.

### Step 2: Create the source-contract annex

Use these official entry points:

| Source | Official entry point | Required pinned artifact |
|---|---|---|
| SIVEP-Gripe | `https://dadosabertos.saude.gov.br/dataset/srag-2019-a-2026` | Resolved 2025 and 2026 CSV resources |
| CNES | `https://cnes.datasus.gov.br/pages/downloads/arquivosBaseDados.jsp` | Latest complete compatible ICU-bed competence |
| IBGE | `https://ftp.ibge.gov.br/Estimativas_de_Populacao/Estimativas_2025/` | Applicable official Brazil population estimate |
| PNI influenza | `https://www.gov.br/saude/pt-br/composicao/seidigi/demas/campanhas-de-vacinacao/vacinacao-contra-a-influenza` | Latest official 2026 target-population coverage observation no later than `as_of` |

For each artifact, `source-contracts.md` must record:

- landing URL, resolved resource URL, and resource identifier;
- license or reuse notice;
- retrieval timestamp and source watermark;
- data-dictionary/schema version;
- byte size, SHA-256, row count, encoding, and delimiter;
- source-to-canonical fields;
- geographic and temporal semantics;
- valid, unknown, ignored, and excluded codes;
- deduplication key and ordering fields;
- failure, staleness, and replacement rules;
- fixture derivation and verification evidence.

If any value cannot be verified from the source and file, record it as `UNVERIFIED`, explain the blocking evidence, and keep SDD 01 `DRAFT`. Never substitute a guessed value.

### Step 3: Rewrite Gherkin acceptance

Use `@draft @data-foundation` at feature level, version `2.0`, and explicit lowercase tags for every linked `CH`, requirement, NFR, and AC. Write scenarios that prove:

- `AC-DF-1`: all four source families have complete contracts and a reduced real fixture before finalization;
- `AC-DF-2`: only the four pinned input families are loaded and every output identifies its exact source;
- `AC-DF-3`: ignored/unknown values, impossible dates, deterministic duplicate precedence, and structural quarantine behave correctly;
- `AC-DF-4`: identifiers, technical keys, and row-level records are absent past the analytical boundary;
- `AC-DF-5`: DuckDB is queryable read-only and identical inputs produce identical normalized hashes;
- `AC-DF-6`: `95%` publishes normally, `80%` publishes with warning, `65%` is unavailable, and missing critical columns/hash/coverage override percentages;
- `AC-DF-7`: a failed candidate cannot replace the last valid snapshot;
- `AC-DF-8`: at least 165,000 SIVEP rows complete processing and benchmark metadata is emitted.

### Step 4: Replace the backlog with seven Day-1 tasks

Use this exact inventory and expand each row into the task schema:

`- [ ] **T-DF-1 [P0, D1, CH-10, CH-12, FR-DF-1, AC-DF-1, depends: none]:** ... **Evidence:** ...`

| Task | Priority/day | Explicit links | Dependencies | Verifiable result |
|---|---|---|---|---|
| `T-DF-1` | `P0`, `D1` | `CH-10`, `CH-12`, `FR-DF-1`, `NFR-DF-2`, `AC-DF-1` | none | Four source contracts and a lawful reduced real fixture are verified or the gate remains visibly blocked. |
| `T-DF-2` | `P0`, `D1` | `CH-10`, `CH-15`, `FR-DF-2`, `FR-DF-3`, `AC-DF-2`, `AC-DF-3` | `T-DF-1` | Canonical schema, code matrix, temporal semantics, and minimization allowlist are frozen. |
| `T-DF-3` | `P0`, `D1` | `CH-10`, `FR-DF-3`, `FR-DF-4`, `AC-DF-3` | `T-DF-2` | Pinned parsers, normalization, deduplication, invalid-field handling, reason codes, and quarantine pass fixtures. |
| `T-DF-4` | `P0`, `D1` | `CH-02`, `CH-15`, `FR-DF-5`, `FR-DF-6`, `NFR-DF-3`, `AC-DF-4`, `AC-DF-5` | `T-DF-3` | Minimized tables and read-only DuckDB expose no prohibited fields. |
| `T-DF-5` | `P0`, `D1` | `CH-10`, `CH-12`, `CH-13`, `FR-DF-6`, `FR-DF-7`, `FR-DF-8`, `AC-DF-5`, `AC-DF-6`, `AC-DF-7` | `T-DF-3`, `T-DF-4` | Manifest, quality scoring, structural overrides, and atomic publication gates pass. |
| `T-DF-6` | `P1`, `D1` | `CH-10`, `CH-13`, `CH-16`, `FR-DF-2`, `FR-DF-3`, `FR-DF-4`, `FR-DF-5`, `FR-DF-6`, `FR-DF-7`, `FR-DF-8`, `NFR-DF-1`, `NFR-DF-2`, `NFR-DF-3`, `AC-DF-2`, `AC-DF-3`, `AC-DF-4`, `AC-DF-5`, `AC-DF-6`, `AC-DF-7` | `T-DF-5` | Unit, contract, integration, determinism, and privacy tests pass. |
| `T-DF-7` | `P1`, `D1` | `CH-10`, `CH-12`, `CH-16`, `CH-19`, `FR-DF-1`, `FR-DF-8`, `NFR-DF-4`, `AC-DF-1`, `AC-DF-7`, `AC-DF-8` | `T-DF-6` | Full-volume benchmark and finalization evidence are recorded; unsupported promotion remains blocked. |

### Step 5: Validate SDD 01

Run:

```bash
rtk rg -n 'Status: DRAFT|Version: 2.0|FR-DF-|NFR-DF-|AC-DF-|T-DF-' .agent/specs/01-data-foundation
```

Expected: one coherent v2 ID set, eight acceptance IDs, seven mandatory tasks, and no stale v1 semantics.

Run:

```bash
rtk rg -n 'download ao vivo|Brasil ou UF|@final|Status: FINAL' .agent/specs/01-data-foundation
```

Expected: no output.

### Step 6: Commit SDD 01

```bash
rtk git add .agent/specs/01-data-foundation/spec.md .agent/specs/01-data-foundation/acceptance.feature .agent/specs/01-data-foundation/tasks.md .agent/specs/01-data-foundation/source-contracts.md
rtk git commit -m "docs(sdd): rewrite data foundation around pinned contracts"
```

---

## Task 3: Rewrite SDD 02 With Exact Metrics and Periods

**Files:**

- Modify: `.agent/specs/02-epidemiological-metrics/spec.md`
- Modify: `.agent/specs/02-epidemiological-metrics/acceptance.feature`
- Modify: `.agent/specs/02-epidemiological-metrics/tasks.md`

**Interfaces:**

- Consumes: the frozen SDD 01 DuckDB schema, source manifests, population, vaccination observation, and quality states.
- Produces: four required metrics, two supplementary indicators, two structured series, two deterministic charts, and evidence objects for SDD 03.
- Excludes: UF, COVID-19 coverage, LLM arithmetic, observed all-cause ICU occupancy, and zero-fill outside proven coverage.

### Step 1: Rewrite the normative contract

Set `Status: DRAFT`, `Version: 2.0`, and use the canonical `FR-MT-*` and `NFR-MT-*` meanings.

Specify these formulas and periods exactly:

```text
case_growth = (reference_week_cases - previous_week_cases)
              / previous_week_cases * 100

mortality_per_100k = SRAG_deaths_in_latest_4_stabilized_epi_weeks
                     / official_population * 100_000

supplementary_fatality = SRAG_deaths
                         / hospitalizations_with_known_outcome * 100

icu_pressure = valid_SRAG_ICU_patient_days
               / compatible_CNES_existing_ICU_bed_days * 100

supplementary_icu_use = SRAG_hospitalizations_with_ICU_use
                        / SRAG_hospitalizations_with_known_ICU_status * 100

influenza_coverage = valid_influenza_doses_for_target_groups
                     / official_target_population * 100
```

The spec must also state:

- Brazilian epidemiological weeks are Sunday through Saturday.
- `generated_at` is UTC and distinct from `as_of`.
- default `as_of` is the maximum valid SIVEP symptom-onset date.
- a requested `as_of` after that watermark is rejected.
- the reference week ends at least 14 days before `as_of`.
- population mortality uses the latest four stabilized epidemiological weeks and counts SRAG-attributed deaths by evolution date.
- supplementary fatality uses four complete onset cohorts ending at least 28 days before `as_of`, excludes unknown outcomes, and never uses the simple label “mortalidade”.
- ICU pressure uses the latest complete month common to SIVEP and CNES, valid patient-day intersections, explicitly compatible existing ICU beds, and becomes unavailable above `100%`.
- supplementary ICU use is not occupancy.
- vaccination uses the latest official 2026 influenza observation published by `as_of`, its official target groups, numerator, denominator, and source.
- the daily chart has exactly 30 dates ending at `as_of`; the latest 14 dates are provisional.
- the monthly chart has exactly 12 complete calendar months before the month containing `as_of`.
- no period is forced across sources with different watermarks.
- every required result enforces the SDD 01 quality state.

Correct the old growth example so the mathematical numerator is the case delta, not the current-week count.

Define the minimum typed contracts in the spec:

```text
MetricResult:
  metric_id, label, value, state, unit, numerator, denominator,
  period_start, period_end, geography, snapshot_id, formula_version,
  quality, source_ids, limitations

SeriesResult:
  series_id, granularity, points[{period, value, state}],
  period_start, period_end, geography, snapshot_id, quality, source_ids

ChartResult:
  chart_id, series_id, path, sha256, title, period, unit,
  source_ids, watermark, alt_text
```

`value`, `numerator`, and `denominator` may be absent only when the structured
state and reason explain why the result is unavailable or non-percentual.

### Step 2: Rewrite Gherkin acceptance

Use `@draft @metrics`, version `2.0`, Brazil-only background, and explicit tags. Include scenarios proving:

- `AC-MT-1`: Sunday/Saturday week boundaries, default `as_of`, later-date rejection, 14-day stabilization, 28-day fatality maturity, and separate source periods;
- `AC-MT-2`: `100 -> 125` produces `25%`, numerator/delta `25`, plus `stable_zero`, `new_activity`, and negative-growth behavior;
- `AC-MT-3`: `20` qualifying deaths over population `1,000,000` produces `2.0/100,000`, with other-cause deaths excluded;
- `AC-MT-4`: `10` SRAG deaths over `100` known outcomes produces `10%`, with unknown outcomes counted as exclusions;
- `AC-MT-5`: `150` patient-days over `1,000` bed-days produces `15%`, exact proxy label/limitation, and `>100%` becomes unavailable;
- `AC-MT-6`: `30` known ICU uses over `100` known statuses produces a supplementary `30%` without occupancy labeling;
- `AC-MT-7`: the latest eligible 2026 influenza observation is selected and COVID-19 is absent from the MVP output;
- `AC-MT-8`: exactly 30 daily points, coverage-aware zeroes, 14 provisional points, and a faithful accessible daily chart;
- `AC-MT-9`: exactly 12 complete prior calendar months and a faithful accessible monthly chart;
- `AC-MT-10`: `95%`, `80%`, and `65%` completeness map to normal, warning, and unavailable, while structural/hash/coverage failures override;
- `AC-MT-11`: repeatability, read-only database access, no LLM calculation, and the five-second reduced-fixture check.

### Step 3: Replace the backlog with seven Day-2 tasks

| Task | Priority/day | Explicit links | Dependencies | Verifiable result |
|---|---|---|---|---|
| `T-MT-1` | `P0`, `D2` | `CH-11`, `CH-13`, `FR-MT-1`, `FR-MT-10`, `NFR-MT-2`, `AC-MT-1`, `AC-MT-10` | `T-DF-7` | Typed time, result, quality, provenance, series, and chart contracts are frozen. |
| `T-MT-2` | `P0`, `D2` | `CH-04`, `CH-05`, `FR-MT-2`, `FR-MT-3`, `AC-MT-2`, `AC-MT-3` | `T-MT-1` | Growth and population-mortality formulas and edge states pass. |
| `T-MT-3` | `P0`, `D2` | `CH-06`, `FR-MT-4`, `FR-MT-5`, `FR-MT-6`, `AC-MT-4`, `AC-MT-5`, `AC-MT-6` | `T-MT-1` | Fatality, ICU patient-days/bed-days, `>100%` rejection, and supplementary ICU use pass. |
| `T-MT-4` | `P0`, `D2` | `CH-07`, `FR-MT-7`, `AC-MT-7` | `T-DF-7`, `T-MT-1` | Latest applicable official 2026 influenza coverage is selected with complete evidence. |
| `T-MT-5` | `P0`, `D2` | `CH-08`, `CH-09`, `FR-MT-8`, `FR-MT-9`, `FR-MT-10`, `NFR-MT-5`, `AC-MT-8`, `AC-MT-9`, `AC-MT-10` | `T-MT-1` | Both exact-length series and faithful accessible charts pass coverage/provisional rules. |
| `T-MT-6` | `P1`, `D2` | `CH-04`, `CH-05`, `CH-06`, `CH-07`, `CH-08`, `CH-09`, `CH-10`, `CH-16`, `FR-MT-1`, `FR-MT-2`, `FR-MT-3`, `FR-MT-4`, `FR-MT-5`, `FR-MT-6`, `FR-MT-7`, `FR-MT-8`, `FR-MT-9`, `FR-MT-10`, `NFR-MT-1`, `NFR-MT-2`, `NFR-MT-3`, `NFR-MT-5`, `AC-MT-1`, `AC-MT-2`, `AC-MT-3`, `AC-MT-4`, `AC-MT-5`, `AC-MT-6`, `AC-MT-7`, `AC-MT-8`, `AC-MT-9`, `AC-MT-10` | `T-MT-2`, `T-MT-3`, `T-MT-4`, `T-MT-5` | Formula, period, quality, edge, provenance, privacy, and chart tests pass. |
| `T-MT-7` | `P1`, `D2` | `CH-02`, `CH-04`, `CH-05`, `CH-06`, `CH-07`, `CH-08`, `CH-09`, `CH-10`, `CH-16`, `CH-19`, `NFR-MT-3`, `NFR-MT-4`, `AC-MT-10`, `AC-MT-11` | `T-MT-6` | DuckDB integration fixture produces the complete known evidence package within the measured limit. |

### Step 4: Validate SDD 02

Run:

```bash
rtk rg -n 'Status: DRAFT|Version: 2.0|FR-MT-|NFR-MT-|AC-MT-|T-MT-' .agent/specs/02-epidemiological-metrics
```

Expected: the canonical v2 ID set and seven mandatory tasks.

Run:

```bash
rtk rg -n 'Brasil ou UF|UF inválida|duas coberturas vacinais|HTML/PDF|@final|Status: FINAL' .agent/specs/02-epidemiological-metrics
```

Expected: no output.

### Step 5: Commit SDD 02

```bash
rtk git add .agent/specs/02-epidemiological-metrics/spec.md .agent/specs/02-epidemiological-metrics/acceptance.feature .agent/specs/02-epidemiological-metrics/tasks.md
rtk git commit -m "docs(sdd): define exact SRAG metrics and periods"
```

---

## Task 4: Rewrite SDD 03 as a Controlled OpenAI/LangGraph Workflow

**Files:**

- Modify: `.agent/specs/03-agentic-reporting/spec.md`
- Modify: `.agent/specs/03-agentic-reporting/acceptance.feature`
- Modify: `.agent/specs/03-agentic-reporting/tasks.md`

**Interfaces:**

- Consumes: validated SDD 02 evidence, fixed RSS configuration, a configured OpenAI model, and an `AuditSink`.
- Produces: a validated `EvidenceBundle`, structured evidence-linked claims, a sanitized run bundle, and deterministic HTML.
- Excludes: free-form SQL, arbitrary tool loops, row-level records, LLM-created numbers/URLs, multi-provider abstraction, report PDF, and unbounded retries.

### Step 1: Rewrite the graph and tool contract

Set `Status: DRAFT`, `Version: 2.0`, and use the canonical `FR-AR-*` and `NFR-AR-*` meanings.

Specify a fixed route:

```text
validate_request
  -> select_snapshot
  -> collect_metrics
  -> render_charts
  -> search_news
  -> validate_evidence
  -> generate_commentary
  -> validate_commentary
  -> render_report
  -> finalize_run
```

Require this package boundary:

```text
srag_report/
  config.py
  domain/
  data/
  metrics/
  tools/
  agent/
  reporting/
  audit/
  cli.py
```

`domain` must not depend on infrastructure. `data` owns source contracts,
cleaning, manifests, and DuckDB; `metrics` owns deterministic formulas;
`tools` owns the narrow analytical/news interfaces; `agent` owns LangGraph,
OpenAI, and claim validation; `reporting` owns charts/HTML/factual fallback;
`audit` owns `AuditSink` and JSONL; `cli.py` owns preparation, generation, and
run inspection.

Define typed tools:

- metrics tool: accepts Brazil, `as_of`, and snapshot identifier; queries DuckDB read-only;
- charts tool: accepts validated structured series only; returns chart paths/hashes/metadata;
- news tool: queries `https://news.google.com/rss/search` at runtime with `hl=pt-BR`, `gl=BR`, `ceid=BR:pt-419`, and fixed query `("SRAG" OR "síndrome respiratória aguda grave") when:14d`.

Define the initial news allowlist as Ministério da Saúde, Fiocruz, Agência Brasil, G1, Estadão, and Folha de S.Paulo. Require title, source, final HTTP(S) URL, published time, and collected time. Reject missing dates, stale items, non-allowlisted final domains/sources, invalid schemes, and duplicates. Accept at most five items.

Treat titles/descriptions as untrusted evidence, never instructions. The 14-day news window ends at `generated_at`.

Define these minimum agent-facing contracts:

```text
ReportRequest:
  geography = "BR", as_of, snapshot_id, run_id

NewsItem:
  news_id, title, source, final_url, published_at, collected_at

EvidenceBundle:
  request, metrics, series, charts, news, sources, watermarks, quality

CommentaryClaim:
  claim_id, text, evidence_ids

AuditEvent:
  run_id, sequence, occurred_at, event_type, component, status,
  summary, evidence_ids, artifact_hashes, duration_ms
```

Tools must consume/return these domain contracts rather than arbitrary
dictionaries. Every identifier included in `CommentaryClaim.evidence_ids`
must resolve inside the immutable `EvidenceBundle`.

### Step 2: Rewrite OpenAI, evidence, audit, and failure rules

The spec must require:

- one OpenAI adapter;
- exact model name from repository configuration and in audit events;
- a repository default only after its structured-output smoke passes;
- aggregate-only `EvidenceBundle`;
- structured claims carrying existing metric/news evidence IDs;
- no OpenAI-generated URLs, authoritative numbers, chart values, or dates;
- rejection of unsupported IDs/numbers/citations, unsupported causality, diagnosis, clinical recommendation, and prompt-injection instructions;
- deterministic factual fallback after OpenAI failure or invalid claims;
- one normal call per tool;
- one retry only for transient news or OpenAI failures;
- maximum five accepted news items;
- maximum 1,200 OpenAI output tokens;
- 120-second global timeout.

Make failure routes exact:

| Failure | Route | Publish? | Golden eligible? |
|---|---|---|---|
| Invalid request or requested `as_of` after watermark | terminate before tools/OpenAI | no | no |
| Invalid snapshot/hash/schema/evidence structure | terminate before OpenAI | no | no |
| One metric unavailable with valid reason | render explicit unavailable section | yes, degraded | no |
| No valid news after allowed retry | render quantitative report with explicit limitation | yes, degraded | no |
| OpenAI unavailable after retry or claims invalid | render deterministic factual commentary | yes, degraded | no |
| Chart or renderer failure | terminate publication | no | no |
| Critical audit persistence failure | terminate before OpenAI/publication | no | no |
| Global timeout before a valid publishable bundle | terminate and audit timeout | no | no |

Assign ownership of `AuditSink` and this exact structure to SDD 03:

```text
runs/<run_id>/
  request.json
  evidence.json
  audit.jsonl
  charts/
  report.html
  manifest.json
```

Ban row-level records, technical keys, secrets, raw source payloads, full article bodies, and arbitrary objects from the bundle.

### Step 3: Rewrite Gherkin acceptance

Use `@draft @agentic-reporting`, version `2.0`, and explicit tags. Include scenarios proving:

- `AC-AR-1`: a valid Brazil request follows every fixed node and an invalid/later `as_of` terminates before tools;
- `AC-AR-2`: metrics/charts tools reject arbitrary SQL/table/column input, return no records, and run once normally;
- `AC-AR-3`: the live RSS contract applies fixed locale/query, 14-day freshness, allowlist, redirects, deduplication, maximum five, and at least one item for a golden candidate;
- `AC-AR-4`: news prompt injection cannot alter graph transitions, tools, policy, or OpenAI instructions;
- `AC-AR-5`: the evidence file and OpenAI request contain aggregates and evidence IDs only;
- `AC-AR-6`: valid structured claims reference existing IDs, log the exact configured model, and respect 1,200 output tokens;
- `AC-AR-7`: invented numbers/URLs/citations and clinical/causal overclaims are rejected and audited;
- `AC-AR-8`: HTML contains four required metrics, both supplements, both charts, current news context, methods, sources, watermarks, quality, limitations, and run ID;
- `AC-AR-9`: every row in the failure matrix has its exact terminal/degraded route and no degraded result is golden-eligible;
- `AC-AR-10`: retries, tool counts, news count, timeout, critical audit events, manifest hashes, and sanitation are enforced;
- `AC-AR-11`: fake OpenAI and fixed RSS produce byte-stable evidence/claims aside from explicitly normalized run timestamps/IDs.

### Step 4: Replace the backlog with eight Day-3 tasks

| Task | Priority/day | Explicit links | Dependencies | Verifiable result |
|---|---|---|---|---|
| `T-AR-1` | `P0`, `D3` | `CH-11`, `CH-12`, `CH-13`, `FR-AR-1`, `FR-AR-2`, `FR-AR-10`, `AC-AR-1`, `AC-AR-10` | `T-MT-7` | Typed request/state, fixed transitions, `AuditSink`, and terminal/degraded routes are implemented. |
| `T-AR-2` | `P0`, `D3` | `CH-01`, `CH-02`, `CH-11`, `CH-14`, `FR-AR-3`, `AC-AR-2` | `T-AR-1` | Metrics and chart tools enforce schemas, read-only access, call limits, and aggregate-only outputs. |
| `T-AR-3` | `P0`, `D3` | `CH-01`, `CH-03`, `CH-14`, `FR-AR-4`, `AC-AR-3`, `AC-AR-4` | `T-AR-1` | RSS query, allowlist, redirect, date, deduplication, injection, limit, and retry rules pass fixed-feed tests. |
| `T-AR-4` | `P0`, `D3` | `CH-01`, `CH-11`, `CH-13`, `CH-15`, `FR-AR-2`, `FR-AR-5`, `NFR-AR-5`, `AC-AR-1`, `AC-AR-5` | `T-AR-2`, `T-AR-3` | Graph freezes an immutable, sanitized, validated `EvidenceBundle`. |
| `T-AR-5` | `P0`, `D3` | `CH-01`, `CH-13`, `FR-AR-6`, `FR-AR-7`, `FR-AR-9`, `NFR-AR-1`, `NFR-AR-2`, `AC-AR-6`, `AC-AR-7`, `AC-AR-9` | `T-AR-4` | OpenAI adapter, structured claims, evidence validator, limits, and factual fallback pass with a fake. |
| `T-AR-6` | `P0`, `D3` | `CH-01`, `CH-11`, `CH-12`, `FR-AR-8`, `FR-AR-10`, `AC-AR-8`, `AC-AR-10` | `T-AR-5` | HTML and complete sanitized run bundle render with hashes and critical-event gates. |
| `T-AR-7` | `P1`, `D3` | `CH-13`, `CH-15`, `CH-16`, `FR-AR-7`, `FR-AR-9`, `FR-AR-10`, `NFR-AR-3`, `NFR-AR-4`, `NFR-AR-5`, `NFR-AR-6`, `AC-AR-4`, `AC-AR-5`, `AC-AR-7`, `AC-AR-9`, `AC-AR-10`, `AC-AR-11` | `T-AR-6` | Deterministic graph, injection, privacy, timeout, retry, degradation, and audit-failure tests pass. |
| `T-AR-8` | `P1`, `D3` | `CH-01`, `CH-03`, `CH-16`, `CH-19`, `FR-AR-4`, `FR-AR-6`, `NFR-AR-6`, `AC-AR-3`, `AC-AR-6`, `AC-AR-11` | `T-AR-7` | Current configured OpenAI model passes structured-output smoke and is recorded; otherwise SDD 03 remains `DRAFT`. |

### Step 5: Validate SDD 03

Run:

```bash
rtk rg -n 'Status: DRAFT|Version: 2.0|FR-AR-|NFR-AR-|AC-AR-|T-AR-' .agent/specs/03-agentic-reporting
```

Expected: the canonical v2 ID set and eight mandatory tasks.

Run:

```bash
rtk rg -n 'Brasil/UF|HTML/PDF|multi-provider|interromper ou degradar|@final|Status: FINAL' .agent/specs/03-agentic-reporting
```

Expected: no output.

### Step 6: Commit SDD 03

```bash
rtk git add .agent/specs/03-agentic-reporting/spec.md .agent/specs/03-agentic-reporting/acceptance.feature .agent/specs/03-agentic-reporting/tasks.md
rtk git commit -m "docs(sdd): constrain the OpenAI LangGraph report flow"
```

---

## Task 5: Rewrite SDD 04 Around Strict Delivery Evidence

**Files:**

- Modify: `.agent/specs/04-governance-delivery/spec.md`
- Modify: `.agent/specs/04-governance-delivery/acceptance.feature`
- Modify: `.agent/specs/04-governance-delivery/tasks.md`

**Interfaces:**

- Consumes: completed behavior and artifacts from SDDs 01–03.
- Produces: golden/degradation gates, two quickstarts, README/sample requirements, architecture PDF acceptance, CI/security checks, clean-clone evidence, and public URL evidence.
- Ownership boundary: SDD 03 creates audit/run bundles; SDD 04 verifies and releases them.

### Step 1: Rewrite the normative delivery contract

Set `Status: DRAFT`, `Version: 2.0`, and use the canonical `FR-GD-*` and `NFR-GD-*` meanings.

Define the strict golden run as requiring all of:

- four required real and available metrics: case growth, population mortality, ICU pressure proxy, and 2026 influenza coverage;
- supplementary hospital fatality and ICU-use proportion;
- complete 30-day and 12-month charts;
- at least one valid live recent news item;
- valid structured OpenAI commentary;
- sources, methods, watermarks, quality, limitations, and run ID;
- complete sanitized `request.json`, `evidence.json`, `audit.jsonl`, `charts/`, `report.html`, and `manifest.json`.

State that any missing item fails golden acceptance. Degraded reports remain useful test outputs but cannot become the reference report.

Define two quickstarts:

- deterministic: fake OpenAI, fixed RSS, no key, no live claim, no code edits;
- live: only `OPENAI_API_KEY` is user-supplied, current RSS is queried, and the configured repository model is audited.

Require README coverage for setup, architecture, sources, source acquisition, formulas, temporal semantics, quality, agent graph, tools, OpenAI, news, audit, guardrails, privacy, tests, quickstarts, limitations, sample interpretation, and public release.

Require pytest, Ruff, mypy, GitHub Actions, Gitleaks, and an ignore policy covering `.env`, raw data, complete snapshots, local run bundles, `.superpowers/`, and `Desafio de GenAI.txt`.

The architecture PDF must show health sources, Google News RSS, DuckDB, metrics/chart/news tools, LangGraph orchestrator, OpenAI, validator, renderer, `AuditSink`, output bundle, trust boundaries, and aggregate-only flow.

### Step 2: Rewrite Gherkin acceptance

Use `@draft @governance-delivery`, version `2.0`, and explicit tags. Include scenarios proving:

- `AC-GD-1`: every strict golden item exists, values are real/available, news is live/recent, claims are valid, and bundle hashes/sanitation pass;
- `AC-GD-2`: each news/OpenAI/metric/audit degradation test has the specified outcome but cannot be selected as golden;
- `AC-GD-3`: a clean deterministic quickstart needs no key/network-dependent OpenAI or RSS, edits no code, and marks output non-live;
- `AC-GD-4`: the live quickstart needs only `OPENAI_API_KEY`, uses live RSS, records the exact model, and can produce a golden candidate;
- `AC-GD-5`: README and sanitized sample cover every evaluation and reproduction topic;
- `AC-GD-6`: PDF is visually legible and contains every required component, interaction, and trust boundary;
- `AC-GD-7`: pytest, Ruff, mypy, CI, Gitleaks, staged-file inspection, ignore rules, and restricted-file exclusion pass;
- `AC-GD-8`: an unauthenticated clean clone of the public URL runs the deterministic path and exposes release/golden evidence;
- `AC-GD-9`: task counts are `7 + 7 + 8 + 6 = 28`, every task has all required metadata, Days 1–5 are covered, and Stretch is isolated.

### Step 3: Replace the backlog with six Day-4/Day-5 tasks

| Task | Priority/day | Explicit links | Dependencies | Verifiable result |
|---|---|---|---|---|
| `T-GD-1` | `P0`, `D4` | `CH-01`, `CH-03`, `CH-04`, `CH-05`, `CH-06`, `CH-07`, `CH-08`, `CH-09`, `CH-12`, `FR-GD-1`, `NFR-GD-1`, `NFR-GD-2`, `AC-GD-1` | `T-AR-8` | Strict golden fixture/live candidate and complete sanitized bundle pass every mandatory assertion. |
| `T-GD-2` | `P0`, `D4` | `CH-13`, `CH-15`, `FR-GD-2`, `NFR-GD-1`, `NFR-GD-2`, `AC-GD-2` | `T-GD-1` | Degradation, injection, privacy, audit failure, and security suites pass without being golden-eligible. |
| `T-GD-3` | `P0`, `D4` | `CH-17`, `FR-GD-3`, `FR-GD-4`, `NFR-GD-3`, `AC-GD-3`, `AC-GD-4`, `AC-GD-5` | `T-GD-1` | Both quickstarts, complete README, and sanitized labeled sample work as documented. |
| `T-GD-4` | `P0`, `D4` | `CH-18`, `FR-GD-5`, `NFR-GD-4`, `AC-GD-6` | `T-GD-3` | Architecture source and visually verified PDF contain all required components and boundaries. |
| `T-GD-5` | `P0`, `D5` | `CH-15`, `CH-16`, `CH-17`, `CH-19`, `FR-GD-6`, `FR-GD-8`, `NFR-GD-2`, `NFR-GD-5`, `AC-GD-7`, `AC-GD-9` | `T-GD-2`, `T-GD-3`, `T-GD-4` | CI, quality, Gitleaks, staged-file review, ignore policy, 28-task check, and restricted-file exclusion pass. |
| `T-GD-6` | `P0`, `D5` | `CH-03`, `CH-17`, `CH-19`, `FR-GD-7`, `FR-GD-8`, `AC-GD-4`, `AC-GD-8`, `AC-GD-9` | `T-GD-5` | Live smoke, visual review, public unauthenticated clean clone, public URL, and release evidence are verified. |

### Step 4: Validate SDD 04

Run:

```bash
rtk rg -n 'Status: DRAFT|Version: 2.0|FR-GD-|NFR-GD-|AC-GD-|T-GD-' .agent/specs/04-governance-delivery
```

Expected: the canonical v2 ID set and six mandatory tasks.

Run:

```bash
rtk rg -n 'Brasil/UF|COVID-19|relatório PDF|qualquer indisponibilidade.*aceita|@final|Status: FINAL' .agent/specs/04-governance-delivery
```

Expected: no output.

### Step 5: Commit SDD 04

```bash
rtk git add .agent/specs/04-governance-delivery/spec.md .agent/specs/04-governance-delivery/acceptance.feature .agent/specs/04-governance-delivery/tasks.md
rtk git commit -m "docs(sdd): enforce strict golden and public delivery gates"
```

---

## Task 6: Reconcile IDs, Dependencies, Status Gates, and Challenge Coverage

**Files:**

- Modify: `.agent/specs/traceability.md`
- Modify only if validation finds a defect:
  - `.agent/specs/01-data-foundation/spec.md`
  - `.agent/specs/01-data-foundation/acceptance.feature`
  - `.agent/specs/01-data-foundation/tasks.md`
  - `.agent/specs/01-data-foundation/source-contracts.md`
  - `.agent/specs/02-epidemiological-metrics/spec.md`
  - `.agent/specs/02-epidemiological-metrics/acceptance.feature`
  - `.agent/specs/02-epidemiological-metrics/tasks.md`
  - `.agent/specs/03-agentic-reporting/spec.md`
  - `.agent/specs/03-agentic-reporting/acceptance.feature`
  - `.agent/specs/03-agentic-reporting/tasks.md`
  - `.agent/specs/04-governance-delivery/spec.md`
  - `.agent/specs/04-governance-delivery/acceptance.feature`
  - `.agent/specs/04-governance-delivery/tasks.md`

**Interfaces:**

- Consumes: all rewritten SDD artifacts and the restricted challenge.
- Produces: one internally consistent, mechanically auditable documentation set with honest status gates.

### Step 1: Count the mandatory backlog

Run:

```bash
rtk rg '^- \[ \] \*\*T-' .agent/specs/*/tasks.md | rtk wc -l
```

Expected:

```text
28
```

Run:

```bash
rtk rg -c '^- \[ \] \*\*T-' .agent/specs/*/tasks.md
```

Expected per-file counts: data `7`, metrics `7`, agentic reporting `8`, governance/delivery `6`.

### Step 2: Reject stale scope and status claims

Run each check independently:

```bash
rtk rg -n '@final|Status: FINAL' .agent/specs
```

Expected: no output.

```bash
rtk rg -n '(FR|NFR|AC|T)-[A-Z]{2}-[0-9]+\.\.' .agent/specs
```

Expected: no output.

```bash
rtk rg -n 'Brasil ou UF|Brasil/UF|UF inválida|duas coberturas vacinais|relatório HTML/PDF|download ao vivo' .agent/specs/01-data-foundation .agent/specs/02-epidemiological-metrics .agent/specs/03-agentic-reporting .agent/specs/04-governance-delivery
```

Expected: no output.

### Step 3: Verify every task has complete metadata

Run:

```bash
rtk rg -n '^- \[ \] \*\*T-' .agent/specs/*/tasks.md
```

Inspect all 28 lines. Every line must contain priority (`P0` or `P1`), day (`D1`–`D5`), at least one `CH-*`, at least one `FR-*` or `NFR-*`, at least one `AC-*`, `depends:`, and `Evidence:`.

Run:

```bash
rtk rg -n '^- \[ \] \*\*T-(DF|MT|AR|GD)-[0-9]+ \[(P0|P1), D[1-5], .*CH-[0-9]{2}.*(FR|NFR)-[A-Z]{2}-[0-9]+.*AC-[A-Z]{2}-[0-9]+.*depends: .*\]:.*Evidence:' .agent/specs/*/tasks.md
```

Expected: 28 matching lines.

### Step 4: Verify referential integrity

Run this read-only check:

```bash
rtk python3 - <<'PY'
from pathlib import Path
import re

root = Path(".agent/specs")
spec_text = "\n".join(path.read_text() for path in root.glob("[0-9][0-9]-*/spec.md"))
acceptance_text = "\n".join(path.read_text() for path in root.glob("[0-9][0-9]-*/acceptance.feature"))
task_text = "\n".join(path.read_text() for path in root.glob("[0-9][0-9]-*/tasks.md"))
trace_text = (root / "traceability.md").read_text()

defined_requirements = set(re.findall(r"\b(?:N?FR)-[A-Z]{2}-\d+\b", spec_text))
defined_acceptance = {item.upper() for item in re.findall(r"@ac-([a-z]{2}-\d+)", acceptance_text)}
defined_acceptance = {"AC-" + item for item in defined_acceptance}
defined_tasks = set(re.findall(r"\*\*(T-[A-Z]{2}-\d+) ", task_text))

referenced_requirements = set(re.findall(r"\b(?:N?FR)-[A-Z]{2}-\d+\b", acceptance_text + task_text + trace_text))
referenced_acceptance = set(re.findall(r"\bAC-[A-Z]{2}-\d+\b", task_text + trace_text))
referenced_tasks = set(re.findall(r"\bT-[A-Z]{2}-\d+\b", trace_text))

problems = []
problems += [f"undefined requirement: {item}" for item in sorted(referenced_requirements - defined_requirements)]
problems += [f"unreferenced requirement: {item}" for item in sorted(defined_requirements - referenced_requirements)]
problems += [f"undefined acceptance: {item}" for item in sorted(referenced_acceptance - defined_acceptance)]
problems += [f"unreferenced acceptance: {item}" for item in sorted(defined_acceptance - referenced_acceptance)]
problems += [f"undefined task: {item}" for item in sorted(referenced_tasks - defined_tasks)]
problems += [f"unmapped task: {item}" for item in sorted(defined_tasks - referenced_tasks)]

if problems:
    raise SystemExit("\n".join(problems))

print(
    f"OK: {len(defined_requirements)} requirements, "
    f"{len(defined_acceptance)} acceptance IDs, "
    f"{len(defined_tasks)} tasks"
)
PY
```

Expected: one `OK:` line and exit code `0`.

### Step 5: Re-read against the challenge without publishing it

Compare `traceability.md` row by row with the local restricted challenge and confirm:

- database consultation is an actual typed DuckDB tool;
- news is queried live during generation;
- all four required metric names have defensible, explicit implementations;
- both exact chart periods are required;
- real-data quality, sensitive data, architecture, audit, guardrails, tools, and clean code each have acceptance evidence;
- public GitHub, complete documentation, and architecture PDF are release gates;
- the plan fits five days;
- the restricted challenge file itself is explicitly excluded from Git.

Record the review date and outcome in `traceability.md`; do not copy challenge prose.

### Step 6: Review the complete diff

Run:

```bash
rtk git diff --check
```

Expected: no whitespace errors.

Run:

```bash
rtk git diff --stat
```

Expected: the two cross-package files, one source annex, and the twelve existing SDD files only.

Run:

```bash
rtk git status --short
```

Expected: no staged or untracked restricted input; unrelated `.omc/`, `.superpowers/`, and `Desafio de GenAI.txt` remain untouched.

### Step 7: Commit final reconciliation

Stage only files changed by the reconciliation:

```bash
rtk git add .agent/specs
rtk git diff --cached --name-only
```

Expected: only SDD documentation files; never `Desafio de GenAI.txt`, `.omc/`, or `.superpowers/`.

```bash
rtk git commit -m "docs(sdd): reconcile challenge coverage and evidence gates"
```

## Execution Hand-off

After this documentation rewrite passes, do not start application implementation from the old v1 task set. Use the rewritten v2 `tasks.md` files in dependency order:

```text
D1: T-DF-1 through T-DF-7
 -> D2: T-MT-1 through T-MT-7
 -> D3: T-AR-1 through T-AR-8
 -> D4: T-GD-1 through T-GD-4
 -> D5: T-GD-5 through T-GD-6
```

No Stretch task starts before `T-GD-6` and strict golden acceptance are green.
