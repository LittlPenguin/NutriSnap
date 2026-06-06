from __future__ import annotations

import streamlit as st

from services.database import get_database
from ui.pages import (
    calorie_table_page,
    history_page,
    recognition_page,
    stats_page,
)
from ui.styles import inject_css

PAGE_LABELS = ["食物识别", "历史记录", "热量表", "统计分析"]
PAGE_KEYS = {"recognition", "history", "calories", "stats"}
DEFAULT_PAGE = "recognition"


st.set_page_config(
    page_title="NutriSnap 轻食记录",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_resource
def load_db():
    return get_database()


def resolve_page(raw_page: str | None) -> str:
    if raw_page in PAGE_KEYS:
        return raw_page
    return DEFAULT_PAGE


def current_page_key() -> str:
    raw_page = st.query_params.get("page", DEFAULT_PAGE)
    if isinstance(raw_page, list):
        raw_page = raw_page[0] if raw_page else DEFAULT_PAGE
    return resolve_page(raw_page)


def main() -> None:
    inject_css()
    db = load_db()
    active_page = current_page_key()
    if active_page == "history":
        history_page(db)
    elif active_page == "calories":
        calorie_table_page(db)
    elif active_page == "stats":
        stats_page(db)
    else:
        recognition_page(db)


if __name__ == "__main__":
    main()
