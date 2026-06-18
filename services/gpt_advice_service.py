from __future__ import annotations

import json
import os
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import httpx
from dotenv import load_dotenv

from services.schemas import PROJECT_ROOT


@dataclass(frozen=True)
class OpenAISettings:
    """OpenAI 连接配置的数据类。

    Attributes:
        api_key: API 密钥
        base_url: 基础 URL（可选，用于中转代理）
        model: 模型名称
        source: 配置来源（session / env / default）
    """
    api_key: str | None
    base_url: str | None
    model: str
    source: str

    @property
    def has_api_key(self) -> bool:
        """是否有有效的 API Key。"""
        return bool(self.api_key)


def _clean(value: Any) -> str | None:
    """清理输入值：去除首尾空白，空字符串转为 None。"""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def resolve_openai_settings(overrides: dict[str, Any] | OpenAISettings | None = None) -> OpenAISettings:
    """解析 OpenAI 配置，优先级：传入参数 > .env 文件 > 默认值。

    支持三种配置来源：
    1. session：当前 Streamlit 会话中页面上的手动输入
    2. env：.env 文件中的环境变量
    3. default：使用默认值（gpt-5）
    """
    load_dotenv(PROJECT_ROOT / ".env")
    # 如果传入的就是 OpenAISettings 对象，直接返回
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
    """脱敏显示 API Key（仅显示前 3 位和后 4 位）。"""
    key = _clean(api_key)
    if not key:
        return "未配置"
    if len(key) <= 8:
        return "****"
    return f"{key[:3]}****{key[-4:]}"


def _api_base_url(base_url: str | None) -> str:
    """规范化 API Base URL：去掉末尾的 /chat/completions 或 /responses。"""
    base = (base_url or "https://api.openai.com/v1").rstrip("/")
    if base.endswith("/chat/completions"):
        return base[: -len("/chat/completions")]
    if base.endswith("/responses"):
        return base[: -len("/responses")]
    return base


def _safe_error_reason(exc: Exception) -> str:
    """从异常中安全提取可读的错误原因。"""
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
        return "连接超时"
    return str(exc)[:220] or exc.__class__.__name__


def _extract_stream_delta(payload: dict[str, Any]) -> str:
    """从流式响应的 JSON 块中提取文本增量。

    兼容 chat/completions 和 responses 两种 endpoint 格式。
    """
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
    """对 OpenAI 兼容 API 发送流式请求，逐个 yield 事件（delta / done）。

    SSE 格式：每行以 data: 开头，结尾为 data: [DONE]。
    """
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
    """构造发送给模型的提示词。"""
    return (
        "请基于以下已经明确给出的饮食记录生成中文饮食建议，100字以内。"
        "不要说食物或目标未明确，不要给医学诊断或治疗建议，必须说明热量为估算值。"
        f"\n食物名称：{food_name}"
        f"\n本次重量：{weight_g}g"
        f"\n估算热量：{total_calorie} kcal"
        f"\n用户目标：{user_goal}"
    )


def local_rule_advice(food_name: str, weight_g: float, total_calorie: float, user_goal: str, prefix: str = "") -> str:
    """基于本地规则的降级建议（当 GPT 调用失败时使用）。

    根据热量高低和目标生成不同建议文案，标注不作为医学或营养诊断。
    """
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


def _model_instructions() -> str:
    """模型 system prompt / instructions，约束输出为中文、简短、不做诊断。"""
    return (
        "你是饮食记录应用中的建议助手。输出中文，100字以内。"
        "只能给一般饮食记录建议，不做医学或营养诊断。"
    )


def _chat_stream_payload(settings: OpenAISettings, prompt: str) -> dict[str, Any]:
    """构造 chat/completions 流式请求的 payload。"""
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
    """构造 responses 流式请求的 payload。"""
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
    """流式生成 GPT 饮食建议，支持降级。

    先检查 API Key，没有则直接返回降级；
    否则依次尝试 chat/completions 和 responses 两个 endpoint 进行流式调用。
    """
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
