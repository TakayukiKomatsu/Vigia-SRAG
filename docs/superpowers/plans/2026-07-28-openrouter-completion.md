# OpenRouter Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `srag-report live` use OpenRouter through the installed OpenAI Python client, treat scoped influenza coverage as supplementary in strict-golden evaluation, and align verified SDD evidence without claiming the owner's pending public release.

**Architecture:** Preserve the existing `CommentaryAdapter` protocol and graph. Add `OpenRouterCommentaryAdapter` beside the OpenAI adapter, select it in the CLI, and keep provider-specific transport details out of the graph. Rebaseline governance so the complete metric package still includes influenza coverage while only the other five metrics must be nationally unscoped.

**Tech Stack:** Python 3.12, openai 2.50.0, Pydantic 2.13.4, httpx 0.28.1, LangGraph 1.2.10, pytest 8.3.4.

## Global Constraints

- Use `OpenAI(base_url="https://openrouter.ai/api/v1", api_key=...)`; add no dependency.
- Default live provider/model: `openrouter` / `openrouter/free`.
- Preserve explicit `openai` / `gpt-5.6` compatibility.
- Never log provider credentials or raw error payloads.
- Every model claim must pass `CommentaryClaims` and `validate_commentary_claims`.
- Keep `influenza_coverage` present, scoped, sourced, and labeled supplementary; never call it national.
- Public publication and unauthenticated clone evidence remain owner-owned T-GD-6 work.
- Do not mark any SDD item complete without observed evidence.

---

### Task 1: OpenRouter Commentary Adapter

**Files:**
- Modify: `src/srag_report/agent/commentary.py`
- Create: `tests/test_commentary.py`

**Interfaces:**
- Consumes: `CommentaryAdapter`, `EvidenceBundle`, `CommentaryClaims`, `CommentaryResult`, `validate_commentary_claims`.
- Produces: `DEFAULT_OPENROUTER_MODEL = "openrouter/free"` and `OpenRouterCommentaryAdapter(*, model: str = DEFAULT_OPENROUTER_MODEL, client: OpenAI | None = None, api_key: str | None = None)`.

- [ ] **Step 1: Write failing streaming contract tests**

Create fake OpenAI-client chunks and assert that the adapter calls Chat Completions with `stream=True`, a JSON-schema `response_format`, an evidence-ID allowlist, and `extra_body={"provider": {"require_parameters": True}}`. Assert that streamed content becomes a `CommentaryResult` with `requested_model="openrouter/free"`, the actual `chunk.model`, and grounded claims.

```python
adapter = OpenRouterCommentaryAdapter(client=cast(OpenAI, fake_client))
result = adapter.generate(evidence)
assert result.requested_model == "openrouter/free"
assert result.served_model == "openai/gpt-oss-20b:free"
assert not result.fallback_used
assert fake_client.kwargs["stream"] is True
```

- [ ] **Step 2: Write failing error-path tests**

Cover one retry for `openai.APIConnectionError`, `openai.RateLimitError`, and `openai.InternalServerError`; rejection after the second transient failure; no retry for malformed JSON, missing model metadata, non-`stop` finish reason, unknown evidence IDs, or non-transient provider errors.

- [ ] **Step 3: Run the new tests and observe failure**

Run: `uv run pytest tests/test_commentary.py -q`

Expected: collection/import failure because `OpenRouterCommentaryAdapter` is not defined.

- [ ] **Step 4: Implement the minimal adapter**

Use the installed SDK:

```python
self._client = client or OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
    timeout=30.0,
    max_retries=0,
)
stream = self._client.chat.completions.create(
    model=self.requested_model,
    messages=[
        {"role": "system", "content": _INSTRUCTIONS},
        {"role": "user", "content": prompt},
    ],
    stream=True,
    response_format=response_format,
    extra_body={"provider": {"require_parameters": True}},
)
```

Collect only textual deltas, require terminal `finish_reason == "stop"`, require served-model metadata, parse with `CommentaryClaims.model_validate_json`, and validate evidence references before returning. Retry only the same transient exception classes used by the OpenAI adapter.

- [ ] **Step 5: Run adapter tests**

Run: `uv run pytest tests/test_commentary.py -q`

Expected: all tests pass.

