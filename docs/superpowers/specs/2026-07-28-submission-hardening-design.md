# Submission Hardening Design

> Status: REVIEW
> Date: 2026-07-28
> Branch: `feature/openrouter-completion`
> Scope: close the independently reproduced correctness, guardrail, governance, acceptance, official-data evidence, and public-delivery gaps before submitting the SRAG GenAI PoC.

## Goal

Make the repository a defensible submission for `Desafio de GenAI.txt` without inventing national health metrics or overstating what a local bundle can prove. The delivered system must execute deterministically without credentials, execute the documented live OpenRouter/RSS path when configured, produce evidence-grounded commentary, preserve sensitive-data boundaries, demonstrate the data pipeline with an official SIVEP/Open DATASUS extract, and be reproducible from a public unauthenticated clone.

## Product Decision: Scientifically Honest Metrics

The submission keeps the implemented metrics scientifically precise:

- `icu_pressure` is SRAG patient-days divided by compatible CNES ICU bed-days. It is a pressure proxy, not observed all-cause UTI occupancy.
- `icu_use` is the supplementary proportion of SRAG hospitalizations that used UTI. It is not occupancy.
- `influenza_coverage` is the latest eligible official influenza campaign observation, with explicit `population_scope`. A regional NE/CO/S/SE observation is never labeled national.
- Missing, temporally ineligible, legally unverified, or structurally unverified source evidence produces a typed unavailable result. It is never replaced with zero, extrapolated, or relabeled to satisfy the brief.

The README and report explain how these scientifically honest measurements address the challenge while documenting their limitations.

## Commentary Boundary

### Provider output contract

OpenRouter returns a provider DTO that is validated locally before it becomes a domain `CommentaryClaim`:

- exactly three claims;
- each claim has `text` and one or more permitted `evidence_ids`;
- text is non-empty, at most 240 characters, and contains no numeric digits;
- evidence IDs come from the exact request allowlist;
- provider output contains no internal `claim_id` field;
- deterministic internal IDs are assigned only after the complete DTO passes validation.

The same local constraints generate the remote JSON Schema, preventing wire and runtime contracts from drifting.

### Evidence exposed to the model

The LLM receives only validated aggregate metrics, series metadata, chart metadata, quality, source names, watermarks, and the permitted evidence-ID allowlist. Raw RSS titles, article URLs, source-provided instructions, and news evidence IDs are excluded from the provider prompt.

Live news remains visible in the deterministic HTML as an escaped contextual section. The model explains the computed metrics; it does not interpret or restate untrusted headlines. This preserves the challenge's live-news tool while removing the semantic prompt-injection boundary.

### Failure taxonomy

Provider-neutral sanitized codes distinguish:

- `model_provider_unavailable`: exhausted connection, rate-limit, or server failures;
- `model_output_invalid`: malformed, incomplete, schema-invalid, or ungrounded provider output;
- `commentary_rejected`: a post-generation domain guardrail rejection.

`CommentaryResult` carries an optional failure code when deterministic fallback is used. The graph, manifest, audit, and HTML consume this code without provider-specific wording. No raw exception, provider payload, prompt, or claim text is written to audit.

A commentary rejection emits a sanitized audit event containing only the rejection code, safe component name, run ID, and permitted evidence IDs.

## RSS and Network Boundary

The live RSS client uses `follow_redirects=False` and `trust_env=False`.

Every request, including the initial Google feed request, follows one shared policy:

1. allow only HTTP or HTTPS, ports 80/443, and no URL credentials;
2. require the fixed Google feed host or an approved publisher domain;
3. resolve all A/AAAA answers and reject non-global destinations before the request;
4. follow redirects manually up to the configured bound, revalidating every hop;
5. stream responses with a fixed byte ceiling before XML parsing;
6. reject DTD/entity declarations;
7. enforce bounded title, source, and URL lengths before constructing `NewsItem`;
8. retry only the documented transient transport/status failures once.

The policy applies to feed, source URL, and opaque article-link resolution. Tests use `httpx.MockTransport`; CI performs no live requests.

## Governance Boundary

### Metric scope

- Available `influenza_coverage` must have a non-empty explicit `population_scope`.
- The domain model continues to reject `population_scope` on every other metric.
- Because non-influenza scope is schema-invalid before semantic governance, the dead `metric_scoped:*` branch is removed. The plan and acceptance contract specify fail-closed `invalid_manifest_or_evidence` for that malformed evidence.

### Model identity

A golden candidate requires:

- an approved non-empty requested model;
- a non-empty, non-whitespace served model;
- served model not equal to `fallback`;
- no fallback or degradation.

### Execution evidence

The gate validates the complete typed audit stream, including:

