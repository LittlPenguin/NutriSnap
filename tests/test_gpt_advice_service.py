from __future__ import annotations

from services.gpt_advice_service import (
    OpenAISettings,
    _api_base_url,
    build_openai_client,
    generate_gpt_advice,
    mask_api_key,
    resolve_openai_settings,
    stream_model_advice,
)


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
    calls = []

    def fake_post_json(api_key, base_url, endpoint, payload):
        calls.append(
            {
                "api_key": api_key,
                "base_url": base_url,
                "endpoint": endpoint,
                "payload": payload,
            }
        )
        return {"output_text": "估算热量约399 kcal，建议控制份量并搭配蔬菜。"}

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.example.test/v1")
    monkeypatch.setenv("OPENAI_MODEL", "custom-gpt")
    monkeypatch.setattr("services.gpt_advice_service._post_json", fake_post_json)

    result = generate_gpt_advice("披萨", 150, 399, "减脂")

    assert result["status"] == "success"
    assert calls[0]["api_key"] == "test-key"
    assert calls[0]["base_url"] == "https://api.example.test/v1"
    assert calls[0]["endpoint"] == "chat/completions"
    assert calls[0]["payload"]["model"] == "custom-gpt"


def test_generate_gpt_advice_falls_back_from_chat_to_responses(monkeypatch):
    calls = []

    def fake_post_json(api_key, base_url, endpoint, payload):
        calls.append((api_key, base_url, endpoint, payload))
        if endpoint == "chat/completions":
            raise RuntimeError("chat blocked")
        return {"output": [{"content": [{"text": "估算热量为参考值，建议搭配蔬菜。"}]}]}

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.example.test/v1")
    monkeypatch.setenv("OPENAI_MODEL", "custom-gpt")
    monkeypatch.setattr("services.gpt_advice_service._post_json", fake_post_json)

    result = generate_gpt_advice("披萨", 150, 399, "减脂")

    assert result["status"] == "success"
    assert [call[2] for call in calls] == ["chat/completions", "responses"]
    assert calls[0][3]["model"] == "custom-gpt"
    assert calls[0][3]["messages"][1]["content"]
    assert calls[1][3]["input"]


def test_openai_settings_prefers_session_override_over_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://env.example.test/v1")
    monkeypatch.setenv("OPENAI_MODEL", "env-model")

    settings = resolve_openai_settings(
        {
            "api_key": "session-key",
            "base_url": "https://session.example.test/v1",
            "model": "session-model",
        }
    )

    assert isinstance(settings, OpenAISettings)
    assert settings.api_key == "session-key"
    assert settings.base_url == "https://session.example.test/v1"
    assert settings.model == "session-model"
    assert settings.source == "session"
    assert settings.has_api_key


def test_openai_settings_reads_env_and_masks_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key-abcdef")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://env.example.test/v1")
    monkeypatch.setenv("OPENAI_MODEL", "env-model")

    settings = resolve_openai_settings()

    assert settings.api_key == "test-openai-key-abcdef"
    assert settings.base_url == "https://env.example.test/v1"
    assert settings.model == "env-model"
    assert settings.source == "env"
    assert mask_api_key(settings.api_key) == "tes****cdef"