- [ ] **Step 6: Commit the adapter slice**

Commit subject: `feat(agent): add OpenRouter commentary adapter`

---

### Task 2: Supplementary Scoped PNI Governance

**Files:**
- Modify: `src/srag_report/governance.py`
- Modify: `tests/test_governance.py`

**Interfaces:**
- Consumes: `DEFAULT_OPENAI_MODEL`, `DEFAULT_OPENROUTER_MODEL`, `MetricId`.
- Produces: complete analytical metric set of six; nationally unscoped required set of five; approved requested models `{gpt-5.6, openrouter/free}`.

- [ ] **Step 1: Rewrite the golden fixture test to preserve PNI scope**

Make the live fixture use `requested_model=DEFAULT_OPENROUTER_MODEL` and a real free served-model identifier. Do not erase `influenza_coverage.population_scope`. Assert the strict gate accepts it.

```python
assert MetricId.INFLUENZA_COVERAGE in metrics
assert metrics[MetricId.INFLUENZA_COVERAGE].population_scope
assert evaluate_golden_run(run_path).eligible
```

- [ ] **Step 2: Add a failing national-metric scope test**

Mutate `case_growth.population_scope` to `{"SE"}`, update the evidence hash in the manifest, evaluate the gate, and assert `metric_scoped:case_growth` remains a failure.

- [ ] **Step 3: Run governance tests and observe failure**

Run: `uv run pytest tests/test_governance.py -q`

Expected: scoped influenza and OpenRouter remain rejected by current governance.

- [ ] **Step 4: Implement the two-set invariant**

Keep `_REQUIRED_METRICS` at six. Add `_NATIONAL_REQUIRED_METRICS = _REQUIRED_METRICS - {MetricId.INFLUENZA_COVERAGE}` and reject `population_scope` only for members of that set. Add both provider defaults to `_APPROVED_REQUESTED_MODELS`. Continue rejecting `served_model == "fallback"`, all degradation, missing metrics, unavailable values, and unavailable quality.

- [ ] **Step 5: Run governance tests**

Run: `uv run pytest tests/test_governance.py -q`

Expected: all tests pass; only influenza may be scoped.

- [ ] **Step 6: Commit the governance slice**

Commit subject: `feat(governance): treat scoped PNI as supplementary`

---

### Task 3: Live CLI Provider Selection

**Files:**
- Modify: `src/srag_report/cli.py`
- Modify: `tests/test_cli.py`
- Modify: `.env.example`

**Interfaces:**
- Consumes: `CommentaryAdapter`, `OpenAICommentaryAdapter`, `OpenRouterCommentaryAdapter`, `DEFAULT_OPENAI_MODEL`, `DEFAULT_OPENROUTER_MODEL`.
- Produces: `srag-report live --provider {openrouter,openai} [--model MODEL]`; default provider `openrouter`.

- [ ] **Step 1: Add failing provider-key tests**

Assert default live mode requires `OPEN_ROUTER_API_KEY`, explicit `--provider openai` requires `OPENAI_API_KEY`, and neither path accepts the other provider's key as a substitute.

- [ ] **Step 2: Add failing adapter-selection tests**

Publish the existing synthetic snapshot fixture, monkeypatch `_execute`, invoke `main`, and inspect the captured commentary dependency. Assert default construction is `OpenRouterCommentaryAdapter(model="openrouter/free")`; explicit OpenAI selection and `--model` override construct the expected adapter/model.

- [ ] **Step 3: Run CLI tests and observe failure**

Run: `uv run pytest tests/test_cli.py -q`

Expected: parser rejects `--provider`/`--model`, and default live mode still requires OpenAI.

- [ ] **Step 4: Implement provider selection**

Change `_execute` to accept the `CommentaryAdapter` protocol. Resolve provider, model, and credential before loading the snapshot. Add parser choices and instantiate the selected adapter inside the existing shared `httpx.Client` scope. Do not change metrics, news, audit, graph, or publication wiring.

- [ ] **Step 5: Update the environment template**

Document `OPEN_ROUTER_API_KEY=` as the default live credential and retain `OPENAI_API_KEY=` for explicit OpenAI mode. Do not add real values.

- [ ] **Step 6: Run CLI and adapter tests**

