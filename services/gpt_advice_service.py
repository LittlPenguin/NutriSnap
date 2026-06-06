from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


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
) -> dict[str, str]:
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL") or None
    model = os.getenv("OPENAI_MODEL", "gpt-5")

    if client is None and not api_key:
        return {
            "status": "fallback",
            "advice": local_rule_advice(food_name, weight_g, total_calorie, user_goal),
        }

    try:
        if client is None:
            client = build_openai_client(api_key, base_url)
        response = client.responses.create(
            model=model,
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
