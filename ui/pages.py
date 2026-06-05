from __future__ import annotations

from html import escape
from io import BytesIO

import pandas as pd
import streamlit as st
from PIL import Image, UnidentifiedImageError

from services.calorie_service import CalorieService
from services.gpt_advice_service import generate_gpt_advice
from services.predictor import predict_image
from services.schemas import USER_GOALS
from services.stats_service import get_daily_stats, get_food_ranking
from ui.components import (
    bottom_nav,
    brand_header,
    calorie_result_card,
    daily_bar_chart,
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
            ("建议模式", "GPT / 本地规则", "失败时自动降级"),
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
            workflow_state_strip("GPT 生成中")
            with st.spinner("正在生成 GPT 饮食建议..."):
                advice_result = generate_gpt_advice(
                    calorie_result["name_cn"],
                    calorie_result["weight_g"],
                    calorie_result["total_calorie"],
                    user_goal,
                )
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
            status = "GPT 饮食建议" if advice_result["status"] == "success" else "本地规则建议"
            workflow_state_strip("GPT 建议完成" if advice_result["status"] == "success" else "本地规则建议")
            st.markdown(
                f"""
                <div class="result-card advice-card">
                  <strong>{status}</strong><br>
                  {advice_result["advice"]}
                </div>
                """,
                unsafe_allow_html=True,
            )
    bottom_nav("食物识别")


def history_page(db) -> None:
    brand_header("识别历史与建议摘要", "历史记录")
    page_title("历史记录", "按时间倒序查看饮食记录，移动端使用卡片，PC 端保留宽屏表格。", "含 GPT 失败降级提示", "warn")
    history = db.list_history()
    advice_logs = db.list_gpt_advice_logs()
    today = pd.Timestamp.now().strftime("%Y-%m-%d")
    today_rows = [row for row in history if str(row["created_at"]).startswith(today)]
    today_calorie = sum(float(row["total_calorie"]) for row in today_rows)
    fallback_count = sum(1 for row in advice_logs if row.get("status") in {"fallback", "error"})
    metric_grid(
        [
            ("今日记录", f"{len(today_rows)} 次", "今天保存的识别历史"),
            ("今日估算", f"{today_calorie:.0f} kcal", "仅供饮食记录参考"),
            ("累计记录", f"{len(history)} 次", "按时间倒序展示"),
            ("降级建议", f"{fallback_count} 条", "GPT 失败时使用本地规则建议"),
        ]
    )

    if not history:
        status_card("暂无历史记录", "完成一次识别和热量估算后会自动保存到 SQLite。", "info")
        estimate_boundary_card(
            "GPT 失败降级",
            "API key 未配置、网络失败或超时时，系统仍会展示本地规则建议，并在日志中记录 fallback 或 error。",
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
              <span>食物</span><span>重量</span><span>估算热量</span><span>置信度</span><span>GPT 建议摘要</span>
            </div>
            {"".join(table_rows)}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    estimate_boundary_card(
        "本地规则建议",
        "当 GPT API key 未配置、网络失败或响应超时时，系统仍保存历史记录，并展示本地规则建议。",
    )
    bottom_nav("历史记录")


def calorie_table_page(db) -> None:
    brand_header("Food-101 子集热量参考", "热量表")
    page_title("食物热量表", "查询系统支持食物类别的每 100g 热量和默认份量。", "SQLite food_calorie")
    all_foods = db.list_foods()
    metric_grid(
        [
            ("支持类别", f"{len(all_foods)} 类", "Food-101 一期子集"),
            ("设计示例", "266 kcal / 100g", "披萨热量口径"),
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
    page_title("统计分析", "查看记录次数、累计热量、今日热量、近 7 日估算热量和常见食物排行。", "趋势参考")
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

    daily_stats = get_daily_stats(db)
    if daily_stats.empty:
        st.markdown(daily_bar_chart([]), unsafe_allow_html=True)
    else:
        chart_rows = []
        for row in daily_stats.to_dict("records"):
            row = dict(row)
            if row["date"] == today:
                row["label"] = "今天"
            chart_rows.append(row)
        st.markdown(daily_bar_chart(chart_rows), unsafe_allow_html=True)

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
        "结果边界说明",
        "统计分析基于识别历史中的估算热量，不代表真实摄入精确值，也不作为医学或营养诊断。",
    )
    bottom_nav("统计分析")


def about_page() -> None:
    brand_header("项目说明与功能边界", "系统说明")
    page_title("系统说明", "说明项目目标、使用步骤和功能限制。", "不作为医学或营养诊断", "warn")
    st.markdown(
        """
        <div class="result-card">
          本系统通过食物图像识别和热量表估算，为用户提供日常饮食记录参考。
          用户上传食物图片后，可查看识别结果、输入食物重量、获得估算热量和饮食建议。
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.subheader("使用步骤")
    st.markdown(
        """
        1. 上传食物图片。
        2. 查看识别结果和 Top-3 预测。
        3. 输入本次食物重量。
        4. 查看估算热量。
        5. 选择用户目标并生成饮食建议。
        """
    )
    st.subheader("注意事项")
    st.markdown(
        """
        - 热量通过“食物类别 + 重量 + 每 100g 热量表”估算。
        - 系统不会仅凭图片自动精确估重。
        - 估算热量仅供饮食记录参考。
        - 本系统不作为医学或营养诊断，也不提供治疗建议。
        """
    )
    bottom_nav("系统说明")
