from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
DEFAULT_DB_PATH = DATA_DIR / "food_calorie.db"
DEFAULT_SEED_PATH = DATA_DIR / "food_calorie_seed.csv"
DEFAULT_MODEL_PATH = MODELS_DIR / "food_resnet18.pth"
DEFAULT_CLASS_NAMES_PATH = MODELS_DIR / "class_names.json"

FOOD101_SUBSET_CLASSES = [
    "apple_pie",
    "baby_back_ribs",
    "beef_carpaccio",
    "caesar_salad",
    "cheesecake",
    "chicken_curry",
    "dumplings",
    "french_fries",
    "hamburger",
    "pizza",
    "ramen",
    "sushi",
]

CLASS_NAME_CN = {
    "apple_pie": "苹果派",
    "baby_back_ribs": "烤肋排",
    "beef_carpaccio": "牛肉薄片",
    "caesar_salad": "凯撒沙拉",
    "cheesecake": "芝士蛋糕",
    "chicken_curry": "咖喱鸡",
    "dumplings": "饺子",
    "french_fries": "薯条",
    "hamburger": "汉堡",
    "pizza": "披萨",
    "ramen": "拉面",
    "sushi": "寿司",
}

USER_GOALS = ["普通饮食", "减脂", "增肌", "控糖"]

DEMO_PREDICTION = {
    "status": "demo",
    "predicted_class": "pizza",
    "predicted_name_cn": "披萨",
    "confidence": 0.93,
    "top3": [
        {"class_name": "pizza", "name_cn": "披萨", "confidence": 0.93},
        {"class_name": "hamburger", "name_cn": "汉堡", "confidence": 0.04},
        {"class_name": "cheesecake", "name_cn": "芝士蛋糕", "confidence": 0.01},
    ],
    "message": "当前处于演示模式，结果为课程展示示例。",
}
