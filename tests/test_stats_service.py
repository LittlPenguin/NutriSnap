from __future__ import annotations

from services.database import Database
from services.stats_service import get_daily_stats, get_food_ranking


def test_daily_stats_groups_history_by_date(tmp_path):
    db = Database(tmp_path / "food.db")
    db.initialize()
    db.save_history(
        {
            "image_name": "pizza.jpg",
            "predicted_class": "pizza",
            "predicted_name_cn": "披萨",
            "confidence": 0.93,
            "weight_g": 150,
            "calorie_per_100g": 266,
            "total_calorie": 399,
            "gpt_advice": "建议控制份量。",
            "created_at": "2026-06-05T08:00:00",
        }
    )
    db.save_history(
        {
            "image_name": "sushi.jpg",
            "predicted_class": "sushi",
            "predicted_name_cn": "寿司",
            "confidence": 0.89,
            "weight_g": 180,
            "calorie_per_100g": 150,
            "total_calorie": 270,
            "gpt_advice": "建议搭配蔬菜。",
            "created_at": "2026-06-05T12:00:00",
        }
    )

    stats = get_daily_stats(db)
    ranking = get_food_ranking(db)

    assert stats.iloc[0]["date"] == "2026-06-05"
    assert stats.iloc[0]["total_calorie"] == 669
    assert stats.iloc[0]["record_count"] == 2
    assert set(ranking["predicted_name_cn"]) == {"披萨", "寿司"}
