# Submission Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the reproduced commentary, RSS, governance, traceability, official-data evidence, and public-delivery gaps while preserving scientifically honest UTI and vaccination labels.

**Architecture:** Keep the fixed LangGraph and existing data/report modules. Deepen their boundaries: one locally validated provider DTO feeds domain claims; one network-policy helper owns all RSS requests; governance validates reciprocal scope/model/audit invariants; a repository-native checker validates domain-shaped SDD IDs; an offline official-source command builds a minimized SIVEP/IBGE snapshot without committing raw data. Documentation and release evidence are updated only after the implementation and official-data execution pass.

**Tech Stack:** Python 3.12, Pydantic 2.13, httpx 0.28, LangGraph 1.2, DuckDB 1.5, OpenAI-compatible Chat Completions, pytest, Ruff, mypy, uv, GitHub CLI, Gitleaks.

## Global Constraints

- `icu_pressure` remains a pressure proxy; `icu_use` remains a supplementary proportion. Neither is labeled observed all-cause UTI occupancy.
- Regional influenza coverage always carries explicit `population_scope` and is never labeled national.
- Raw RSS titles, article URLs, and news evidence IDs never enter the LLM request.
- Provider/audit failures never persist raw exceptions, prompts, payloads, claim text, secrets, or clinical rows.
- CI performs no live provider, RSS, or source-download calls.
- Raw official data, snapshots, run bundles, `.env`, agent state, and `Desafio de GenAI.txt` remain ignored.
- The gate proves bundle consistency and execution evidence, not cryptographic authenticity.
- No external requirement is marked complete without reproduced evidence.

---

### Task 1: Enforce the Local Commentary Contract and Provider-Neutral Failures

**Files:**
- Modify: `src/srag_report/agent/models.py`
- Modify: `src/srag_report/agent/commentary.py`
- Modify: `src/srag_report/agent/graph.py`
- Modify: `src/srag_report/cli.py`
- Modify: `src/srag_report/reporting/html.py`
- Test: `tests/test_commentary.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_graph.py`

**Interfaces:**
- Consumes: `EvidenceBundle`, `CommentaryAdapter`, `validate_commentary_claims`, `AuditSink.emit`.
- Produces: `ProviderCommentaryClaim`, `ProviderCommentaryClaims`, `CommentaryFailureCode`, `CommentaryResult.failure_code`, `commentary_evidence_ids(evidence: EvidenceBundle) -> tuple[str, ...]`, and provider-neutral fallback/audit rendering.

- [ ] **Step 1: Write failing local-schema and prompt-minimization tests**

Add tests proving that one/four claims, text over 240 characters, ASCII, full-width, or Arabic-Indic decimal digits, unknown IDs, and provider-supplied `claim_id` fail after two bounded attempts. Assert the outbound prompt and schema exclude every `news:*` ID, RSS title, and article URL.

```python
@pytest.mark.parametrize(
    "payload",
    [
        {"claims": [{"text": "Claim válida", "evidence_ids": ["metric:case_growth"]}]},
        {"claims": [
            {"text": f"Claim {letter}", "evidence_ids": ["metric:case_growth"]}
            for letter in ("A", "B", "C", "D")
        ]},
        {"claims": [{"text": "A" * 241, "evidence_ids": ["metric:case_growth"]}] * 3},
        {"claims": [{"text": "Crescimento 50", "evidence_ids": ["metric:case_growth"]}] * 3},
        {"claims": [{
            "claim_id": "provider-id",
            "text": "Claim válida",
            "evidence_ids": ["metric:case_growth"],
        }] * 3},
    ],
)
def test_openrouter_rejects_provider_output_outside_local_schema(payload: object) -> None:
    completions = FakeCompletions(
        _stream(json.dumps(payload)),
        _stream(json.dumps(payload)),
    )
    with pytest.raises((ValueError, ValidationError)):
        _adapter(completions).generate(_evidence())
    assert len(completions.calls) == 2
```

- [ ] **Step 2: Write failing failure-taxonomy and real HTTP-attempt tests**

Cover two transient failures, one non-retryable `BadRequestError`, malformed output, OpenRouter graph fallback, and post-generation rejection. Assert call counts, `failure_code`, provider-neutral manifest reason/HTML, and one sanitized audit rejection event. In addition to fake-completion unit tests, use the real OpenAI SDK client with `httpx.MockTransport` to assert exactly two HTTP requests for transient exhaustion and one for a non-retryable 4xx.

```python
def test_openrouter_does_not_retry_bad_request() -> None:
    error = openai.BadRequestError(
        "bad request",
        response=httpx.Response(
            400,
            request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions"),
        ),
        body=None,
    )
    completions = FakeCompletions(error, _stream(_claims()))
    with pytest.raises(openai.BadRequestError):
        _adapter(completions).generate(_evidence())
    assert len(completions.calls) == 1
```

