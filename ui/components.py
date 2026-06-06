from __future__ import annotations

from collections.abc import Iterable
from html import escape

import streamlit as st

PAGE_ITEMS = [
    ("食物识别", "recognition", "图", "识别"),
    ("历史记录", "history", "时", "历史"),
    ("热量表", "calories", "表", "热量表"),
    ("统计分析", "stats", "柱", "统计"),
]


def page_key(label: str) -> str:
    for item_label, key, _, _ in PAGE_ITEMS:
        if item_label == label:
            return key
    return PAGE_ITEMS[0][1]


def _active_key(active_page: str | None) -> str:
    if not active_page:
        return PAGE_ITEMS[0][1]
    keys = {key for _, key, _, _ in PAGE_ITEMS}
    if active_page in keys:
        return active_page
    return page_key(active_page)


def _label_for_key(page: str, mobile: bool = False) -> str:
    for label, key, icon, short in PAGE_ITEMS:
        if key == page:
            return f"{icon} {short}" if mobile else label
    return page


def _switch_page(selected_page: str | None, active_page: str | None) -> None:
    active_key = _active_key(active_page)
    if selected_page and selected_page != active_key:
        st.query_params["page"] = selected_page
        st.rerun()


def brand_header(subtitle: str, active_page: str | None = None) -> None:
    active_key = _active_key(active_page)
    st.markdown(
        f"""
        <header class="desktop-top">
          <div class="brand-lockup">
            <div class="brand-mark">N</div>
            <div>
              <strong>NutriSnap 轻食记录</strong>
              <p class="muted" style="font-size:12px;margin:2px 0 0">{escape(subtitle)}</p>
            </div>
          </div>
          <div class="desktop-nav active">{escape(_label_for_key(active_key))}</div>
        </header>
        """,
        unsafe_allow_html=True,
    )
    with st.container(key=f"desktop_nav_container_{active_key}"):
        selected_page = st.pills(
            "页面导航",
            [key for _, key, _, _ in PAGE_ITEMS],
            default=active_key,
            format_func=lambda page: _label_for_key(str(page)),
            key=f"desktop_nav_{active_key}",
            label_visibility="collapsed",
            width="content",
        )
    _switch_page(str(selected_page) if selected_page else None, active_key)


