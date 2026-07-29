from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import httpx
import openai
import pytest
from openai import OpenAI
from pydantic import ValidationError

from srag_report.agent.commentary import (
    DEFAULT_OPENROUTER_MODEL,
    CommentaryOutputInvalidError,
    CommentaryProviderUnavailableError,
    OpenRouterCommentaryAdapter,
    commentary_evidence_ids,
    generate_or_fallback,
)
from srag_report.agent.models import CommentaryFailureCode, CommentaryResult, EvidenceBundle


class FakeCompletions:
    def __init__(self, *outcomes: Exception | list[object]) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> Iterator[object]:
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return iter(outcome)


class FakeOpenAI:
    def __init__(self, completions: FakeCompletions) -> None:
        self.chat = SimpleNamespace(completions=completions)


def _evidence() -> EvidenceBundle:
    return EvidenceBundle.model_validate_json(
        Path("examples/deterministic-run/evidence.json").read_text(encoding="utf-8")
    )


def _claims(*, evidence_id: str = "metric:case_growth") -> str:
    return json.dumps(
        {
            "claims": [
                {
                    "text": "O indicador de crescimento está disponível.",
                    "evidence_ids": [evidence_id],
                },
                {
                    "text": "O indicador de mortalidade está disponível.",
                    "evidence_ids": ["metric:mortality_per_100k"],
                },
                {
                    "text": "A evidência de pressão sobre UTI está disponível.",
                    "evidence_ids": ["metric:icu_pressure"],
                },
            ]
        }
    )


def _stream(
    content: str,
    *,
    model: str | None = "openai/gpt-oss-20b:free",
    finish_reason: str = "stop",
) -> list[object]:
    return [
        SimpleNamespace(
            model=model,
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(content=content),
                    finish_reason=finish_reason,
                )
            ],
        )
    ]


def _adapter(completions: FakeCompletions) -> OpenRouterCommentaryAdapter:
    return OpenRouterCommentaryAdapter(client=cast(OpenAI, FakeOpenAI(completions)))


def test_openrouter_stream_returns_grounded_claims_and_served_model() -> None:
    completions = FakeCompletions(_stream(_claims()))

    result = _adapter(completions).generate(_evidence())

    assert result.requested_model == DEFAULT_OPENROUTER_MODEL == "openrouter/free"
    assert result.served_model == "openai/gpt-oss-20b:free"
    assert not result.fallback_used
    assert len(result.claims) == 3
    request = completions.calls[0]
    assert request["model"] == "openrouter/free"
    assert request["stream"] is True
    assert request["max_tokens"] == 4_096
    assert request["temperature"] == 0
    assert request["extra_body"] == {
        "provider": {"require_parameters": True},
        "reasoning": {"effort": "none", "exclude": True},
    }
    assert request["response_format"]["type"] == "json_schema"  # type: ignore[index]
    schema = request["response_format"]["json_schema"]["schema"]  # type: ignore[index]
    claims_schema = schema["properties"]["claims"]
    claim_item_schema = schema["$defs"]["ProviderCommentaryClaim"]
    text_schema = claim_item_schema["properties"]["text"]
    assert claim_item_schema["required"] == ["text", "evidence_ids"]
    assert "claim_id" not in claim_item_schema["properties"]
    assert claims_schema["minItems"] == claims_schema["maxItems"] == 3
    assert text_schema["maxLength"] == 240
    assert text_schema["pattern"] == "^[^\\p{Nd}]*$"
    assert '"metric:case_growth"' in request["messages"][1]["content"]  # type: ignore[index]
    prompt = request["messages"][1]["content"]  # type: ignore[index]
    assert "news:" not in prompt
    for item in _evidence().news:
        assert item.title not in prompt
        assert item.final_url not in prompt
    assert set(commentary_evidence_ids(_evidence())) == {
        evidence_id
        for evidence_id in _evidence().evidence_ids()
        if not evidence_id.startswith("news:")
    }


def test_openrouter_retries_one_transient_failure() -> None:
    transient = openai.APIConnectionError(
        request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    )
    completions = FakeCompletions(transient, _stream(_claims()))

    result = _adapter(completions).generate(_evidence())

    assert result.served_model == "openai/gpt-oss-20b:free"
    assert len(completions.calls) == 2