- [ ] **Step 3: Run focused tests and confirm red**

Run: `uv run pytest tests/test_commentary.py tests/test_graph.py -q`

Expected: failures for missing local constraints, failure code, sanitized audit event, and provider-neutral labels.

- [ ] **Step 4: Add provider DTOs and failure taxonomy**

In `agent/models.py`, add constrained models and failure code:

```python
class CommentaryFailureCode(StrEnum):
    MODEL_PROVIDER_UNAVAILABLE = "model_provider_unavailable"
    MODEL_OUTPUT_INVALID = "model_output_invalid"
    COMMENTARY_REJECTED = "commentary_rejected"

class ProviderCommentaryClaim(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    text: str = Field(min_length=1, max_length=240, pattern=r"^[^\p{Nd}]*$")
    evidence_ids: tuple[str, ...] = Field(min_length=1)

class ProviderCommentaryClaims(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    claims: tuple[ProviderCommentaryClaim, ProviderCommentaryClaim, ProviderCommentaryClaim]
```

Add `failure_code: CommentaryFailureCode | None = None` to `CommentaryResult` and enforce `fallback_used == (failure_code is not None)` without provider exceptions. A successful fake adapter is `fallback_used=False, failure_code=None`; every deterministic fallback carries one of the three failure codes. Add model tests rejecting both inconsistent combinations.

- [ ] **Step 5: Make local DTOs the wire-schema source**

Build OpenRouter JSON Schema from `ProviderCommentaryClaims.model_json_schema()`, replacing only the `evidence_ids.items` schema with the exact enum allowlist. Parse provider JSON into `ProviderCommentaryClaims`, then locally validate every returned evidence ID against the exact request allowlist before constructing any domain claim. Only after the complete DTO and allowlist validation pass may deterministic internal IDs be assigned:

```python
def _provider_claims_to_domain(
    payload: ProviderCommentaryClaims,
    *,
    allowed_evidence_ids: frozenset[str],
) -> CommentaryClaims:
    if any(
        evidence_id not in allowed_evidence_ids
        for claim in payload.claims
        for evidence_id in claim.evidence_ids
    ):
        raise ValueError("provider returned unknown evidence ID")
    return CommentaryClaims(
        claims=tuple(
            CommentaryClaim(
                claim_id=f"openrouter-claim-{index}",
                text=claim.text,
                evidence_ids=claim.evidence_ids,
            )
            for index, claim in enumerate(payload.claims, start=1)
        )
    )
```

Use `commentary_evidence_ids()` to allow only metric, series, and chart IDs. Build a minimized provider payload without `news`. The unknown-ID regression must prove no domain claim is constructed before rejection.

- [ ] **Step 6: Emit provider-neutral failures and audit rejection codes**

Construct both OpenRouter and explicit OpenAI SDK clients with `max_retries=0`; the adapter alone owns the two-attempt policy. Wrap adapter retry exhaustion in provider-neutral typed exceptions or map caught exception classes at the adapter boundary. `generate_or_fallback` must set the matching failure code. `graph.generate_commentary` propagates `commentary.failure_code.value` into `degraded_reasons`. Before deterministic fallback, `validate_commentary` emits exactly one sanitized `guardrail` audit event whose envelope has run ID, sequence, timestamp, safe component, `commentary_rejected`, and the request's permitted metric/series/chart evidence IDs. Tests assert the event contains no claim text, prompt, provider payload, exception text, URLs, or `news:*` IDs. HTML says `falha/rejeição do provedor de comentários`.

- [ ] **Step 7: Run focused tests and verify green**

Run: `uv run pytest tests/test_commentary.py tests/test_evidence.py tests/test_graph.py tests/test_cli.py -q`

Expected: all pass, including exact three-claim local validation and provider-neutral fallback.

- [ ] **Step 8: Commit commentary slice**

```bash
git add src/srag_report/agent/models.py src/srag_report/agent/commentary.py src/srag_report/agent/graph.py src/srag_report/reporting/html.py src/srag_report/cli.py tests/test_commentary.py tests/test_graph.py tests/test_cli.py
git commit -m "fix(agent): harden commentary provider boundary"
```

---

### Task 2: Close RSS Redirect, DNS, XML, and Resource Boundaries

