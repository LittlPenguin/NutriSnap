from __future__ import annotations

from html import escape
from io import BytesIO

import pandas as pd
import streamlit as st
from PIL import Image, UnidentifiedImageError

from services.calorie_service import CalorieService
from services.gpt_advice_service import mask_api_key, resolve_openai_settings, stream_model_advice
from services.predictor import predict_image
from services.schemas import USER_GOALS
from services.stats_service import get_food_ranking
from ui.components import (
    bottom_nav,
    brand_header,
    calorie_result_card,
    estimate_boundary_card,
    food_calorie_card,
    history_record_card,
    metric_grid,
    page_title,
    ranking_row,
    status_card,
    top3_progress,
    upload_state_card,
    workflow_state_strip,
)

OPENAI_SESSION_CONFIG_KEY = "openai_session_config"
LATEST_IMAGE_BYTES_KEY = "latest_uploaded_image_bytes"
LATEST_IMAGE_NAME_KEY = "latest_uploaded_image_name"


def read_uploaded_image(uploaded_file) -> Image.Image | None:
    if uploaded_file is None:
        return None
    try:
        return Image.open(BytesIO(uploaded_file.getvalue())).convert("RGB")
    except (UnidentifiedImageError, OSError):
        st.error("图片读取失败，请上传 jpg、jpeg 或 png 格式文件。")
        return None


