from __future__ import annotations

import streamlit as st

from services.database import get_database
from ui.pages import (
    about_page,
    calorie_table_page,
    history_page,
    recognition_page,
    stats_page,
)
from ui.styles import inject_css

PAGE_LABELS = ["食物识别", "历史记录", "热量表", "统计分析", "系统说明"]


st.set_page_config(
    page_title="NutriSnap 轻食记录",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_resource
def load_db():
    return get_database()


def main() -> None:
    inject_css()
    db = load_db()
    tabs = st.tabs(PAGE_LABELS)
    with tabs[0]:
        recognition_page(db)
    with tabs[1]:
        history_page(db)
    with tabs[2]:
        calorie_table_page(db)
    with tabs[3]:
        stats_page(db)
    with tabs[4]:
        about_page()


if __name__ == "__main__":
    main()