**Files:**
- Modify: `src/srag_report/agent/models.py`
- Modify: `src/srag_report/tools/news.py`
- Modify: `src/srag_report/cli.py`
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Test: `tests/test_news.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: fixed `GOOGLE_NEWS_RSS`, publisher allowlist, `httpx.Client`, `httpcore.NetworkBackend`, and `defusedxml`.
- Produces: validated/pinned hostname addresses, `PinnedNetworkBackend`, `PinnedHTTPTransport`, `_get_bounded(client, url, *, params=None) -> bytes`, bounded `NewsItem` fields, hardened XML parsing, and a no-auto-redirect/no-environment-proxy live client.

- [ ] **Step 1: Write failing policy tests for every RSS request path**

Add parameterized tests for the initial feed, source URL, and opaque article-link resolution. For each path cover non-HTTP(S) scheme, URL credentials, disallowed host, unexpected port, an empty DNS result, any loopback/private/link-local DNS answer, redirect to a forbidden destination, and excess redirects. Add one documented transient failure followed by success, two transient failures, and an immediate non-retryable 4xx. Add a DNS-rebinding regression where preflight resolution is global but a second system resolution would be loopback; assert the transport connects only to the pinned global IP and preserves the original TLS hostname.

```python
def test_news_tool_rejects_initial_feed_redirect_to_loopback() -> None:
    requested: list[str] = []
    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return httpx.Response(
            302,
            headers={"location": "http://127.0.0.1/private-feed"},
            request=request,
        )
    with httpx.Client(transport=httpx.MockTransport(handler), trust_env=False) as client:
        with pytest.raises(ValueError, match="non-global"):
            GoogleNewsRssTool(client).collect(generated_at=_NOW)
    assert not any("127.0.0.1" in url for url in requested)
```

- [ ] **Step 2: Write failing size/XML/field-bound tests for every path**

Test feed and article bodies over 1 MiB; UTF-8 and UTF-16 `<!DOCTYPE>`/`<!ENTITY>` payloads; title over 300 characters; source over 100 characters; and URL over 2,048 characters. Every case must reject before `NewsItem` reaches evidence. Hardened parser prohibitions apply before application parsing; field bounds apply before construction.

- [ ] **Step 3: Run RSS tests and confirm red**

Run: `uv run pytest tests/test_news.py tests/test_cli.py -q`

Expected: redirect, DNS, size, XML, and field-bound tests fail.

- [ ] **Step 4: Implement one pinned bounded request policy**

Use constants:

```python
_MAX_RESPONSE_BYTES = 1_048_576
_MAX_TITLE_LENGTH = 300
_MAX_SOURCE_LENGTH = 100
_MAX_URL_LENGTH = 2_048
```

Resolve each hostname once, reject an empty result or any non-global address, select a validated address, and register it in a request-scoped pin map. Implement `PinnedNetworkBackend` over httpcore's `NetworkBackend`: its `connect_tcp(original_host, ...)` delegates to `SyncBackend.connect_tcp(pinned_ip, ...)`, while the enclosing httpcore connection retains the original origin so `NetworkStream.start_tls(..., server_hostname=original_host)` preserves SNI and certificate hostname validation. Implement an `httpx.BaseTransport` backed by `httpcore.ConnectionPool(network_backend=pinned_backend)` rather than letting HTTPX resolve again. Add direct dependencies `httpcore==1.0.9` and `defusedxml==0.7.1`.

The initial feed, source URL, and opaque article-link path all call `_get_bounded()`. Stream with automatic redirects disabled and stop beyond `_MAX_RESPONSE_BYTES`. Parse only with `defusedxml.ElementTree` configured to forbid DTDs, entities, and external references. Permit exactly one retry for `httpx.ConnectError`, `ConnectTimeout`, `ReadTimeout`, `RemoteProtocolError`, and status 408/425/429/500/502/503/504; exhaust after the second failure and never retry any other 4xx or validation error.

- [ ] **Step 5: Bound NewsItem fields and configure the live client**

Use Pydantic `Field(min_length=1, max_length=...)` on title/source/final_url. Construct the CLI client with:

```python
httpx.Client(
    transport=PinnedHTTPTransport(),
    timeout=httpx.Timeout(15.0),
    follow_redirects=False,
    max_redirects=0,
    trust_env=False,
)
```

- [ ] **Step 6: Run focused tests and verify green**

Run: `uv run pytest tests/test_news.py tests/test_cli.py tests/test_graph.py -q`

Expected: all pass; no mocked request reaches a private destination.

- [ ] **Step 7: Commit RSS slice**

```bash
git add src/srag_report/agent/models.py src/srag_report/tools/news.py src/srag_report/cli.py pyproject.toml uv.lock tests/test_news.py tests/test_cli.py
git commit -m "fix(news): enforce bounded RSS network policy"
```

---

### Task 3: Repair Golden Scope, Model, and Audit Invariants

**Files:**
- Modify: `src/srag_report/governance.py`
- Modify: `src/srag_report/audit/sink.py` only if a shared typed event loader is required
- Modify: `src/srag_report/metrics/models.py`
- Test: `tests/test_governance.py`
- Test: `tests/test_security.py`

**Interfaces:**
- Consumes: `RunManifest`, `EvidenceBundle`, `AuditEvent`, `NODE_ORDER`, `MetricId`.
- Produces: reciprocal influenza scope validation, nonblank model validation, typed complete audit validation, and schema-level non-influenza scope rejection.

- [ ] **Step 1: Write failing reciprocal-scope and model tests**

Create promoted live candidates with available influenza coverage missing scope, unavailable influenza coverage without scope, empty/unapproved requested model, empty/whitespace served model, padded/case-varied served model `fallback`, `fallback_used=True`, and non-empty degradation reasons. Pass malformed serialized scoped case-growth evidence through the real gate loader rather than constructing an invalid `MetricResult`. Expected outcomes:

```python
assert evaluate_golden_run(available_missing_scope).failures == ("influenza_scope_missing",)
assert "influenza_scope_missing" not in evaluate_golden_run(unavailable_without_scope).failures
assert "unapproved_or_unserved_model" in evaluate_golden_run(blank_model).failures
assert "degraded_or_fallback" in evaluate_golden_run(fallback_candidate).failures
assert evaluate_golden_run(serialized_scoped_case).failures == (
    "invalid_manifest_or_evidence",
)
```

- [ ] **Step 2: Write failing typed-audit tests**

Mutate run ID, sequence, status, timestamp order, node order, model event, news event, and final publication event. Update the artifact hash after each mutation so each test proves semantic audit rejection rather than hash rejection.

- [ ] **Step 3: Run governance tests and confirm red**

Run: `uv run pytest tests/test_governance.py tests/test_security.py -q`

Expected: reciprocal scope, model identity, fallback/degradation, malformed evidence loading, and typed-audit cases fail.

- [ ] **Step 4: Implement reciprocal scope and complete model checks**

In the metric loop:

```python
if (
    metric_id is MetricId.INFLUENZA_COVERAGE
    and metric.state is not MetricState.UNAVAILABLE
    and not metric.population_scope
):
    failures.append("influenza_scope_missing")
