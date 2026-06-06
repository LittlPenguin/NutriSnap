from __future__ import annotations

import json
import os
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import httpx
from dotenv import load_dotenv
from openai import OpenAI

from services.schemas import PROJECT_ROOT


@dataclass(frozen=True)
class OpenAISettings:
    api_key: str | None
    base_url: str | None
    model: str
    source: str

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key)


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def resolve_openai_settings(overrides: dict[str, Any] | OpenAISettings | None = None) -> OpenAISettings:
    load_dotenv(PROJECT_ROOT / ".env")
    if isinstance(overrides, OpenAISettings):
        return overrides

    overrides = overrides or {}
    session_api_key = _clean(overrides.get("api_key"))
    session_base_url = _clean(overrides.get("base_url"))
    session_model = _clean(overrides.get("model"))

    env_api_key = _clean(os.getenv("OPENAI_API_KEY"))
    env_base_url = _clean(os.getenv("OPENAI_BASE_URL"))
    env_model = _clean(os.getenv("OPENAI_MODEL"))

    api_key = session_api_key or env_api_key
    base_url = session_base_url or env_base_url
    model = session_model or env_model or "gpt-5"

    if session_api_key or session_base_url or session_model:
        source = "session"
    elif env_api_key or env_base_url or env_model:
        source = "env"
    else:
        source = "default"

    return OpenAISettings(api_key=api_key, base_url=base_url, model=model, source=source)


def mask_api_key(api_key: str | None) -> str:
    key = _clean(api_key)
    if not key:
        return "未配置"
    if len(key) <= 8:
        return "****"
    return f"{key[:3]}****{key[-4:]}"


def build_openai_client(api_key: str, base_url: str | None = None) -> OpenAI:
    return OpenAI(api_key=api_key, base_url=base_url or None, timeout=20.0)


def _api_base_url(base_url: str | None) -> str:
    base = (base_url or "https://api.openai.com/v1").rstrip("/")
    if base.endswith("/chat/completions"):
        return base[: -len("/chat/completions")]
    if base.endswith("/responses"):
        return base[: -len("/responses")]
    return base


