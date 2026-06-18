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

# 四个页面的内部 key，用于 URL 参数路由
PAGE_KEYS = {"recognition", "history", "calories", "stats"}
# 默认页面 key
DEFAULT_PAGE = "recognition"

# 配置 Streamlit 页面标题、宽屏布局、默认收起侧边栏
st.set_page_config(
    page_title="NutriSnap 轻食记录",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_resource
def load_db():
    """缓存数据库实例，避免 Streamlit 每次 rerun 都重新初始化。"""
    return get_database()


def resolve_page(raw_page: str | None) -> str:
    """校验页面 key 是否合法，不合法则回退到默认页。"""
    if raw_page in PAGE_KEYS:
        return raw_page
    return DEFAULT_PAGE


def current_page_key() -> str:
    """从 URL 查询参数 ?page=xxx 中读取当前页面 key。"""
    raw_page = st.query_params.get("page", DEFAULT_PAGE)
    if isinstance(raw_page, list):
        raw_page = raw_page[0] if raw_page else DEFAULT_PAGE
    return resolve_page(raw_page)


def main() -> None:
    """应用入口：注入样式、初始化数据库、根据路由分发到对应页面函数。"""
    inject_css() #css
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