```

Normalize once with `served_model = manifest.served_model.strip()` and reject an empty or unapproved requested model, `not served_model`, `served_model.casefold() == "fallback"`, `fallback_used`, and non-empty `degraded_reasons`. Add padded and case-varied fallback regressions. Remove `_NATIONAL_REQUIRED_METRICS` and the unreachable `metric_scoped:*` branch; retain `MetricResult._check_population_scope` as the authoritative non-influenza invariant. The malformed serialized regression must fail as `invalid_manifest_or_evidence` at the real evidence-loading/gate entry point.

- [ ] **Step 5: Validate the complete audit stream**

Parse every JSONL line with `AuditEvent.model_validate_json`. Require matching run ID, contiguous sequence `1..N`, nondecreasing UTC timestamps, and exactly one ordered start followed by exactly one successful terminal event for every `NODE_ORDER` component. Require one live news event, exactly one model event whose requested/served identities equal the manifest, and a final successful publication event. Reject identity mismatches, duplicates, failed/skipped terminal events, and missing events with stable failure codes such as `audit_invalid`, `audit_sequence_invalid`, `audit_node_order_invalid`, `live_news_event_absent`, and `model_event_absent`.

- [ ] **Step 6: Run focused tests and verify green**

Run: `uv run pytest tests/test_governance.py tests/test_security.py tests/test_graph.py -q`

Expected: all pass and intentionally mutated audits fail closed.

- [ ] **Step 7: Commit governance slice**

```bash
git add src/srag_report/governance.py src/srag_report/audit/sink.py src/srag_report/metrics/models.py tests/test_governance.py tests/test_security.py
git commit -m "fix(governance): enforce reciprocal golden invariants"
```

---

### Task 4: Add Non-Vacuous Domain Traceability and Align the SDD

**Files:**
- Create: `scripts/check_traceability.py`
- Create: `tests/test_traceability.py`
- Create: `scripts/check_release_metadata.py`
- Create: `scripts/check_release_contents.py`
- Create: `tests/test_release_checks.py`
- Create: `scripts/check_external_release.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `.agent/specs/02-epidemiological-metrics/{spec.md,acceptance.feature,tasks.md}`
- Modify: `.agent/specs/03-agentic-reporting/{spec.md,acceptance.feature,tasks.md}`
- Modify: `.agent/specs/04-governance-delivery/{spec.md,acceptance.feature,tasks.md}`
- Modify: `.agent/specs/traceability.md`
- Modify: `docs/superpowers/plans/2026-07-28-openrouter-completion.md`

