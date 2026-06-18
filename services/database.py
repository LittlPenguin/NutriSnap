from __future__ import annotations

import csv
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from services.schemas import DEFAULT_DB_PATH, DEFAULT_SEED_PATH


class Database:
    """SQLite 数据访问层，管理食物热量表、识别历史记录和 GPT 调用日志。"""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH, seed_path: str | Path = DEFAULT_SEED_PATH) -> None:
        """初始化数据库连接参数。

        Args:
            db_path: SQLite 数据库文件路径，默认为 data/food_calorie.db
            seed_path: 初始热量数据 CSV 路径，默认为 data/food_calorie_seed.csv
        """
        self.db_path = Path(db_path)
        self.seed_path = Path(seed_path)

    def connect(self) -> sqlite3.Connection:
        """创建并返回数据库连接，自动创建父目录，设置行工厂为 sqlite3.Row（支持列名访问）。"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        """建表（如不存在）并在热量表为空时导入初始 CSV 数据。"""
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
            self._seed_foods(connection)

    def _seed_foods(self, connection: sqlite3.Connection) -> None:
        """从 CSV 文件读取初始食物热量数据并批量插入 food_calorie 表。"""
        if not self.seed_path.exists():
            raise FileNotFoundError(f"初始数据 CSV 文件不存在: {self.seed_path}")
        with self.seed_path.open("r", encoding="utf-8-sig", newline="") as file:
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
        if not rows:
            raise ValueError("初始数据 CSV 为空，无法导入 food_calorie 表")
        seed_class_names = [row[0] for row in rows]
        connection.execute(
            f"DELETE FROM food_calorie WHERE class_name NOT IN ({','.join('?' for _ in seed_class_names)})",
            tuple(seed_class_names),
        )
        connection.executemany(
            """
            INSERT INTO food_calorie (
                class_name, name_cn, calorie_per_100g, default_weight_g, category, note
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(class_name) DO UPDATE SET
                name_cn = excluded.name_cn,
                calorie_per_100g = excluded.calorie_per_100g,
                default_weight_g = excluded.default_weight_g,
                category = excluded.category,
                note = excluded.note
            """,
            rows,
        )

    def get_food(self, class_name: str) -> dict[str, Any] | None:
        """根据 class_name 查询单条食物热量记录。"""
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM food_calorie WHERE class_name = ?",
                (class_name,),
            ).fetchone()
        return dict(row) if row else None

    def list_foods(self, category: str | None = None, query: str | None = None) -> list[dict[str, Any]]:
        """查询食物热量表，支持按分类筛选和名称模糊搜索。"""
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
        """保存一条识别历史记录，返回自增 ID。"""
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
        """查询识别历史，按时间倒序，可选限制条数。"""
        sql = "SELECT * FROM recognition_history ORDER BY datetime(created_at) DESC, id DESC"
        params: tuple[Any, ...] = ()
        if limit is not None:
            sql += " LIMIT ?"
            params = (limit,)
        with self.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def save_gpt_advice_log(self, record: dict[str, Any]) -> int:
        """保存 GPT 建议调用日志，返回自增 ID。"""
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
        """查询 GPT 建议日志，按时间倒序，可选限制条数。"""
        sql = "SELECT * FROM gpt_advice_log ORDER BY datetime(created_at) DESC, id DESC"
        params: tuple[Any, ...] = ()
        if limit is not None:
            sql += " LIMIT ?"
            params = (limit,)
        with self.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [dict(row) for row in rows]


def get_database() -> Database:
    """快捷函数：创建并初始化数据库实例。"""
    db = Database()
    db.initialize()
    return db