def _post_json(api_key: str, base_url: str | None, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{_api_base_url(base_url)}/{endpoint.lstrip('/')}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    last_error: Exception | None = None
    with httpx.Client(timeout=45.0) as http_client:
        for _ in range(2):
            try:
                response = http_client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code < 500:
                    raise
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
    if last_error:
        raise last_error
    raise RuntimeError("OpenAI HTTP request failed")


def _safe_error_reason(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        try:
            body = exc.response.json()
            message = body.get("error", {}).get("message") or body.get("message") or exc.response.text
        except Exception:
            message = exc.response.text
        text = str(message).strip()
        return f"HTTP {status_code}: {text[:180]}" if text else f"HTTP {status_code}"
    if isinstance(exc, httpx.TimeoutException):
        return "timeout"
    return str(exc)[:220] or exc.__class__.__name__


def _extract_stream_delta(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if choices:
        delta = choices[0].get("delta") or {}
        content = delta.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(str(item.get("text", item)) for item in content)
        text = choices[0].get("text")
        return str(text) if text else ""

    if payload.get("type") in {"response.output_text.delta", "output_text.delta"}:
        return str(payload.get("delta") or "")
    if payload.get("delta") and isinstance(payload.get("delta"), str):
        return str(payload["delta"])
    if payload.get("output_text_delta"):
        return str(payload["output_text_delta"])
    return ""


def _stream_json(
    api_key: str,
    base_url: str | None,
    endpoint: str,
    payload: dict[str, Any],
) -> Iterator[dict[str, str]]:
    url = f"{_api_base_url(base_url)}/{endpoint.lstrip('/')}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    full_text = ""
    with httpx.Client(timeout=45.0) as http_client:
        with http_client.stream("POST", url, headers=headers, json=payload) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                text_line = line.decode("utf-8", errors="ignore") if isinstance(line, bytes) else str(line)
                text_line = text_line.strip()
                if not text_line or not text_line.startswith("data:"):
                    continue
                data = text_line.removeprefix("data:").strip()
                if data == "[DONE]":
                    yield {"type": "done", "text": full_text}
                    return
                try:
                    parsed = json.loads(data)
                except json.JSONDecodeError:
                    continue
                delta = _extract_stream_delta(parsed)
                if delta:
                    full_text += delta
                    yield {"type": "delta", "text": delta}
            if full_text:
                yield {"type": "done", "text": full_text}


def build_prompt(food_name: str, weight_g: float, total_calorie: float, user_goal: str) -> str:
    return (
        "请基于以下已经明确给出的饮食记录生成中文饮食建议，100字以内。"
        "不要说食物或目标未明确，不要给医学诊断或治疗建议，必须说明热量为估算值。"
        f"\n食物名称：{food_name}"
        f"\n本次重量：{weight_g}g"
        f"\n估算热量：{total_calorie} kcal"
        f"\n用户目标：{user_goal}"
    )


def local_rule_advice(food_name: str, weight_g: float, total_calorie: float, user_goal: str, prefix: str = "") -> str:
    if total_calorie >= 500:
        suggestion = "这餐热量偏高，建议控制份量，并搭配蔬菜或无糖饮品。"
    elif total_calorie >= 300:
        suggestion = "这餐热量中等，建议关注当天其他高油高糖食物摄入。"
    else:
        suggestion = "这餐热量较低，可按当天饱腹感搭配优质蛋白和蔬菜。"

    if user_goal == "减脂":
        suggestion += " 减脂期间优先保证蛋白质和蔬菜，减少额外酱料。"
    elif user_goal == "增肌":
        suggestion += " 增肌期间可搭配蛋白质来源，并关注训练前后总能量。"
    elif user_goal == "控糖":
        suggestion += " 控糖目标下建议留意主食和甜味酱料摄入。"

    lead = f"{prefix}本地规则建议：" if prefix else ""
    return f"{lead}{food_name}{weight_g}g 估算约 {total_calorie} kcal。{suggestion} 不作为医学或营养诊断。"


def _extract_output_text(response: Any) -> str:
    if isinstance(response, dict):
        output_text = response.get("output_text")
        if output_text:
            return str(output_text).strip()
        choices = response.get("choices") or []
        if choices:
            message = choices[0].get("message") or {}
            content = message.get("content")
            if content:
                if isinstance(content, list):
                    return "\n".join(str(item.get("text", item)) for item in content).strip()
                return str(content).strip()
        output = response.get("output") or []
        texts: list[str] = []
        for item in output:
            for content in item.get("content", []) or []:
                text = content.get("text")
                if text:
                    texts.append(str(text))
        return "\n".join(texts).strip()

    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text).strip()
    output = getattr(response, "output", None) or []
    texts: list[str] = []
    for item in output:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if text:
                texts.append(str(text))
    return "\n".join(texts).strip()


def _generate_http_advice(settings: OpenAISettings, prompt: str) -> str:
    if not settings.api_key:
        raise ValueError("OpenAI API key is required")

    instructions = _model_instructions()
    responses_payload = {
        "model": settings.model,
        "instructions": instructions,
        "input": prompt,
        "max_output_tokens": 180,
    }
    chat_payload = {
        "model": settings.model,
        "messages": [
            {"role": "system", "content": instructions},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 180,
    }

    errors: list[Exception] = []
    for endpoint, payload in (("chat/completions", chat_payload), ("responses", responses_payload)):
        try:
            advice = _extract_output_text(_post_json(str(settings.api_key), settings.base_url, endpoint, payload))
            if advice:
                return advice
        except Exception as exc:
            errors.append(exc)
    raise RuntimeError(f"OpenAI HTTP request failed: {errors[-1] if errors else 'empty response'}")


def _model_instructions() -> str:
    return (
        "你是饮食记录应用中的建议助手。输出中文，100字以内。"
        "只能给一般饮食记录建议，不做医学或营养诊断。"
    )


def _chat_stream_payload(settings: OpenAISettings, prompt: str) -> dict[str, Any]:
    return {
        "model": settings.model,
        "messages": [
            {"role": "system", "content": _model_instructions()},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 180,
        "stream": True,
    }


def _responses_stream_payload(settings: OpenAISettings, prompt: str) -> dict[str, Any]:
    return {
        "model": settings.model,
        "instructions": _model_instructions(),
        "input": prompt,
        "max_output_tokens": 180,
        "stream": True,
    }


def stream_model_advice(
    food_name: str,
    weight_g: float,
    total_calorie: float,
    user_goal: str,
    settings: OpenAISettings | dict[str, Any] | None = None,
) -> Iterator[dict[str, str]]:
    resolved_settings = resolve_openai_settings(settings)
    fallback = local_rule_advice(food_name, weight_g, total_calorie, user_goal, prefix="Model 调用失败，")

    if not resolved_settings.api_key:
        yield {
            "type": "error",
            "reason": "API Key 未配置",
            "fallback": local_rule_advice(food_name, weight_g, total_calorie, user_goal, prefix="Model 调用失败，"),
        }
        return

    prompt = build_prompt(food_name, weight_g, total_calorie, user_goal)
    endpoint_payloads = (
        ("chat/completions", _chat_stream_payload(resolved_settings, prompt)),
        ("responses", _responses_stream_payload(resolved_settings, prompt)),
    )
    last_reason = "empty streaming response"
    for endpoint, payload in endpoint_payloads:
        emitted_text = ""
        try:
            for event in _stream_json(str(resolved_settings.api_key), resolved_settings.base_url, endpoint, payload):
                if event.get("type") == "delta":
                    emitted_text += event.get("text", "")
                    yield event
                elif event.get("type") == "done":
                    final_text = event.get("text") or emitted_text
                    if final_text.strip():
                        yield {"type": "done", "text": final_text.strip()}
                        return
            last_reason = "empty streaming response"
        except Exception as exc:
            last_reason = _safe_error_reason(exc)
    yield {"type": "error", "reason": last_reason, "fallback": fallback}


def generate_gpt_advice(
    food_name: str,
    weight_g: float,
    total_calorie: float,
    user_goal: str,
    client: Any | None = None,
    settings: OpenAISettings | dict[str, Any] | None = None,
) -> dict[str, str]:
    resolved_settings = resolve_openai_settings(settings)

    if client is None and not resolved_settings.api_key:
        return {
            "status": "fallback",
            "advice": local_rule_advice(food_name, weight_g, total_calorie, user_goal),
        }

    try:
        prompt = build_prompt(food_name, weight_g, total_calorie, user_goal)
        if client is None:
            advice = _generate_http_advice(resolved_settings, prompt)
            return {"status": "success", "advice": advice}

        response = client.responses.create(
            model=resolved_settings.model,
            instructions=_model_instructions(),
            input=prompt,
            max_output_tokens=180,
        )
        advice = _extract_output_text(response)
        if not advice:
            raise ValueError("empty OpenAI response")
        return {"status": "success", "advice": advice}
    except Exception:
        return {
            "status": "error",
            "advice": local_rule_advice(food_name, weight_g, total_calorie, user_goal, prefix="Model 调用失败，"),
        }