**Interfaces:**
- Consumes: IDs shaped as `FR-AR-6`, `NFR-GD-2`, `AC-MT-7`, task references, release version `2.2`, release date `2026-07-29`, and Git reachable objects.
- Produces: `collect_ids`, `check_spec_dir`, CLI exit status, complete Gherkin mappings, aligned release metadata, current/history restricted-content checks, and an external GitHub-release status check bound to an immutable SHA.

- [ ] **Step 1: Write failing checker tests**

Cover actual domain IDs, missing acceptance FR, missing task FR, unknown acceptance AC, and zero discovered IDs. The empty-ID case must fail rather than print OK.

```python
def test_checker_understands_domain_qualified_ids(tmp_path: Path) -> None:
    spec_dir = _spec(tmp_path, fr="FR-AR-6", ac="AC-AR-6", task="FR-AR-6")
    assert check_spec_dir(spec_dir) == ()

def test_checker_rejects_vacuous_success(tmp_path: Path) -> None:
    spec_dir = _spec(tmp_path, fr="", ac="", task="")
    assert "no_requirement_ids_discovered" in check_spec_dir(spec_dir)
```

- [ ] **Step 2: Run checker tests and confirm red**

Run: `uv run pytest tests/test_traceability.py -q`

Expected: import failure because the repository-native checker does not exist.

- [ ] **Step 3: Implement the repository-native checker**

Use patterns:

```python
FR_RE = re.compile(r"\b(?:NFR|FR)-[A-Z]{2}-\d+\b", re.IGNORECASE)
AC_RE = re.compile(r"\bAC-[A-Z]{2}-\d+\b", re.IGNORECASE)
TAG_FR_RE = re.compile(r"@(?:nfr|fr)-[a-z]{2}-\d+\b", re.IGNORECASE)
TAG_AC_RE = re.compile(r"@ac-[a-z]{2}-\d+\b", re.IGNORECASE)
```

Return deterministic issue codes and print discovered IDs. Wire CI to invoke all four SDD directories after pytest. Add `check_release_metadata.py` to require version `2.2`, date `2026-07-29`, and truthful status markers across every affected SDD, task ledger, traceability file, README, architecture source, and sanitized example. Add `check_release_contents.py` with current-tree and `--history` modes; inspect tracked paths and every reachable Git blob for restricted challenge content, credentials, raw data, snapshots, run bundles, and agent state. Add `check_external_release.py` to query/validate that GitHub release `v2.2`, its evidence asset, and its passing anonymous-clone status all target the supplied immutable SHA; unit-test its pure validation against fixture API payloads.

- [ ] **Step 4: Add every missing acceptance scenario and remove contradictions**

Add explicit scenarios for default OpenRouter; explicit OpenAI; requested and served model recording; one transient retry; transient exhaustion; immediate non-retryable failure; local exactly-three contract; raw-news exclusion; provider-neutral fallback; commentary rejection audit; initial-feed redirect rejection; article redirect rejection; response and field-size bounds; missing available-influenza scope while unavailable influenza remains valid; blank served model; schema-invalid national scope; official SIVEP evidence with unavailable CNES/PNI metrics; and public unauthenticated clone plus deterministic quickstart. Replace the non-goal with `provedores além de OpenRouter padrão e OpenAI explícito`. Map each scenario to a requirement, task, and executable test or release-evidence command.

- [ ] **Step 5: Align plan, tasks, and release metadata**

Change the scoped non-influenza expectation to `invalid_manifest_or_evidence`; set every affected artifact to version `2.2` and date `2026-07-29`; map every new scenario to requirement/task/evidence; and keep official/public external criteria open until executed. Add fixture tests proving both release checkers reject missing, stale, and forbidden data.

- [ ] **Step 6: Run non-vacuous traceability and tests**

Run:

```bash
uv run pytest tests/test_traceability.py tests/test_release_checks.py -q
uv run python scripts/check_traceability.py .agent/specs/01-data-foundation
uv run python scripts/check_traceability.py .agent/specs/02-epidemiological-metrics
uv run python scripts/check_traceability.py .agent/specs/03-agentic-reporting
uv run python scripts/check_traceability.py .agent/specs/04-governance-delivery
```

Expected: fixture tests and every traceability directory pass with non-empty IDs. Do not run repository-wide release metadata/content checks yet: README, architecture, and official evidence are aligned in Tasks 5–6, then validated before any release.

- [ ] **Step 7: Commit traceability slice**

```bash
git add scripts/check_traceability.py scripts/check_release_metadata.py scripts/check_release_contents.py scripts/check_external_release.py tests/test_traceability.py tests/test_release_checks.py .github/workflows/ci.yml .agent/specs docs/superpowers/plans/2026-07-28-openrouter-completion.md
git commit -m "docs(sdd): make hardening traceability executable"
```

---

### Task 5: Build and Exercise an Official SIVEP/IBGE Snapshot