def test_openrouter_retries_one_invalid_structured_response() -> None:
    completions = FakeCompletions(_stream("not-json"), _stream(_claims()))

    result = _adapter(completions).generate(_evidence())

    assert result.served_model == "openai/gpt-oss-20b:free"
    assert len(completions.calls) == 2


def test_openrouter_assigns_deterministic_ids_after_provider_validation() -> None:
    result = _adapter(FakeCompletions(_stream(_claims()))).generate(_evidence())

    assert [claim.claim_id for claim in result.claims] == [
        "openrouter-claim-1",
        "openrouter-claim-2",
        "openrouter-claim-3",
    ]


@pytest.mark.parametrize(
    "payload",
    [
        {"claims": [{"text": "Claim válida", "evidence_ids": ["metric:case_growth"]}]},
        {
            "claims": [
                {"text": f"Claim {letter}", "evidence_ids": ["metric:case_growth"]}
                for letter in ("A", "B", "C", "D")
            ]
        },
        {"claims": [{"text": "A" * 241, "evidence_ids": ["metric:case_growth"]}] * 3},
        {"claims": [{"text": "Crescimento 50", "evidence_ids": ["metric:case_growth"]}] * 3},
        {"claims": [{"text": "Crescimento ５０", "evidence_ids": ["metric:case_growth"]}] * 3},
        {"claims": [{"text": "Crescimento ٥٠", "evidence_ids": ["metric:case_growth"]}] * 3},
        {
            "claims": [
                {
                    "claim_id": "provider-id",
                    "text": "Claim válida",
                    "evidence_ids": ["metric:case_growth"],
                }
            ]
            * 3
        },
        {"claims": [{"text": "Claim válida", "evidence_ids": ["news:news-1"]}] * 3},
    ],
)
def test_openrouter_rejects_provider_output_outside_local_schema(payload: object) -> None:
    completions = FakeCompletions(_stream(json.dumps(payload)), _stream(json.dumps(payload)))

    with pytest.raises((ValueError, ValidationError)):
        _adapter(completions).generate(_evidence())

    assert len(completions.calls) == 2


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


@pytest.mark.parametrize(("status_code", "requests"), [(503, 2), (400, 1)])
def test_openrouter_sdk_client_attempts_are_owned_by_adapter(
    status_code: int, requests: int
) -> None:
    recorded: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        recorded.append(request)
        return httpx.Response(status_code, request=request, json={"error": "synthetic"})

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key="test-key",
        max_retries=0,
        http_client=http_client,
    )
    try:
        with pytest.raises(
            CommentaryProviderUnavailableError if status_code == 503 else openai.BadRequestError
        ):
            OpenRouterCommentaryAdapter(client=client).generate(_evidence())
    finally:
        http_client.close()

    assert len(recorded) == requests


def test_invalid_provider_output_gets_a_provider_neutral_failure_code() -> None:
    result = generate_or_fallback(
        _adapter(FakeCompletions(_stream("not-json"), _stream("not-json"))), _evidence()
    )

    assert result.fallback_used
    assert result.failure_code is CommentaryFailureCode.MODEL_OUTPUT_INVALID


def test_commentary_result_requires_failure_code_exactly_for_fallback() -> None:
    claims = _adapter(FakeCompletions(_stream(_claims()))).generate(_evidence()).claims
    with pytest.raises(ValidationError):
        CommentaryResult(
            claims=claims,
            requested_model="requested",
            served_model="fallback",
            fallback_used=True,
        )
    with pytest.raises(ValidationError):
        CommentaryResult(
            claims=claims,
            requested_model="requested",
            served_model="served",
            failure_code=CommentaryFailureCode.MODEL_OUTPUT_INVALID,
        )


@pytest.mark.parametrize(
    ("stream", "error_type"),
    [
        (_stream("not-json"), ValueError),
        (_stream(_claims(), finish_reason="length"), CommentaryOutputInvalidError),
        (_stream(_claims(), model=None), CommentaryOutputInvalidError),
        (_stream(_claims(evidence_id="metric:unknown")), ValueError),
    ],
)
def test_openrouter_fails_closed_for_invalid_streams(
    stream: list[object], error_type: type[Exception]
) -> None:
    with pytest.raises(error_type):
        _adapter(FakeCompletions(stream, stream)).generate(_evidence())
