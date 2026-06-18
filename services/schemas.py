from __future__ import annotations

from pathlib import Path

# ============================================================
# 项目路径常量
# ============================================================

# 项目根目录（services/schemas.py 的上两级）
PROJECT_ROOT = Path(__file__).resolve().parents[1]
# 数据目录
DATA_DIR = PROJECT_ROOT / "data"
# 模型目录
MODELS_DIR = PROJECT_ROOT / "models"
# SQLite 数据库文件路径
DEFAULT_DB_PATH = DATA_DIR / "food_calorie.db"
# 热量初始数据 CSV 路径
DEFAULT_SEED_PATH = DATA_DIR / "food_calorie_seed.csv"
# ResNet18 模型权重文件路径
DEFAULT_MODEL_PATH = MODELS_DIR / "food_resnet18.pth"
# 类别名称列表 JSON 路径
DEFAULT_CLASS_NAMES_PATH = MODELS_DIR / "class_names.json"

# ============================================================
# Food-101 子集的 25 个常见餐饮类别
# ============================================================
FOOD101_SUBSET_CLASSES = [
    "dumplings",
    "fried_rice",
    "hot_and_sour_soup",
    "spring_rolls",
    "peking_duck",
    "gyoza",
    "chicken_wings",
    "fried_calamari",
    "french_fries",
    "hamburger",
    "pizza",
    "hot_dog",
    "ice_cream",
    "donuts",
    "cup_cakes",
    "chocolate_cake",
    "cheesecake",
    "apple_pie",
    "ramen",
    "sushi",
    "bibimbap",
    "takoyaki",
    "omelette",
    "steak",
    "grilled_salmon",
]

# 英文类名 → 中文名的映射表
CLASS_NAME_CN = {
    "dumplings": "饺子",
    "fried_rice": "炒饭",
    "hot_and_sour_soup": "酸辣汤",
    "spring_rolls": "春卷",
    "peking_duck": "北京烤鸭",
    "gyoza": "煎饺",
    "chicken_wings": "鸡翅",
    "fried_calamari": "炸鱿鱼",
    "french_fries": "薯条",
    "hamburger": "汉堡",
    "pizza": "披萨",
    "hot_dog": "热狗",
    "ice_cream": "冰淇淋",
    "donuts": "甜甜圈",
    "cup_cakes": "杯子蛋糕",
    "chocolate_cake": "巧克力蛋糕",
    "cheesecake": "芝士蛋糕",
    "apple_pie": "苹果派",
    "ramen": "拉面",
    "sushi": "寿司",
    "bibimbap": "拌饭",
    "takoyaki": "章鱼烧",
    "omelette": "煎蛋卷",
    "steak": "牛排",
    "grilled_salmon": "烤三文鱼",
}

# 用户可选饮食目标
USER_GOALS = ["普通饮食", "减脂", "增肌", "控糖"]

# 固定预测结果
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
