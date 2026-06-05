from __future__ import annotations

import pandas as pd

from services.database import Database, get_database


def _history_frame(db: Database) -> pd.DataFrame:
    history = db.list_history()
    if not history:
        return pd.DataFrame(
            columns=[
                "id",
                "predicted_name_cn",
                "total_calorie",
                "created_at",
            ]
        )
    frame = pd.DataFrame(history)
    frame["created_at"] = pd.to_datetime(frame["created_at"])
    frame["date"] = frame["created_at"].dt.strftime("%Y-%m-%d")
    return frame


def get_daily_stats(db: Database | None = None, days: int = 7) -> pd.DataFrame:
    db = db or get_database()
    frame = _history_frame(db)
    if frame.empty:
        return pd.DataFrame(columns=["date", "total_calorie", "record_count"])
    stats = (
        frame.groupby("date", as_index=False)
        .agg(total_calorie=("total_calorie", "sum"), record_count=("id", "count"))
        .sort_values("date", ascending=False)
        .head(days)
        .sort_values("date")
        .reset_index(drop=True)
    )
    return stats


def get_food_ranking(db: Database | None = None, limit: int = 5) -> pd.DataFrame:
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
