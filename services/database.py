from __future__ import annotations

import csv
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from services.schemas import DEFAULT_DB_PATH, DEFAULT_SEED_PATH


class Database:
    """Small SQLite data access layer for calorie data, recognition history, and GPT logs."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH, seed_path: str | Path = DEFAULT_SEED_PATH) -> None:
        self.db_path = Path(db_path)
        self.seed_path = Path(seed_path)

    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS food_calorie (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    class_name TEXT NOT NULL UNIQUE,
                    name_cn TEXT NOT NULL,
                    calorie_per_100g REAL NOT NULL,
                    default_weight_g REAL NOT NULL,
                    category TEXT NOT NULL,
                    note TEXT
                );

                CREATE TABLE IF NOT EXISTS recognition_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_name TEXT,
                    predicted_class TEXT NOT NULL,
                    predicted_name_cn TEXT NOT NULL,
                    confidence REAL,
                    weight_g REAL NOT NULL,
                    calorie_per_100g REAL NOT NULL,
                    total_calorie REAL NOT NULL,
                    gpt_advice TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS gpt_advice_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    history_id INTEGER,
                    user_goal TEXT NOT NULL,
                    prompt_summary TEXT NOT NULL,
                    advice TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(history_id) REFERENCES recognition_history(id)
                );
                """
            )
            count = connection.execute("SELECT COUNT(*) AS count FROM food_calorie").fetchone()["count"]
            if count == 0:
                self._seed_foods(connection)

    def _seed_foods(self, connection: sqlite3.Connection) -> None:
        if not self.seed_path.exists():
            raise FileNotFoundError(f"Seed file not found: {self.seed_path}")
        with self.seed_path.open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            rows = [
                (
                    row["class_name"],
                    row["name_cn"],
                    float(row["calorie_per_100g"]),
                    float(row["default_weight_g"]),
                    row["category"],
                    row.get("note", ""),
                )
                for row in reader
            ]
        connection.executemany(
            """
            INSERT INTO food_calorie (
                class_name, name_cn, calorie_per_100g, default_weight_g, category, note
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

    def get_food(self, class_name: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM food_calorie WHERE class_name = ?",
                (class_name,),
            ).fetchone()
        return dict(row) if row else None

    def list_foods(self, category: str | None = None, query: str | None = None) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if category and category != "全部":
            clauses.append("category = ?")
            params.append(category)
        if query:
            clauses.append("(class_name LIKE ? OR name_cn LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%"])
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM food_calorie {where} ORDER BY category, name_cn",
                params,
            ).fetchall()
        return [dict(row) for row in rows]

    def save_history(self, record: dict[str, Any]) -> int:
        created_at = record.get("created_at") or datetime.now().isoformat(timespec="seconds")
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO recognition_history (
                    image_name, predicted_class, predicted_name_cn, confidence, weight_g,
                    calorie_per_100g, total_calorie, gpt_advice, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.get("image_name"),
                    record["predicted_class"],
                    record["predicted_name_cn"],
                    record.get("confidence"),
                    record["weight_g"],
                    record["calorie_per_100g"],
                    record["total_calorie"],
                    record.get("gpt_advice", ""),
                    created_at,
                ),
            )
            return int(cursor.lastrowid)

    def list_history(self, limit: int | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM recognition_history ORDER BY datetime(created_at) DESC, id DESC"
        params: tuple[Any, ...] = ()
        if limit is not None:
            sql += " LIMIT ?"
            params = (limit,)
        with self.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def save_gpt_advice_log(self, record: dict[str, Any]) -> int:
        created_at = record.get("created_at") or datetime.now().isoformat(timespec="seconds")
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO gpt_advice_log (
                    history_id, user_goal, prompt_summary, advice, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record.get("history_id"),
                    record["user_goal"],
                    record["prompt_summary"],
                    record["advice"],
                    record["status"],
                    created_at,
                ),
            )
            return int(cursor.lastrowid)

    def list_gpt_advice_logs(self, limit: int | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM gpt_advice_log ORDER BY datetime(created_at) DESC, id DESC"
        params: tuple[Any, ...] = ()
        if limit is not None:
            sql += " LIMIT ?"
            params = (limit,)
        with self.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [dict(row) for row in rows]


def get_database() -> Database:
    db = Database()
    db.initialize()
    return db