def test_generate_gpt_advice_uses_explicit_settings(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    calls = []

    def fake_post_json(api_key, base_url, endpoint, payload):
        calls.append((api_key, base_url, endpoint, payload))
        return {"output_text": "估算热量约399 kcal，建议搭配蔬菜。"}

    monkeypatch.setattr("services.gpt_advice_service._post_json", fake_post_json)

    result = generate_gpt_advice(
        "披萨",
        150,
        399,
        "减脂",
        settings=OpenAISettings(
            api_key="session-key",
            base_url="https://session.example.test/v1",
            model="session-model",
            source="session",
        ),
    )

    assert result["status"] == "success"
    assert calls[0][0] == "session-key"
    assert calls[0][1] == "https://session.example.test/v1"
    assert calls[0][3]["model"] == "session-model"


def test_generate_gpt_advice_uses_injected_client_and_explicit_settings(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    calls = {}

    class SuccessfulResponses:
        @staticmethod
        def create(**kwargs):
            calls["request"] = kwargs

            class Response:
                output_text = "估算热量约399 kcal，建议搭配蔬菜。"

            return Response()

    class SuccessfulClient:
        responses = SuccessfulResponses()

    result = generate_gpt_advice(
        "披萨",
        150,
        399,
        "减脂",
        client=SuccessfulClient(),
        settings=OpenAISettings(
            api_key="session-key",
            base_url="https://session.example.test/v1",
            model="session-model",
            source="session",
        ),
    )

    assert result["status"] == "success"
    assert calls["request"]["model"] == "session-model"
    assert "披萨" in calls["request"]["input"]


def test_api_base_url_accepts_root_or_endpoint_urls():
    assert _api_base_url("https://api.example.test/v1") == "https://api.example.test/v1"
    assert _api_base_url("https://api.example.test/v1/responses") == "https://api.example.test/v1"
    assert (
        _api_base_url("https://api.example.test/v1/chat/completions")
        == "https://api.example.test/v1"
    )


def test_stream_model_advice_yields_delta_and_done(monkeypatch):
    calls = []

    def fake_stream_json(api_key, base_url, endpoint, payload):
        calls.append((api_key, base_url, endpoint, payload))
        yield {"type": "delta", "text": "这份披萨"}
        yield {"type": "delta", "text": "热量约399 kcal。"}
        yield {"type": "done", "text": "这份披萨热量约399 kcal。"}

    monkeypatch.setattr("services.gpt_advice_service._stream_json", fake_stream_json)

    events = list(
        stream_model_advice(
            "披萨",
            150,
            399,
            "减脂",
            settings=OpenAISettings("test-key", "https://api.example.test/v1", "model-x", "session"),
        )
    )

    assert [event["type"] for event in events] == ["delta", "delta", "done"]
    assert events[-1]["text"] == "这份披萨热量约399 kcal。"
    assert calls[0][2] == "chat/completions"
    assert calls[0][3]["model"] == "model-x"
    assert calls[0][3]["stream"] is True


def test_stream_model_advice_reports_error_reason_without_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")

    events = list(stream_model_advice("披萨", 150, 399, "减脂"))

    assert events[-1]["type"] == "error"
    assert "API Key 未配置" in events[-1]["reason"]
    assert "本地规则建议" in events[-1]["fallback"]


def test_stream_model_advice_reports_http_error_reason(monkeypatch):
    def fake_stream_json(api_key, base_url, endpoint, payload):
        raise RuntimeError("HTTP 403 PermissionDenied")
        yield

    monkeypatch.setattr("services.gpt_advice_service._stream_json", fake_stream_json)

    events = list(
        stream_model_advice(
            "披萨",
            150,
            399,
            "减脂",
            settings=OpenAISettings("test-key", "https://api.example.test/v1", "model-x", "session"),
        )
    )

    assert events[-1]["type"] == "error"
    assert "HTTP 403 PermissionDenied" in events[-1]["reason"]
    assert "本地规则建议" in events[-1]["fallback"]


def test_stream_model_advice_reports_empty_stream(monkeypatch):
    def fake_stream_json(api_key, base_url, endpoint, payload):
        if False:
            yield {"type": "delta", "text": ""}

    monkeypatch.setattr("services.gpt_advice_service._stream_json", fake_stream_json)

    events = list(
        stream_model_advice(
            "披萨",
            150,
            399,
            "减脂",
            settings=OpenAISettings("test-key", "https://api.example.test/v1", "model-x", "session"),
        )
    )

    assert events[-1]["type"] == "error"
    assert events[-1]["reason"] == "empty streaming response"
    assert "本地规则建议" in events[-1]["fallback"]