**Files:**
- Create: `scripts/prepare_official_snapshot.py`
- Create: `scripts/acquire_official_sources.py`
- Create: `tests/test_prepare_official_snapshot.py`
- Modify: `.gitignore` if the output paths are not already covered
- Modify: `.agent/specs/01-data-foundation/source-contracts.md`
- Create: `examples/official-source-run.json`

**Interfaces:**
- Consumes: required fixed official SIVEP 2026 CSV URL/hash/size/rows; optional independently attested IBGE ODS URL/hash/size; `normalize_sivep_csv_to_jsonl`, `normalize_ibge_ods`, `materialize_snapshot`, `build_snapshot_manifest`, and `publish_snapshot`.
- Produces: an offline CLI that always accepts verified SIVEP, optionally accepts verified IBGE, publishes a minimized snapshot with absent supporting-source tables, marks dependent metrics unavailable, prevents golden promotion, and writes sanitized source/run evidence in `examples/official-source-run.json`.

- [ ] **Step 1: Write failing acquisition, provenance, and snapshot tests**

Use tiny local HTTP/CSV/ODS fixtures and assert independent per-source download failure, hash/size/row mismatch, actual retrieval timestamp capture, landing/resource URL distinction, license/reuse evidence, encoding, selected mappings/dictionary version, successful SIVEP-only and SIVEP+IBGE preparation, streaming normalization, quarantine/minimization counts, raw paths absent from committed JSON, empty absent-source tables, unavailable dependent metrics, golden ineligibility, effective watermarks, and exact source/snapshot metadata.

- [ ] **Step 2: Run official-snapshot tests and confirm red**

Run: `uv run pytest tests/test_prepare_official_snapshot.py -q`

Expected: import failure because the preparation command does not exist.

- [ ] **Step 3: Implement the offline preparation command**

The preparation command is explicit and network-free; IBGE is optional:

```text
--acquisition data/raw/acquisition.json
--sivep-csv data/raw/sivep/INFLUD26-27-07-2026.csv
--ibge-ods data/raw/ibge/POP2025_20260113.ods
--output-root data/snapshots
--snapshot-id official-20260727
--as-of 2026-07-26
```

When `--ibge-ods` is omitted or its sidecar status is unavailable, preparation continues with an empty IBGE table and typed-unavailable population-denominator metrics.

The command verifies:

```python
SIVEP_SHA256 = "5b1de50c4ca58b1c7068d61f58b42772d1634a06917d41443443fff1fdd359fb"
SIVEP_SIZE = 198_233_708
SIVEP_ROWS = 177_445
IBGE_SHA256 = "33dc6f79def9522e282cd69b87a9ce75327a81239d6060d9c8f9f5a49bd2a1b5"
IBGE_SIZE = 212_846
```

Normalize required SIVEP to ignored JSONL and stream it into `SivepCanonicalRow.model_validate_json`. If independently verified IBGE is present, normalize it; otherwise materialize an empty IBGE table. Materialize empty CNES/PNI tables, publish with `QualityState.WARNING`, mark every absent-source-dependent metric unavailable, and make the bundle explicitly ineligible for golden promotion without blocking the official SIVEP execution itself.

- [ ] **Step 4: Run preparation tests and verify green**

Run: `uv run pytest tests/test_prepare_official_snapshot.py tests/data -q`

Expected: all pass without network.

- [ ] **Step 5: Acquire and attest fixed SIVEP plus optional IBGE independently**

Run `scripts/acquire_official_sources.py --output-root data/raw`. It independently downloads and verifies fixed dated SIVEP and optional IBGE resources, then atomically writes ignored `data/raw/acquisition.json` with a per-source status. Each available source records actual retrieval time, official landing/resource URLs, license/reuse statement and evidence URL, raw hash/size/encoding/row count, and selected dictionary/version. Expected constants never change to fit a new artifact. Missing/mismatched IBGE is recorded as unavailable and preparation continues. Only missing/mismatched SIVEP or unverifiable SIVEP legal/source evidence writes `runs/official-source-blocked.json` and blocks the official-execution criterion.

- [ ] **Step 6: Run deterministic official preparation separately from live provider evidence**

When SIVEP acquisition passes, run the network-free preparation command, deterministic report, and gate. Case growth uses official SIVEP; mortality per 100k is available only when IBGE passed and otherwise is typed unavailable. UTI pressure and vaccination remain unavailable when CNES/PNI are absent. The bundle is never golden while required supporting metrics are unavailable. Then attempt live OpenRouter/RSS independently; missing credentials block only live-provider evidence.

- [ ] **Step 7: Record complete sanitized official SIVEP evidence**