- matching run IDs;
- contiguous sequence numbers;
- valid statuses and timestamps;
- expected node transitions in order;
- live news collection event;
- model event with requested and served identity;
- final successful publication event;
- artifact hashes matching the bundle.

The gate establishes internal bundle consistency and presence of execution evidence. Documentation must not describe it as cryptographic proof against an artifact producer who can rewrite the entire bundle. Cryptographic signing and external trust anchors remain outside this PoC.

## Official Data Reference

The release workflow must acquire an official SIVEP-Gripe/Open DATASUS resource permitted by the source contract and record:

- official landing/resource URL;
- retrieval timestamp;
- license/reuse statement available at retrieval;
- raw SHA-256, byte size, encoding, and row count;
- selected column mapping and dictionary/version;
- normalization, quarantine, and minimization counts;
- canonical snapshot/content hashes;
- report run ID and effective watermarks.

The raw source remains ignored and is never committed. Only minimized, legally permitted evidence and sanitized source metadata may enter the repository.

The official execution is not promoted as a complete golden reference when required CNES, IBGE, or PNI evidence remains unavailable or unverified. Its unavailable metrics and limitations must be visible in evidence, manifest, and HTML.

## Acceptance and Traceability

Add or update Gherkin scenarios for:

- default OpenRouter and explicit OpenAI selection;
- requested/served model recording;
- exactly-three locally validated structured claims;
- one transient retry, exhaustion fallback, and immediate non-retryable failure;
- provider-neutral fallback classification;
- raw-news exclusion from the LLM payload;
- rejected commentary audit event;
- initial-feed and article redirect rejection;
- response and field-size bounds;
- missing influenza scope rejection;
- blank served-model rejection;
- schema-level rejection of scoped non-influenza evidence;
- official SIVEP source evidence and unavailable supporting metrics;
- public unauthenticated clone and deterministic quickstart.

Replace or wrap the current traceability checker so it recognizes IDs shaped like `FR-AR-6`, `NFR-GD-2`, and `AC-MT-7`. It must fail on missing and unknown mappings and must fail when it discovers zero IDs in a non-empty SDD.

All affected SDDs, task ledgers, traceability metadata, README, architecture source/PDF, and sanitized examples use the same version/date and truthful completion status.

## Public Release

Before publication:

- confirm `Desafio de GenAI.txt`, credentials, raw data, local snapshots, run bundles, and agent state are ignored;
- run repository and generated-bundle secret scans;
- verify the branch contains no restricted challenge text;
- configure or create the intended public GitHub repository only after these checks pass;
- push the reviewed main branch;
- clone through the public unauthenticated HTTPS URL into a new temporary directory;
- run dependency installation, deterministic quickstart, tests, Ruff, mypy, and lock verification from the clean clone;
- record the public URL, commit SHA, and clone verification result in the release evidence.

## Verification Strategy

### Required regression probes

- provider returns one, four, overlength, or digit-bearing claims;
- two transient failures and one non-retryable 4xx failure;
- OpenRouter failure produces no OpenAI-specific label;
- malicious RSS instruction cannot enter the provider prompt or become a news-grounded claim;
- initial feed redirect to loopback/private/disallowed host is rejected;
- oversized feed and oversized title are rejected;
- missing influenza scope fails the gate;
- blank served model fails the gate;
- malformed scoped national metric fails at schema loading with the documented code;
- rejected commentary emits one sanitized audit event;
- mutated or out-of-order audit streams fail governance;
- traceability checker detects real domain IDs and intentional missing mappings.

### Full closeout

Run:

- focused changed-path tests;
- full pytest suite;
- Ruff;
- mypy;
- lock verification;
- all SDD traceability checks;
- representative 165,000-row benchmark;
- deterministic report smoke;
- real OpenRouter and RSS smoke using ignored credentials;
- official SIVEP execution;
- strict gate on eligible and deliberately ineligible bundles;
- repository and artifact secret scans;
- architecture PDF visual inspection;
- public anonymous clean-clone verification.

## Completion Criteria

The remediation is complete only when:

1. every reproduced code/security probe is protected by a failing-then-passing regression;
2. all local checks pass;
3. live OpenRouter/RSS execution records requested/served models, three valid claims, and no incorrect provider labels;
4. official SIVEP source metadata and a reproducible official-data execution exist without committing raw data;
5. metric limitations are explicit and no proxy is labeled as literal national occupancy/coverage;
6. traceability checks parse the repository's actual identifiers and pass non-vacuously;
7. the architecture PDF matches the implementation;
8. no secrets or restricted challenge content are published;
9. the public repository can be cloned without authentication and the deterministic quickstart passes from that clone.

If an official source, GitHub credential, or public repository permission is unavailable, all other remediation remains mandatory and the unreachable external criterion stays explicitly blocked rather than being marked complete.
