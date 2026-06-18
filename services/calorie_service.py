from __future__ import annotations

from typing import Any

from services.database import Database, get_database


def _normalize_number(value: float) -> int | float:
    """将数值标准化：如果是整数则返回 int，否则保留两位小数。"""
    return int(value) if float(value).is_integer() else round(float(value), 2)


class CalorieService:
    """热量计算服务：根据食物类别和重量估算热量。"""

    def __init__(self, db: Database | None = None) -> None:
        """初始化热量服务。

        Args:
            db: 数据库实例，不传则自动创建默认数据库
        """
        self.db = db or get_database()

    def calculate_calorie(self, class_name: str, weight_g: float | int | str) -> dict[str, Any]:
        """根据食物类别和重量计算估算热量。

        公式：总热量 = 每 100g 热量 × (重量 / 100)

        Args:
            class_name: 食物类别英文名
            weight_g: 食物重量（克）

        Returns:
            包含 class_name、name_cn、weight_g、calorie_per_100g、total_calorie 的字典

        Raises:
            ValueError: 重量不合法（非正数）
            KeyError: 食物类别在数据库中不存在
        """
        try:
            weight = float(weight_g)
        except (TypeError, ValueError) as exc:
            raise ValueError("weight_g must be a positive number") from exc
        if weight <= 0:
            raise ValueError("weight_g must be a positive number")

        food = self.db.get_food(class_name)
        if not food:
            raise KeyError(f"未知的食物类别: {class_name}")

        calorie_per_100g = float(food["calorie_per_100g"])
        total_calorie = calorie_per_100g * weight / 100
        return {
            "class_name": food["class_name"],
            "name_cn": food["name_cn"],
            "weight_g": _normalize_number(weight),
            "calorie_per_100g": _normalize_number(calorie_per_100g),
            "total_calorie": _normalize_number(total_calorie),
        }


def calculate_calorie(class_name: str, weight_g: float | int | str) -> dict[str, Any]:
    """快捷函数：使用默认 CalorieService 实例计算热量。"""
    return CalorieService().calculate_calorie(class_name, weight_g)