def confidence_text(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{float(value) * 100:.1f}%"


def _format_time(value: str | None) -> str:
    if not value:
        return "-"
    return value.replace("T", " ")


def get_openai_session_config() -> dict[str, str]:
    value = st.session_state.get(OPENAI_SESSION_CONFIG_KEY)
    return dict(value) if isinstance(value, dict) else {}


def render_openai_config_panel() -> dict[str, str]:
    session_config = get_openai_session_config()
    settings = resolve_openai_settings(session_config)
    source_text = {
        "session": "页面配置",
        "env": ".env 配置",
        "default": "默认配置",
    }.get(settings.source, settings.source)
    if not settings.has_api_key:
        source_status = "当前未配置 API Key，Model 建议将显示失败原因"
    else:
        source_status = f"当前使用：{source_text} · Key {mask_api_key(settings.api_key)}"

    with st.expander("Model 配置", expanded=False):
        st.markdown(
            f"""
            <div class="result-card advice-card">
              <strong>OpenAI 建议配置</strong><br>
              <span class="small-label">{escape(source_status)}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        base_url_input = st.text_input(
            "OpenAI Base URL",
            value=settings.base_url or "",
            placeholder="例如：https://api.openai.com/v1",
            key="openai_base_url_input",
        )
        api_key_input = st.text_input(
            "OpenAI API Key",
            value="",
            placeholder="留空则继续使用 .env 中的 Key；输入后仅保存到本次会话",
            type="password",
            key="openai_api_key_input",
        )
        model_input = st.text_input(
            "OpenAI Model",
            value=settings.model or "gpt-5",
            placeholder="例如：gpt-5",
            key="openai_model_input",
        )
        save_col, clear_col = st.columns(2)
        with save_col:
            if st.button("保存到本次会话", key="save_openai_session_config"):
                next_config = {
                    "base_url": base_url_input.strip(),
                    "model": model_input.strip() or "gpt-5",
                }
                if api_key_input.strip():
                    next_config["api_key"] = api_key_input.strip()
                elif session_config.get("api_key"):
                    next_config["api_key"] = session_config["api_key"]
                st.session_state[OPENAI_SESSION_CONFIG_KEY] = next_config
                st.rerun()
        with clear_col:
            if st.button("清除页面配置，恢复 .env", key="clear_openai_session_config"):
                st.session_state.pop(OPENAI_SESSION_CONFIG_KEY, None)
                st.rerun()

        st.caption("API Key 仅保存到当前 Streamlit 会话，不写入数据库、.env、日志或 Git。")

    return get_openai_session_config()


def render_prediction(prediction: dict) -> None:
    if prediction.get("status") in {"model_missing", "error"}:
        status_card(
            "模型未加载",
            prediction.get("message", "请先训练模型，或将 NUTRISNAP_DEMO_MODE=true 用于课程演示。"),
        )
        return

    status_label = "演示结果" if prediction.get("status") == "demo" else "识别结果"
    st.markdown(
        f"""
        <div class="result-card">
          <div class="result-row">
            <div>
              <div class="small-label">{status_label}</div>
              <h3 style="margin:4px 0 0">{prediction["predicted_name_cn"]}</h3>
            </div>
            <span class="tag primary">置信度 {confidence_text(prediction["confidence"])}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    top3 = prediction.get("top3", [])
    if top3:
        st.markdown(
            f'<div class="result-card"><strong>Top-3 预测</strong>{top3_progress(top3)}</div>',
            unsafe_allow_html=True,
        )


def render_model_advice_stream(
    calorie_result: dict,
    user_goal: str,
    openai_config: dict[str, str],
) -> dict[str, str]:
    status_placeholder = st.empty()
    advice_placeholder = st.empty()
    workflow_state_strip("Model 生成中")
    status_placeholder.markdown(
        (
            '<div class="result-card advice-card"><strong>Model 生成中</strong><br>'
            '<span class="small-label">正在流式生成建议...</span></div>'
        ),
        unsafe_allow_html=True,
    )

    chunks: list[str] = []
    for event in stream_model_advice(
        calorie_result["name_cn"],
        calorie_result["weight_g"],
        calorie_result["total_calorie"],
        user_goal,
        settings=openai_config,
    ):
        event_type = event.get("type")
        if event_type == "delta":
            chunks.append(event.get("text", ""))
            advice_placeholder.markdown(
                f"""
                <div class="result-card advice-card">
                  <strong>Model 饮食建议</strong><br>
                  {escape("".join(chunks))}
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif event_type == "done":
            final_text = event.get("text") or "".join(chunks)
            status_placeholder.markdown(
                (
                    '<div class="result-card advice-card"><strong>生成完毕</strong><br>'
                    '<span class="small-label">Model 建议已完成。</span></div>'
                ),
                unsafe_allow_html=True,
            )
            advice_placeholder.markdown(
                f"""
                <div class="result-card advice-card">
                  <strong>Model 饮食建议</strong><br>
                  {escape(final_text)}
                </div>
                """,
                unsafe_allow_html=True,
            )
            workflow_state_strip("生成完毕")
            return {"status": "success", "advice": final_text}
        elif event_type == "error":
            reason = event.get("reason", "未知错误")
            fallback = event.get("fallback", "")
            status_placeholder.markdown(
                f"""
                <div class="result-card warning-card">
                  <strong>失败：{escape(reason)}</strong><br>
                  <span class="small-label">已显示降级建议内容。</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            advice_placeholder.markdown(
                f"""
                <div class="result-card warning-card">
                  <strong>失败降级建议</strong><br>
                  {escape(fallback)}
                </div>
                """,
                unsafe_allow_html=True,
            )
            workflow_state_strip("失败：")
            return {"status": "error", "advice": fallback, "error_reason": reason}

    reason = "empty streaming response"
    fallback = (
        "Model 调用失败，本地规则建议："
        f"{calorie_result['name_cn']}{calorie_result['weight_g']}g "
        f"估算约 {calorie_result['total_calorie']} kcal。不作为医学或营养诊断。"
    )
    status_placeholder.markdown(
        f'<div class="result-card warning-card"><strong>失败：{reason}</strong></div>',
        unsafe_allow_html=True,
    )
    workflow_state_strip("失败：")
    return {"status": "error", "advice": fallback, "error_reason": reason}


def recognition_page(db) -> None:
    brand_header("今天也记一餐", "食物识别")
    page_title("食物识别工作台", "上传图片、查看识别结果，输入重量后估算热量并生成饮食建议。", "估算热量")
    history = db.list_history()
    today = pd.Timestamp.now().strftime("%Y-%m-%d")
    today_rows = [row for row in history if str(row["created_at"]).startswith(today)]
    today_calorie = sum(float(row["total_calorie"]) for row in today_rows)
    metric_grid(
        [
            ("今日已记录", f"{len(today_rows)} 次", "来自 SQLite 识别历史"),
            ("今日估算", f"{today_calorie:.0f} kcal", "热量为估算值"),
            ("支持格式", "jpg / png", "手机端可拍照或相册上传"),
            ("建议模式", "Model 流式", "失败时显示原因"),
        ]
    )

    left, right = st.columns([1, 1], gap="large")
    with left:
        st.markdown(
            """
            <div class="result-card">
              <div class="result-row">
                <div>
                  <strong>上传食物图片</strong><br>
                  <span class="small-label">支持 PC 文件选择、移动端拍照 / 相册上传</span>
                </div>
                <span class="tag primary">图片预览</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        uploaded_file = st.file_uploader(
            "支持拍照或从相册选择",
            type=["jpg", "jpeg", "png"],
            label_visibility="visible",
        )
        image = read_uploaded_image(uploaded_file)
        upload_state_card(image is not None, uploaded_file.name if uploaded_file else None)
        if image is not None:
            st.session_state[LATEST_IMAGE_BYTES_KEY] = uploaded_file.getvalue()
            st.session_state[LATEST_IMAGE_NAME_KEY] = uploaded_file.name
            st.image(image, caption=uploaded_file.name, use_container_width=True)
            st.markdown(
                '<div class="preview-meta"><span>已上传预览</span><span>仅用于本地识别</span></div>',
                unsafe_allow_html=True,
            )
        else:
            workflow_state_strip("未上传")

    with right:
        st.markdown(
            """
            <div class="result-card">
              <div class="result-row">
                <div>
                  <strong>识别结果与估算</strong><br>
                  <span class="small-label">ResNet18 输出类别、置信度和 Top-3</span>
                </div>
                <span class="tag primary">工作台</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        openai_config = render_openai_config_panel()
        if "prediction" not in st.session_state:
            st.session_state.prediction = None
        if "calorie_result" not in st.session_state:
            st.session_state.calorie_result = None
        if "advice_result" not in st.session_state:
            st.session_state.advice_result = None

        if st.button("开始识别", disabled=image is None):
            with st.spinner("正在识别食物类别..."):
                st.session_state.prediction = predict_image(image)
                st.session_state.calorie_result = None
                st.session_state.advice_result = None

        prediction = st.session_state.prediction
        if prediction:
            workflow_state_strip("识别完成")
            render_prediction(prediction)

        foods = {food["class_name"]: food for food in db.list_foods()}
        can_calculate = prediction and prediction.get("predicted_class") in foods
        default_weight = 100
        if can_calculate:
            default_weight = int(foods[prediction["predicted_class"]]["default_weight_g"])

        weight_g = st.number_input("本次份量（g）", min_value=1, max_value=3000, value=default_weight, step=10)
        st.markdown(
            f"""
            <div class="result-card">
              <div class="input-line">
                <div><strong>本次份量</strong><div class="input-like">{int(weight_g)}</div></div>
                <span class="tag">g</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        user_goal = st.segmented_control("用户目标", USER_GOALS, default="普通饮食")

        if st.button("计算热量并生成建议", disabled=not can_calculate):
            calorie_service = CalorieService(db)
            calorie_result = calorie_service.calculate_calorie(prediction["predicted_class"], weight_g)
            advice_result = render_model_advice_stream(calorie_result, user_goal, openai_config)
            history_id = db.save_history(
                {
                    "image_name": uploaded_file.name if uploaded_file else "",
                    "predicted_class": prediction["predicted_class"],
                    "predicted_name_cn": prediction["predicted_name_cn"],
                    "confidence": prediction.get("confidence"),
                    "weight_g": calorie_result["weight_g"],
                    "calorie_per_100g": calorie_result["calorie_per_100g"],
                    "total_calorie": calorie_result["total_calorie"],
                    "gpt_advice": advice_result["advice"],
                }
            )
            db.save_gpt_advice_log(
                {
                    "history_id": history_id,
                    "user_goal": user_goal,
                    "prompt_summary": (
                        f"{calorie_result['name_cn']} {calorie_result['weight_g']}g "
                        f"{calorie_result['total_calorie']}kcal"
                    ),
                    "advice": advice_result["advice"],
                    "status": advice_result["status"],
                }
            )
            st.session_state.calorie_result = calorie_result
            st.session_state.advice_result = advice_result

        calorie_result = st.session_state.calorie_result
        advice_result = st.session_state.advice_result
        if calorie_result:
            calorie_result_card(str(calorie_result["total_calorie"]), str(calorie_result["calorie_per_100g"]))
        if advice_result:
            status = (
                "Model 饮食建议"
                if advice_result["status"] == "success"
                else f"失败：{advice_result.get('error_reason', '未知错误')}"
            )
            workflow_state_strip("生成完毕" if advice_result["status"] == "success" else "失败：")
            st.markdown(
                f"""
                <div class="result-card advice-card">
                  <strong>{escape(status)}</strong><br>
                  {escape(advice_result["advice"])}
                </div>
                """,
                unsafe_allow_html=True,
            )
    bottom_nav("食物识别")


def history_page(db) -> None:
    brand_header("识别历史与建议摘要", "历史记录")
    page_title("历史记录", "按时间倒序查看饮食记录，移动端使用卡片，PC 端保留宽屏表格。")
    history = db.list_history()
    today = pd.Timestamp.now().strftime("%Y-%m-%d")
    today_rows = [row for row in history if str(row["created_at"]).startswith(today)]
    today_calorie = sum(float(row["total_calorie"]) for row in today_rows)
    metric_grid(
        [
            ("今日记录", f"{len(today_rows)} 次", "今天保存的识别历史"),
            ("今日估算", f"{today_calorie:.0f} kcal", "仅供饮食记录参考"),
            ("累计记录", f"{len(history)} 次", "按时间倒序展示"),
            ("建议摘要", f"{len(history)} 条", "随识别历史保存"),
        ]
    )

    if not history:
        status_card("暂无历史记录", "完成一次识别和热量估算后会自动保存到 SQLite。", "info")
        st.markdown(
            """
            <div class="result-card">
              <div class="result-row">
                <div>
                  <strong>历史记录列表</strong>
                  <div class="small-label">移动端对应紧凑卡片列表，PC 端下方提供宽屏表格。</div>
                </div>
                <span class="tag primary">最近 0 条</span>
              </div>
              <div class="history-list">
                <div class="history-row">
                  <div>
                    <strong>暂无记录</strong>
                    <span>完成一次识别、热量估算和建议生成后会显示在这里。</span>
                  </div>
                  <b class="kcal-small">0 kcal</b>
                </div>
              </div>
            </div>
            <div class="result-card">
              <div class="result-row">
                <strong>PC 历史记录页表格</strong>
                <span class="tag">按时间倒序</span>
              </div>
              <div class="desktop-table">
                <div class="table-row table-head">
                  <span>食物</span><span>重量</span><span>估算热量</span><span>置信度</span><span>Model 建议摘要</span>
                </div>
                <div class="table-row">
                  <span>暂无记录</span><span>-</span><span>-</span><span>-</span><span>完成识别后自动保存</span>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        bottom_nav("历史记录")
        return

    st.markdown(
        f"""
        <div class="result-card">
          <div class="result-row">
            <div>
              <strong>历史记录列表</strong>
              <div class="small-label">移动端对应紧凑卡片列表，PC 端下方提供宽屏表格。</div>
            </div>
            <span class="tag primary">最近 {min(len(history), 8)} 条</span>
          </div>
          <div class="history-list">{"".join(history_record_card(row) for row in history[:8])}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    table_rows = []
    for row in history[:12]:
        table_rows.append(
            f"""
            <div class="table-row">
              <span>{escape(str(row["predicted_name_cn"]))}</span>
              <span>{float(row["weight_g"]):.0f}g</span>
              <span>{float(row["total_calorie"]):.0f} kcal</span>
              <span>{confidence_text(row.get("confidence"))}</span>
              <span>{escape(str(row.get("gpt_advice", "") or "暂无建议摘要"))}</span>
            </div>
            """
        )
    st.markdown(
        f"""
        <div class="result-card">
          <div class="result-row">
            <strong>PC 历史记录页表格</strong>
            <span class="tag">按时间倒序</span>
          </div>
          <div class="desktop-table">
            <div class="table-row table-head">
              <span>食物</span><span>重量</span><span>估算热量</span><span>置信度</span><span>Model 建议摘要</span>
            </div>
            {"".join(table_rows)}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    bottom_nav("历史记录")


def calorie_table_page(db) -> None:
    brand_header("Food-101 子集热量参考", "热量表")
    page_title("食物热量表", "查询系统支持食物类别的每 100g 热量和默认份量。", "SQLite food_calorie")
    all_foods = db.list_foods()
    metric_grid(
        [
            ("支持类别", f"{len(all_foods)} 类", "Food-101 一期子集"),
            ("设计示例", "399 kcal", "150g × 266 kcal / 100g"),
            ("默认份量", "150g", "可在识别页修改"),
            ("数据来源", "SQLite", "food_calorie 表"),
        ]
    )
    query_col, category_col = st.columns([2, 1])
    with query_col:
        query = st.text_input("搜索食物名称", placeholder="例如：披萨 / pizza")
    with category_col:
        category = st.selectbox("分类筛选", ["全部", "主食", "快餐", "甜点", "肉类", "沙拉"])

    foods = db.list_foods(category=category, query=query)
    if not foods:
        st.info("没有找到匹配的食物。")
        estimate_boundary_card(
            "热量表边界说明",
            "当前只覆盖 Food-101 子集中的 12 类食物，未匹配类别需要后续补充热量数据。",
        )
        bottom_nav("热量表")
        return
    st.markdown(
        f"""
        <div class="result-card">
          <div class="result-row">
            <div>
              <strong>Food-101 子集参考数据</strong>
              <div class="small-label">展示中文名、英文类名、分类、每 100g 热量和默认份量。</div>
            </div>
            <span class="tag primary">匹配 {len(foods)} 项</span>
          </div>
          <div class="food-grid">{"".join(food_calorie_card(row) for row in foods)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    estimate_boundary_card(
        "热量表边界说明",
        "热量值来自预置参考表，会因品牌、烹饪方式和配料不同产生误差；结果只用于估算热量。",
    )
    bottom_nav("热量表")


def stats_page(db) -> None:
    brand_header("估算摄入趋势与常见食物", "统计分析")
    page_title("统计分析", "查看记录次数、累计热量、今日热量、最新上传食物图和常见食物排行。", "趋势参考")
    history = db.list_history()
    total_records = len(history)
    total_calorie = sum(float(row["total_calorie"]) for row in history)
    today = pd.Timestamp.now().strftime("%Y-%m-%d")
    today_calorie = sum(float(row["total_calorie"]) for row in history if str(row["created_at"]).startswith(today))
    avg_calorie = total_calorie / total_records if total_records else 0
    metric_grid(
        [
            ("累计记录", f"{total_records} 次", "所有识别历史"),
            ("累计热量", f"{total_calorie:.0f} kcal", "估算值汇总"),
            ("今日热量", f"{today_calorie:.0f} kcal", "今天记录合计"),
            ("单次平均", f"{avg_calorie:.0f} kcal", "按历史记录估算"),
        ]
    )

    st.markdown(
        """
        <div class="result-card">
          <div class="result-row">
            <strong>最新上传食物图</strong>
            <span class="tag primary">当前会话</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    latest_image = st.session_state.get(LATEST_IMAGE_BYTES_KEY)
    if latest_image:
        st.image(
            latest_image,
            caption=st.session_state.get(LATEST_IMAGE_NAME_KEY, "最新上传食物图"),
            use_container_width=True,
        )
    else:
        st.info("暂无上传图片")

    ranking = get_food_ranking(db)
    if ranking.empty:
        status_card("常见食物排行", "暂无排行数据，完成识别记录后会按出现次数生成排行。", "info")
    else:
        ranking_cards = "".join(
            ranking_row(
                str(row["predicted_name_cn"]),
                int(row["count"]),
                float(row["total_calorie"]),
                "最近 7 日 / 全部历史",
            )
            for row in ranking.to_dict("records")
        )
        st.markdown(
            f"""
            <div class="result-card">
              <div class="result-row">
                <strong>常见食物排行</strong>
                <span class="tag primary">按次数排序</span>
              </div>
              <div class="rank-list">{ranking_cards}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    estimate_boundary_card(
        "说明",
        "基于识别历史中的估算热量，不作为医学或营养诊断。",
    )
    bottom_nav("统计分析")
