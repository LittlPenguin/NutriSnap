from __future__ import annotations

from services.database import Database


def test_database_initializes_seed_foods(tmp_path):
    db = Database(tmp_path / "food.db")
    db.initialize()

    foods = db.list_foods()

    assert len(foods) == 12
    assert foods[0]["class_name"]
    assert any(food["class_name"] == "pizza" and food["name_cn"] == "披萨" for food in foods)


def test_save_history_returns_id_and_queries_newest_first(tmp_path):
    db = Database(tmp_path / "food.db")
    db.initialize()

    old_id = db.save_history(
        {
            "image_name": "old.jpg",
            "predicted_class": "sushi",
            "predicted_name_cn": "寿司",
            "confidence": 0.89,
            "weight_g": 180,
            "calorie_per_100g": 150,
            "total_calorie": 270,
            "gpt_advice": "建议搭配蔬菜。",
            "created_at": "2026-06-04T12:00:00",
        }
    )
    new_id = db.save_history(
        {
            "image_name": "new.jpg",
            "predicted_class": "pizza",
            "predicted_name_cn": "披萨",
            "confidence": 0.93,
            "weight_g": 150,
            "calorie_per_100g": 266,
            "total_calorie": 399,
            "gpt_advice": "建议控制份量。",
            "created_at": "2026-06-05T12:00:00",
        }
    )

    rows = db.list_history()

    assert old_id != new_id
    assert [row["id"] for row in rows] == [new_id, old_id]


def test_save_gpt_log_records_status(tmp_path):
    db = Database(tmp_path / "food.db")
    db.initialize()

    history_id = db.save_history(
        {
            "image_name": "pizza.jpg",
            "predicted_class": "pizza",
            "predicted_name_cn": "披萨",
            "confidence": 0.93,
            "weight_g": 150,
            "calorie_per_100g": 266,
            "total_calorie": 399,
            "gpt_advice": "建议控制份量。",
        }
    )
    log_id = db.save_gpt_advice_log(
        {
            "history_id": history_id,
            "user_goal": "减脂",
            "prompt_summary": "披萨 150g 399kcal",
            "advice": "建议控制份量。",
            "status": "fallback",
        }
    )

    logs = db.list_gpt_advice_logs()

    assert log_id == logs[0]["id"]
    assert logs[0]["status"] == "fallback"
