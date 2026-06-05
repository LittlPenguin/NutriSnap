from __future__ import annotations

from typing import Any

from services.database import Database, get_database


def _normalize_number(value: float) -> int | float:
    return int(value) if float(value).is_integer() else round(float(value), 2)


class CalorieService:
    def __init__(self, db: Database | None = None) -> None:
        self.db = db or get_database()

    def calculate_calorie(self, class_name: str, weight_g: float | int | str) -> dict[str, Any]:
        try:
            weight = float(weight_g)
        except (TypeError, ValueError) as exc:
            raise ValueError("weight_g must be a positive number") from exc
        if weight <= 0:
            raise ValueError("weight_g must be a positive number")

        food = self.db.get_food(class_name)
        if not food:
            raise KeyError(f"Unknown food class_name: {class_name}")

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
    return CalorieService().calculate_calorie(class_name, weight_g)
