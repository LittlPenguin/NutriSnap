from __future__ import annotations

from collections.abc import Iterable
from html import escape

import streamlit as st

# 四个导航项的配置元组：(显示标签, 路由 key, 移动端图标, 移动端短标签)
PAGE_ITEMS = [
    ("食物识别", "recognition", "图", "识别"),
    ("历史记录", "history", "时", "历史"),
    ("热量表", "calories", "表", "热量表"),
    ("统计分析", "stats", "柱", "统计"),
]


def page_key(label: str) -> str:
    """根据页面标签获取对应的路由 key。"""
    for item_label, key, _, _ in PAGE_ITEMS:
        if item_label == label:
            return key
    return PAGE_ITEMS[0][1]


def _active_key(active_page: str | None) -> str:
    """获取当前活跃页面的 key，无效则返回第一个。"""
    if not active_page:
        return PAGE_ITEMS[0][1]
    keys = {key for _, key, _, _ in PAGE_ITEMS}
    if active_page in keys:
        return active_page
    return page_key(active_page)


def _label_for_key(page: str, mobile: bool = False) -> str:
    """根据路由 key 获取显示标签，mobile=True 时返回带图标的短标签。"""
    for label, key, icon, short in PAGE_ITEMS:
        if key == page:
            return f"{icon} {short}" if mobile else label
    return page


def _switch_page(selected_page: str | None, active_page: str | None) -> None:
    """站内页面切换：更新 URL 参数并触发 Streamlit rerun。"""
    active_key = _active_key(active_page)
    if selected_page and selected_page != active_key:
        st.query_params["page"] = selected_page
        st.rerun()

def brand_header(subtitle: str, active_page: str | None = None) -> None:
    """渲染顶部品牌栏：NutriSnap 标识 + 副标题 + PC 端导航 pills。"""
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
    """渲染页面标题区域，包含标题、描述和可选标签。"""
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
    """渲染移动端底部固定导航栏（4 列按钮），隐藏 PC 端。"""
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


def metric_card(label: str, value: str, helper: str | None = None) -> str:
    """生成单个指标卡 HTML 字符串。"""
    helper_html = f'<span>{escape(helper)}</span>' if helper else ""
    return f'<div class="desktop-stat"><span>{escape(label)}</span><strong>{escape(value)}</strong>{helper_html}</div>'


def metric_grid(metrics: Iterable[tuple[str, str, str | None]]) -> None:
    """渲染一行多个指标卡（Grid 布局）。"""
    cards = "".join(metric_card(label, value, helper) for label, value, helper in metrics)
    st.markdown(f'<div class="desktop-metrics">{cards}</div>', unsafe_allow_html=True)


def top3_progress(items: Iterable[dict]) -> str:
    """生成 Top-3 预测结果的进度条 HTML，包含中文名和置信度百分比。"""
    rows = []
    for item in items:
        confidence = float(item.get("confidence", 0))
        percent = round(confidence * 100)
        label = escape(str(item.get("name_cn", item.get("class_name", "-"))))
        rows.append(
            f'<div class="progress-item"><span>{label}</span>'
            f'<div class="bar"><span style="width:{percent}%"></span></div>'
            f"<b>{percent}%</b></div>"
        )
    return f'<div class="progress-list">{"".join(rows)}</div>'


def calorie_result_card(total_calorie: str, per_100g: str) -> None:
    """渲染估算热量的结果卡片，包含总热量和每 100g 热量。"""
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
    """渲染状态提示卡片（警告或信息）。"""
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
    """渲染上传状态卡片，显示已上传或待上传。"""
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
    """渲染工作流状态条（6 个步骤，高亮当前所在步骤）。"""
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
    """生成单条历史记录卡片的 HTML。"""
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
    """生成热量表食物卡片的 HTML。"""
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
    """生成排行行 HTML，显示食物名称、次数和总热量。"""
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
    """渲染边界说明卡片（提示数据仅供参考）。"""
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

