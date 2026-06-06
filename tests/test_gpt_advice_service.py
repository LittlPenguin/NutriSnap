from __future__ import annotations

from services.gpt_advice_service import build_openai_client, generate_gpt_advice


def test_generate_gpt_advice_uses_fallback_when_api_key_missing(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")

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


def test_build_openai_client_uses_custom_base_url(monkeypatch):
    captured = {}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("services.gpt_advice_service.OpenAI", FakeOpenAI)

    client = build_openai_client("test-key", "https://api.example.test/v1")

    assert isinstance(client, FakeOpenAI)
    assert captured["api_key"] == "test-key"
    assert captured["base_url"] == "https://api.example.test/v1"
    assert captured["timeout"] == 20.0


def test_generate_gpt_advice_reads_custom_base_url_and_model(monkeypatch):
    calls = {}

    class SuccessfulResponses:
        @staticmethod
        def create(**kwargs):
            calls["request"] = kwargs

            class Response:
                output_text = "估算热量约399 kcal，建议控制份量并搭配蔬菜。"

            return Response()

    class SuccessfulClient:
        responses = SuccessfulResponses()

    def fake_build_client(api_key, base_url):
        calls["api_key"] = api_key
        calls["base_url"] = base_url
        return SuccessfulClient()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.example.test/v1")
    monkeypatch.setenv("OPENAI_MODEL", "custom-gpt")
    monkeypatch.setattr("services.gpt_advice_service.build_openai_client", fake_build_client)

    result = generate_gpt_advice("披萨", 150, 399, "减脂")

    assert result["status"] == "success"
    assert calls["api_key"] == "test-key"
    assert calls["base_url"] == "https://api.example.test/v1"
    assert calls["request"]["model"] == "custom-gpt"