def page_title(title: str, description: str, tag: str | None = None, tag_kind: str = "primary") -> None:
    tag_html = f'<span class="tag {tag_kind}">{escape(tag)}</span>' if tag else ""
    st.markdown(
        f"""
        <div class="page-title result-row" style="margin:14px 0 16px">
          <div>
            <h2>{escape(title)}</h2>
            <p style="margin:4px 0 0">{escape(description)}</p>
          </div>
          {tag_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def bottom_nav(active_page: str) -> None:
    active_key = _active_key(active_page)
    with st.container(key=f"bottom_nav_container_{active_key}"):
        st.markdown(
            '<span class="bottom-nav mobile-nav-grid nav-item active" aria-hidden="true">移动端底部导航</span>',
            unsafe_allow_html=True,
        )
        columns = st.columns(4)
        selected_page = None
        for column, (_, key, _, _) in zip(columns, PAGE_ITEMS, strict=True):
            with column:
                button_key = f"mobile_nav_button_{'active' if key == active_key else 'idle'}_{active_key}_{key}"
                if st.button(
                    _label_for_key(key, mobile=True),
                    key=button_key,
                    use_container_width=True,
                    type="primary" if key == active_key else "secondary",
                ):
                    selected_page = key
    _switch_page(selected_page, active_key)


def card(content: str, class_name: str = "") -> None:
    st.markdown(f'<div class="nutri-card {class_name}">{content}</div>', unsafe_allow_html=True)


def metric_card(label: str, value: str, helper: str | None = None) -> str:
    helper_html = f'<span>{escape(helper)}</span>' if helper else ""
    return f'<div class="desktop-stat"><span>{escape(label)}</span><strong>{escape(value)}</strong>{helper_html}</div>'


def metric_grid(metrics: Iterable[tuple[str, str, str | None]]) -> None:
    cards = "".join(metric_card(label, value, helper) for label, value, helper in metrics)
    st.markdown(f'<div class="desktop-metrics">{cards}</div>', unsafe_allow_html=True)


def top3_progress(items: Iterable[dict]) -> str:
    rows = []
    for item in items:
        confidence = float(item.get("confidence", 0))
        percent = round(confidence * 100)
        rows.append(
            f"""
            <div class="progress-item">
              <span>{escape(str(item.get("name_cn", item.get("class_name", "-"))))}</span>
              <div class="bar"><span style="width:{percent}%"></span></div>
              <b>{percent}%</b>
            </div>
            """
        )
    return f'<div class="progress-list">{"".join(rows)}</div>'


def calorie_result_card(total_calorie: str, per_100g: str) -> None:
    st.markdown(
        f"""
        <div class="result-card advice-card">
          <div class="small-label">估算热量</div>
          <div class="calorie-number">{escape(total_calorie)} kcal</div>
          <p>每 100g 约 {escape(per_100g)} kcal / 100g</p>
          <span class="small-label">热量为估算值，仅供饮食记录参考。</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_card(title: str, body: str, kind: str = "warning") -> None:
    class_name = "warning-card" if kind == "warning" else "advice-card"
    st.markdown(
        f"""
        <div class="result-card {class_name}">
          <strong>{escape(title)}</strong><br>
          <span class="muted">{escape(body)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def upload_state_card(has_image: bool, filename: str | None = None) -> None:
    if has_image:
        title = "已上传预览"
        body = filename or "图片已读取"
        helper = "图片用于本地模型识别，Model 建议不接收原图。"
        tag = '<span class="tag primary">已上传</span>'
    else:
        title = "未上传状态"
        body = "拍照 / 相册 · 支持 jpg、jpeg、png"
        helper = "上传后可查看预览并开始识别。"
        tag = '<span class="tag warn">待上传</span>'
    st.markdown(
        f"""
        <div class="upload-box">
          <div>
            <div class="result-row" style="justify-content:center">
              <strong>{escape(title)}</strong>{tag}
            </div>
            <p style="margin:8px 0 4px">{escape(body)}</p>
            <span class="small-label">{escape(helper)}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def workflow_state_strip(active: str) -> None:
    states = [
        ("未上传", "上传框默认状态"),
        ("已上传预览", "图片预览"),
        ("识别完成", "类别、置信度、Top-3"),
        ("Model 生成中", "加载状态"),
        ("生成完毕", "中文建议卡片"),
        ("失败：", "显示错误原因"),
    ]
    items = []
    for title, body in states:
        class_name = "state-item advice-card" if title == active else "state-item"
        marker = '<i class="loading-line"></i>' if title == "Model 生成中" and active == title else escape(body)
        items.append(f'<div class="{class_name}"><strong>{escape(title)}</strong><span>{marker}</span></div>')
    st.markdown(f'<div class="state-strip">{"".join(items)}</div>', unsafe_allow_html=True)


def history_record_card(record: dict) -> str:
    food_name = escape(str(record.get("predicted_name_cn", "-")))
    weight = float(record.get("weight_g", 0) or 0)
    calorie = float(record.get("total_calorie", 0) or 0)
    confidence = record.get("confidence")
    confidence_text = "-" if confidence is None else f"{float(confidence) * 100:.1f}%"
    created_at = escape(str(record.get("created_at", "-")).replace("T", " "))
    advice = escape(str(record.get("gpt_advice", "暂无建议摘要") or "暂无建议摘要"))
    return f"""
    <div class="history-row">
      <div>
        <strong>{food_name}</strong>
        <span>{weight:.0f}g · 置信度 {escape(confidence_text)} · {created_at}</span>
        <small>{advice}</small>
      </div>
      <b class="kcal-small">{calorie:.0f} kcal</b>
    </div>
    """


def food_calorie_card(food: dict) -> str:
    name_cn = escape(str(food.get("name_cn", "-")))
    class_name = escape(str(food.get("class_name", "-")))
    category = escape(str(food.get("category", "-")))
    calorie = float(food.get("calorie_per_100g", 0) or 0)
    weight = float(food.get("default_weight_g", 0) or 0)
    note = escape(str(food.get("note", "") or "热量会因品牌、配料和做法变化。"))
    return f"""
    <div class="food-row">
      <div>
        <strong>{name_cn}</strong>
        <span>{class_name} · {category}</span>
        <small>{note}</small>
      </div>
      <div class="food-kcal">
        <b>{calorie:.0f} kcal / 100g</b>
        <span>默认份量 {weight:.0f}g</span>
      </div>
    </div>
    """


def ranking_row(name: str, count: int, total_calorie: float | None = None, meta: str | None = None) -> str:
    helper = meta or "最近记录"
    calorie_html = f'<span>{float(total_calorie):.0f} kcal</span>' if total_calorie is not None else ""
    return f"""
    <div class="rank-row">
      <div>
        <strong>{escape(name)}</strong>
        <span>{escape(helper)}</span>
      </div>
      <b class="kcal-small">{int(count)} 次</b>
      {calorie_html}
    </div>
    """


def estimate_boundary_card(title: str, body: str, kind: str = "warning") -> None:
    class_name = "warning-card" if kind == "warning" else "advice-card"
    st.markdown(
        f"""
        <div class="result-card boundary-card {class_name}">
          <strong>{escape(title)}</strong>
          <p>{escape(body)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def daily_bar_chart(rows: Iterable[dict], highlight_label: str = "今天") -> str:
    row_list = list(rows)
    if not row_list:
        return """
        <div class="chart-shell">
          <strong>估算热量参考</strong>
          <div class="upload-box" style="min-height:120px">
            暂无统计数据，完成一次识别后生成柱状图。
          </div>
        </div>
        """

    max_value = max(float(row.get("total_calorie", 0) or 0) for row in row_list) or 1
    bars = []
    for row in row_list:
        label = escape(str(row.get("date", "-"))[-5:])
        value = float(row.get("total_calorie", 0) or 0)
        height = max(18, round(value / max_value * 150))
        class_name = "chart-bar today" if row.get("label") == highlight_label else "chart-bar"
        bars.append(
            f"""
            <div class="{class_name}">
              <i style="height:{height}px"></i>
              <span>{label}</span>
              <b>{value:.0f}</b>
            </div>
            """
        )
    return f"""
    <div class="chart-shell">
      <div class="result-row">
        <strong>估算热量参考</strong>
        <span class="tag warn">仅供饮食记录参考</span>
      </div>
      <div class="chart-bars">{"".join(bars)}</div>
    </div>
    """
