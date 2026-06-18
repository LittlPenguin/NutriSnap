from __future__ import annotations

import pandas as pd

from services.database import Database, get_database


def _history_frame(db: Database) -> pd.DataFrame:
    """从数据库读取识别历史并转换为 DataFrame。"""
    history = db.list_history()
    if not history:
        return pd.DataFrame(
            columns=[
                "id",
                "predicted_name_cn",
                "total_calorie",
            ]
        )
    return pd.DataFrame(history)


def get_food_ranking(db: Database | None = None, limit: int = 5) -> pd.DataFrame:
    """获取常见食物排行：按识别次数降序，取前 N 名。"""
    db = db or get_database()
    frame = _history_frame(db)
    if frame.empty:
        return pd.DataFrame(columns=["predicted_name_cn", "count", "total_calorie"])
    ranking = (
        frame.groupby("predicted_name_cn", as_index=False)
        .agg(count=("id", "count"), total_calorie=("total_calorie", "sum"))
        .sort_values(["count", "total_calorie"], ascending=False)
        .head(limit)
        .reset_index(drop=True)
    )
    return ranking