Whenever verified SIVEP preparation/report passed, write `examples/official-source-run.json` even if IBGE/CNES/PNI are unavailable. Record each source status; acquisition metadata for available sources; normalization/quarantine/deduplication/minimization counts; canonical snapshot/content hashes; effective watermarks; report run IDs; metric states; golden ineligibility; model identities when live succeeded; fallback/live status; and explicit limitations. Exclude raw rows, absolute paths, credentials, and restricted text. If SIVEP itself is blocked, do not create/update the tracked run-evidence file.

- [ ] **Step 8: Commit official-source tooling and sanitized evidence**

```bash
git add scripts/acquire_official_sources.py scripts/prepare_official_snapshot.py tests/test_prepare_official_snapshot.py .gitignore .agent/specs/01-data-foundation/source-contracts.md
test ! -f examples/official-source-run.json || git add examples/official-source-run.json
git commit -m "feat(data): verify official SIVEP reference execution"
```

---

### Task 6: Align README, Architecture, Examples, and Release Claims

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.html`
- Modify: `docs/architecture.pdf`
- Modify: `examples/live-smoke-result.json`
- Modify: `.agent/specs/01-data-foundation/tasks.md`
- Modify: `.agent/specs/02-epidemiological-metrics/tasks.md`
- Modify: `.agent/specs/03-agentic-reporting/tasks.md`
- Modify: `.agent/specs/04-governance-delivery/tasks.md`

**Interfaces:**
- Consumes: verified behavior/evidence from Tasks 1–5.
- Produces: reproducible operator documentation, scientifically honest metric labels, updated architecture PDF, and truthful task ledgers.

- [ ] **Step 1: Update README operational contract**

Document `uv run --env-file .env`, OpenRouter routing alias variability, requested/served model recording, owner-executed publication/clone verification, raw-news exclusion, provider-neutral fallback codes, RSS network bounds, official-data preparation, and explicit UTI/vaccination limitations.

- [ ] **Step 2: Update architecture source**

Show the minimized commentary evidence view, provider DTO validation, bounded RSS policy, guardrail audit event, typed governance audit validation, official source preparation, and consistency-not-authenticity gate boundary.

- [ ] **Step 3: Render and inspect the one-page PDF**

Render `docs/architecture.html` to `docs/architecture.pdf` with the established browser/PDF workflow. Verify one A4 landscape page, no clipping, readable text, and every required component: orchestrator, tools, LLM, DuckDB, RSS, validator, audit sink, bundle, flows, limits.

- [ ] **Step 4: Update sanitized evidence and task ledgers**

Record only freshly reproduced results. Do not check public clone, official source, live provider, or gate items unless their corresponding command passed. Keep external failures explicit. Set version `2.2`, date `2026-07-29`, and truthful status consistently in README, architecture source, SDDs, task ledgers, traceability metadata, and sanitized examples.

- [ ] **Step 5: Run documentation, metadata, and privacy checks**

Run `scripts/check_release_metadata.py` and `scripts/check_release_contents.py`. They must reject restricted challenge text, raw rows, credentials, absolute local paths, obsolete OpenAI-only labels, literal national occupancy/coverage claims, and stale or inconsistent version/date/status markers across every affected artifact.

- [ ] **Step 6: Commit documentation slice**

```bash
git add README.md docs/architecture.html docs/architecture.pdf examples .agent/specs
git commit -m "docs: align hardened submission evidence"
```

---

### Task 7: Full Verification, Independent Review, and Public Release

**Files:**
- Produce (ignored, after final push): `runs/release-verification.json`
- Define tracked `T-GD-6` as an externally evaluated state resolved by `scripts/check_external_release.py`, not as a mutable post-push checkbox

**Interfaces:**
- Consumes: all committed implementation/docs, ignored `.env`, official snapshot, GitHub CLI authentication.
- Produces: final verification evidence bound to one immutable public SHA, public `techtest2` repository, unauthenticated clone result, and truthful release status.

- [ ] **Step 1: Run focused behavioral probes**

Re-run every original `/tmp/retest_openrouter_findings.py` and `/tmp/retest_security_findings.py` behavior as permanent tests. Expected: missing scope, blank model, malformed provider output, private redirect, oversized RSS, prompt injection, and missing audit event are all rejected.

- [ ] **Step 2: Run full local verification**

```bash
uv run ruff check .
uv run mypy src
uv run pytest
uv lock --check
uv run python scripts/check_traceability.py .agent/specs/01-data-foundation
uv run python scripts/check_traceability.py .agent/specs/02-epidemiological-metrics
uv run python scripts/check_traceability.py .agent/specs/03-agentic-reporting
uv run python scripts/check_traceability.py .agent/specs/04-governance-delivery
uv run python scripts/check_release_metadata.py
uv run python scripts/check_release_contents.py
uv run python scripts/check_release_contents.py --history
gitleaks detect --source . --redact --exit-code 1
gitleaks detect --no-git --source . --redact --exit-code 1
```

Expected: all pass; traceability prints non-empty IDs.

- [ ] **Step 3: Run the representative benchmark**

Execute the existing ≥165,000-row benchmark and record duration, peak memory, row counts, and machine context. Expected: no silent loss and completion within the documented gate.

- [ ] **Step 4: Re-run deterministic, available live/official, and adversarial paths**

Run deterministic demo twice and compare files; run live OpenRouter/RSS and official-data paths when their external prerequisites are available; gate eligible and deliberately ineligible bundles; scan each generated bundle with Gitleaks. Expected successful live result: three locally valid claims, requested/served model, no fallback, provider-neutral metadata, and no secret. Unavailable external branches remain explicitly `BLOCKED` and do not suppress the other checks.

- [ ] **Step 5: Close review findings against one final candidate**

Use independent plan/spec, correctness, security/privacy, and acceptance-evidence reviewers against a fixed candidate range. After a review-driven change, regenerate affected tracked examples/architecture using run IDs and artifact/content hashes, commit all tracked code/docs/evidence, then run the complete Steps 2–4 set plus metadata/content/history scans against that exact clean HEAD and re-review it. Never place the commit's own SHA inside tracked evidence. Repeat until reviewers report no blocking findings and the final full pass changes no tracked file; only post-push ignored release evidence records the immutable final SHA.

- [ ] **Step 6: Verify public-release prerequisites and reachable history**

Confirm `gh auth status`, no remote conflict, clean branch, complete commits, ignored restricted challenge document, and no raw/ignored data staged. Run the history-aware Gitleaks scan and `scripts/check_release_contents.py --history` over all reachable paths/blobs. Abort publication and sanitize history if either finds restricted challenge content, credentials, raw data, snapshots, bundles, or agent state.

- [ ] **Step 7: Create or configure the public GitHub repository**

Use the authenticated GitHub owner and repository name `techtest2`. If it does not exist, create it public from the reviewed repository; if it exists and is owned by the authenticated user, configure `origin`. Never overwrite an unrelated repository.

- [ ] **Step 8: Establish and push the immutable final SHA**

Fast-forward `main` to the reviewed branch, push `main`, and verify the GitHub repository reports public visibility and the expected HEAD SHA. From this point onward, make no repository changes or commits; this is the exact SHA the anonymous clone must verify.

- [ ] **Step 9: Perform a credential-isolated anonymous clean-clone verification**

Resolve the public HTTPS URL while authenticated, then run both the clone and all verification commands under one scrubbed environment: a new temporary `HOME`; system Git config disabled; no GitHub, SSH, provider, credential-helper, authorization-header, or private-index settings.

```bash
PUBLIC_URL=$(gh repo view --json url --jq .url)
CLEAN_HOME=$(mktemp -d)
CLONE_DIR=$(mktemp -d)/techtest2
env -i HOME="$CLEAN_HOME" PATH="$PATH" \
  PUBLIC_URL="$PUBLIC_URL" CLONE_DIR="$CLONE_DIR" \
  UV_CACHE_DIR="$CLEAN_HOME/.cache/uv" GIT_CONFIG_NOSYSTEM=1 \
  sh -c 'git -c credential.helper= -c http.extraHeader= clone "$PUBLIC_URL.git" "$CLONE_DIR" &&
    cd "$CLONE_DIR" &&
    uv sync --frozen --extra dev &&
    uv run srag-report demo &&
    uv run pytest &&
    uv run ruff check . &&
    uv run mypy src &&
    uv lock --check'
```

Expected: the clone and every command pass without `.env`, local data, authentication, user/system Git config, credential helpers, provider keys, or private package indexes. Record the sanitized environment controls and exact immutable SHA in release evidence.

- [ ] **Step 10: Publish post-push release evidence without changing the SHA**

Write ignored `runs/release-verification.json` with public URL, public visibility, immutable verified SHA, clone timestamp, deterministic run path, sanitized environment controls, command statuses, test count, and explicit official metric limitations. Publish it as the asset and notes for GitHub release `v2.2` targeted at that exact SHA; creating the release/tag does not modify the verified commit. Run `scripts/check_external_release.py` against the public repository, tag, asset, and immutable SHA. The tracked `T-GD-6` entry is an external-state expression: the checker reports it complete only when public release `v2.2` exists, targets the current SHA, and contains passing anonymous-clone evidence; otherwise it reports `BLOCKED`. No tracked post-push edit is required or permitted.
- [ ] **Step 11: Final clean review**

Verify zero unresolved implementation findings; every unreachable external criterion is explicitly `BLOCKED` and not complete; no tracked changes exist after the immutable SHA; and the public README/PDF render correctly. Do not commit or push after anonymous-clone verification.
