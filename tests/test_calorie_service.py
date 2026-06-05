from __future__ import annotations

import pytest

from services.calorie_service import CalorieService
from services.database import Database


def test_calculate_pizza_calorie_uses_weight_and_per_100g_table(tmp_path):
    db = Database(tmp_path / "food.db")
    db.initialize()
    service = CalorieService(db)

    result = service.calculate_calorie("pizza", 150)

    assert result["class_name"] == "pizza"
    assert result["name_cn"] == "披萨"
    assert result["weight_g"] == 150
    assert result["calorie_per_100g"] == 266
    assert result["total_calorie"] == 399


@pytest.mark.parametrize("weight", [0, -1, "abc"])
def test_calculate_calorie_rejects_invalid_weight(tmp_path, weight):
    db = Database(tmp_path / "food.db")
    db.initialize()
    service = CalorieService(db)

    with pytest.raises(ValueError, match="weight_g"):
        service.calculate_calorie("pizza", weight)


def test_calculate_calorie_rejects_unknown_food(tmp_path):
    db = Database(tmp_path / "food.db")
    db.initialize()
    service = CalorieService(db)

    with pytest.raises(KeyError, match="unknown_food"):
        service.calculate_calorie("unknown_food", 100)
