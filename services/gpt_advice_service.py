from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

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


def build_prompt(food_name: str, weight_g: float, total_calorie: float, user_goal: str) -> str:
    return (
        "请基于以下饮食记录生成中文饮食建议，100字以内。"
        "不要给医学诊断或治疗建议，必须说明热量为估算值。"
        f"\n食物：{food_name}"
        f"\n重量：{weight_g}g"
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
        if client is None:
            client = build_openai_client(str(resolved_settings.api_key), resolved_settings.base_url)
        response = client.responses.create(
            model=resolved_settings.model,
            instructions=(
                "你是饮食记录应用中的建议助手。输出中文，100字以内。"
                "只能给一般饮食记录建议，不做医学或营养诊断。"
            ),
            input=build_prompt(food_name, weight_g, total_calorie, user_goal),
            max_output_tokens=180,
        )
        advice = _extract_output_text(response)
        if not advice:
            raise ValueError("empty OpenAI response")
        return {"status": "success", "advice": advice}
    except Exception:
        return {
            "status": "error",
            "advice": local_rule_advice(food_name, weight_g, total_calorie, user_goal, prefix="GPT 调用失败，"),
        }
