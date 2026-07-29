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

from srag_report.agent.commentary import (
    DEFAULT_OPENROUTER_MODEL,
    OpenRouterCommentaryAdapter,
)
from srag_report.agent.models import EvidenceBundle


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
                    "claim_id": "claim-1",
                    "text": "O indicador de crescimento está disponível.",
                    "evidence_ids": [evidence_id],
                },
                {
                    "claim_id": "claim-2",
                    "text": "O indicador de mortalidade está disponível.",
                    "evidence_ids": ["metric:mortality_per_100k"],
                },
                {
                    "claim_id": "claim-3",
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
    text_schema = request["response_format"]["json_schema"]["schema"]["properties"][  # type: ignore[index]
        "claims"
    ]["items"]["properties"]["text"]
    claims_schema = request["response_format"]["json_schema"]["schema"]["properties"][  # type: ignore[index]
        "claims"
    ]
    claim_item_schema = claims_schema["items"]
    assert claim_item_schema["required"] == ["text", "evidence_ids"]
    assert "claim_id" not in claim_item_schema["properties"]
    assert claims_schema["minItems"] == claims_schema["maxItems"] == 3
    assert text_schema["maxLength"] == 240
    assert text_schema["pattern"] == "^[^0-9]*$"
    assert '"metric:case_growth"' in request["messages"][1]["content"]  # type: ignore[index]


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


def test_openrouter_assigns_deterministic_ids_when_provider_omits_them() -> None:
    without_ids = json.loads(_claims())
    for claim in without_ids["claims"]:
        del claim["claim_id"]

    result = _adapter(FakeCompletions(_stream(json.dumps(without_ids)))).generate(_evidence())

    assert [claim.claim_id for claim in result.claims] == [
        "openrouter-claim-1",
        "openrouter-claim-2",
        "openrouter-claim-3",
    ]


@pytest.mark.parametrize(
    ("stream", "error_type"),
    [
        (_stream("not-json"), ValueError),
        (_stream(_claims(), finish_reason="length"), RuntimeError),
        (_stream(_claims(), model=None), RuntimeError),
        (_stream(_claims(evidence_id="metric:unknown")), ValueError),
    ],
)
def test_openrouter_fails_closed_for_invalid_streams(
    stream: list[object], error_type: type[Exception]
) -> None:
    with pytest.raises(error_type):
        _adapter(FakeCompletions(stream, stream)).generate(_evidence())
