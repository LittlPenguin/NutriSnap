from __future__ import annotations

from services.gpt_advice_service import generate_gpt_advice


def test_generate_gpt_advice_uses_fallback_when_api_key_missing(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result = generate_gpt_advice("披萨", 150, 399, "减脂")

    assert result["status"] == "fallback"
    assert "估算" in result["advice"]
    assert "不作为医学或营养诊断" in result["advice"]


def test_generate_gpt_advice_returns_error_fallback_when_client_fails(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class FailingResponses:
        @staticmethod
        def create(**kwargs):
            raise RuntimeError("network down")

    class FailingClient:
        responses = FailingResponses()

    result = generate_gpt_advice("披萨", 150, 399, "减脂", client=FailingClient())

    assert result["status"] == "error"
    assert "本地规则建议" in result["advice"]