Run: `uv run pytest tests/test_cli.py tests/test_commentary.py -q`

Expected: all tests pass.

- [ ] **Step 7: Commit the CLI slice**

Commit subject: `feat(cli): select OpenRouter for live reports`

---

### Task 4: Live Verification and SDD Alignment

**Files:**
- Modify: `README.md`
- Modify: `examples/live-smoke-result.json`
- Modify: `.agent/specs/01-data-foundation/source-contracts.md`
- Modify: `.agent/specs/02-epidemiological-metrics/{spec.md,acceptance.feature,tasks.md}`
- Modify: `.agent/specs/03-agentic-reporting/{spec.md,acceptance.feature,tasks.md}`
- Modify: `.agent/specs/04-governance-delivery/{spec.md,acceptance.feature,tasks.md}`
- Modify: `.agent/specs/traceability.md`

**Interfaces:**
- Consumes: verified implementation and test results from Tasks 1–3.
- Produces: reproducible OpenRouter quickstart, sanitized smoke evidence, and SDD artifacts that distinguish completed implementation from pending public publication/source-contract evidence.

- [ ] **Step 1: Update provider and PNI contracts**

Replace provider-specific OpenAI live requirements with an approved-provider contract covering OpenRouter and OpenAI. Define influenza coverage as required supplementary scoped evidence, while the other five metrics remain nationally unscoped for golden eligibility. Keep unresolved legal/source facts explicitly `UNVERIFIED`; do not invent national PNI data.

- [ ] **Step 2: Update acceptance scenarios and traceability**

Add scenarios for default OpenRouter selection, served-model recording, grounded structured output, transient retry/fallback, scoped-influenza acceptance, and scoped-national-metric rejection. Map every changed requirement to its task and evidence.

- [ ] **Step 3: Update README and sanitized sample**

Document:

```bash
uv run --env-file .env srag-report live \
  --provider openrouter \
  --model openrouter/free \
  --snapshot data/snapshots/<snapshot>.duckdb \
  --snapshot-id <snapshot-id> \
  --as-of 2026-07-28 \
  --run-id live-20260728
```

State that public publication/clone is owner-executed and that `openrouter/free` may serve different underlying models. Record only sanitized smoke metadata in `examples/live-smoke-result.json`.

- [ ] **Step 4: Run focused and full verification**

Run:

```bash
uv run ruff check .
uv run mypy src
uv run pytest
uv lock --check
python3 "$HOME/.codex/skills/implement-from-spec/scripts/check_traceability.py" .agent/specs/01-data-foundation
python3 "$HOME/.codex/skills/implement-from-spec/scripts/check_traceability.py" .agent/specs/02-epidemiological-metrics
python3 "$HOME/.codex/skills/implement-from-spec/scripts/check_traceability.py" .agent/specs/03-agentic-reporting
python3 "$HOME/.codex/skills/implement-from-spec/scripts/check_traceability.py" .agent/specs/04-governance-delivery
```

Expected: all local checks pass.

- [ ] **Step 5: Run the real OpenRouter smoke**

Using ignored `.env`, execute the documented live path against a locally published test snapshot, then run `srag-report gate <run-path>`. Record requested and served model, fallback/degradation state, news count, claim count, token usage when available, and exact remaining gate failures. Never record the credential.

- [ ] **Step 6: Update task ledgers truthfully**

Mark OpenRouter implementation, model smoke, quickstart, governance behavior, and local verification complete only when their evidence passed. Leave public URL/unauthenticated clone and unresolved official-source/licensing evidence open. Keep affected specs `DRAFT` until their explicit external gates are satisfied.

- [ ] **Step 7: Commit closeout artifacts**

Commit subject: `docs(sdd): align OpenRouter completion evidence`

---

## Execution Order

Tasks 1 and 2 are independent and may run in parallel. Task 3 depends on Task 1. Task 4 depends on Tasks 1–3 and runs only after focused verification passes.

## Completion Boundary

Local provider integration is complete when the real OpenRouter live graph runs without fallback, all local checks pass, and SDD evidence is aligned. Full public delivery remains incomplete until the owner publishes a public remote and reproduces the unauthenticated clean clone required by T-GD-6.
