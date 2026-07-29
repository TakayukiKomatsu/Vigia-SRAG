# OpenRouter Completion Design

**Date:** 2026-07-28  
**Status:** APPROVED  
**Scope:** Permanent OpenRouter live commentary, strict-golden PNI rebaseline, verification, and SDD alignment. Public repository publication remains an explicit owner handoff.

## Decision

Use a native Python `OpenRouterCommentaryAdapter` behind the existing `CommentaryAdapter` protocol. Do not add Node, `@openrouter/sdk`, a subprocess, or a second package-management runtime. Live mode defaults to OpenRouter with `openrouter/free`, while retaining explicit OpenAI selection for compatibility.

Keep influenza vaccination coverage in the evidence bundle and report with its real `population_scope`. Treat it as supplementary scoped evidence rather than one of the nationally eligible metrics required by the strict golden gate. Never relabel regional PNI evidence as national.

## Provider Interface

`OpenRouterCommentaryAdapter` exposes:

- `requested_model: str`
- `generate(evidence: EvidenceBundle) -> CommentaryResult`

It reuses the installed `openai` Python package with `OpenAI(base_url="https://openrouter.ai/api/v1", api_key=...)` and calls `client.chat.completions.create` with streaming enabled and a strict JSON schema matching `CommentaryClaims`. No dependency is added. The prompt includes the exact evidence-ID allowlist. Returned claims pass through `CommentaryClaims` parsing and the existing `validate_commentary_claims` guard before the adapter returns.

The adapter records:

- requested router/model, normally `openrouter/free`;
- actual served model from streamed response metadata;
- `fallback_used=False` on success.

The existing graph remains responsible for deterministic fallback and degraded-state recording when generation fails.

## Configuration and CLI

Live mode gains explicit provider configuration:

- `--provider openrouter|openai`, default `openrouter`;
- `--model <model-id>`, optional, with provider-specific defaults;
- `OPEN_ROUTER_API_KEY` for OpenRouter;
- `OPENAI_API_KEY` for OpenAI.

The CLI constructs the selected adapter and otherwise preserves the current snapshot-manifest, Google News RSS, metrics, charts, audit, rendering, and atomic-publication path. The documented live quickstart uses OpenRouter and can be reproduced without changing project files.

## OpenRouter Error Handling

- One retry is allowed for connection failures, rate limits, and 5xx responses.
- Non-transient HTTP failures fail the adapter immediately.
- Incomplete streams, missing served-model metadata, malformed JSON, schema violations, and invalid evidence references fail closed.
- Provider error payloads and credentials are never copied into audit, manifest, HTML, or evidence artifacts.
- The report graph converts adapter failures to the existing deterministic commentary fallback and marks the run degraded and ineligible for golden promotion.

## Golden-Gate Rebaseline

The nationally eligible required set contains:

- case growth;
- mortality per 100,000;
- hospital CFR;
- ICU pressure;
- ICU use.

`influenza_coverage` remains required in the complete analytical package and rendered report, but it is not required to be national for strict-golden eligibility. If present with `population_scope`, that scope must remain explicit in evidence, provenance, limitations, and rendered output.

The gate continues to require:

- live execution;
- no fallback or degradation;
- an approved requested model and a non-fallback served model;
- complete artifacts with valid hashes;
- nationally eligible required metrics with available quality;
- complete daily/monthly series and charts;
- recent live news;
- valid grounded commentary;
- terminal publication audit event;
- sanitized artifacts.

Approved model configuration includes `openrouter/free`; the actual served model is recorded but may vary because it is a router.

## Verification

Tests cover:

1. OpenRouter structured streaming success and served-model capture.
2. Retry of one transient failure and fail-closed behavior afterward.
3. Invalid JSON, unknown evidence IDs, incomplete streams, and provider errors.
4. Provider-specific CLI key requirements and adapter selection.
5. OpenRouter live execution metadata in manifests and audit.
6. Golden acceptance of scoped supplementary influenza coverage.
7. Continued rejection of scoped non-influenza national metrics.
8. Continued rejection of fallback, degraded, incomplete, unhashed, stale-news, and unsafe bundles.
9. Reproduction of the live OpenRouter quickstart with a real key.
10. Full quality, security, traceability, and deterministic checks.

## SDD and Delivery

Update `spec.md`, `acceptance.feature`, `tasks.md`, source contracts, and traceability so they describe OpenRouter as the live provider and scoped influenza coverage as supplementary. Mark only requirements backed by observed evidence.

Public publication and unauthenticated clean-clone verification remain open under T-GD-6 until the owner configures a public remote. The repository must not claim that handoff passed before a URL and clean-clone evidence exist.
