from __future__ import annotations

from io import BytesIO

import pandas as pd
import streamlit as st
from PIL import Image, UnidentifiedImageError

from services.calorie_service import CalorieService
from services.gpt_advice_service import generate_gpt_advice
from services.predictor import predict_image
from services.schemas import USER_GOALS
from services.stats_service import get_daily_stats, get_food_ranking
from ui.components import bottom_nav, brand_header, calorie_result_card, page_title, status_card, top3_progress


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

    left, right = st.columns([1, 1], gap="large")
    with left:
        st.markdown('<div class="result-card"><strong>上传食物图片</strong>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "支持拍照或从相册选择",
            type=["jpg", "jpeg", "png"],
            label_visibility="visible",
        )
        image = read_uploaded_image(uploaded_file)
        if image is not None:
            st.image(image, caption=uploaded_file.name, use_container_width=True)
        else:
            st.info("上传图片后可查看预览并开始识别。")
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.subheader("识别与估算")
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
            render_prediction(prediction)

        foods = {food["class_name"]: food for food in db.list_foods()}
        can_calculate = prediction and prediction.get("predicted_class") in foods
        default_weight = 100
        if can_calculate:
            default_weight = int(foods[prediction["predicted_class"]]["default_weight_g"])

        weight_g = st.number_input("本次份量（g）", min_value=1, max_value=3000, value=default_weight, step=10)
        user_goal = st.segmented_control("用户目标", USER_GOALS, default="普通饮食")

        if st.button("计算热量并生成建议", disabled=not can_calculate):
            calorie_service = CalorieService(db)
            calorie_result = calorie_service.calculate_calorie(prediction["predicted_class"], weight_g)
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
    page_title("历史记录", "按时间倒序查看饮食记录。", "含 GPT 失败降级提示", "warn")
    history = db.list_history()
    today = pd.Timestamp.now().strftime("%Y-%m-%d")
    today_rows = [row for row in history if str(row["created_at"]).startswith(today)]
    c1, c2 = st.columns(2)
    c1.metric("今日记录", f"{len(today_rows)} 次")
    c2.metric("今日估算", f"{sum(float(row['total_calorie']) for row in today_rows):.0f} kcal")

    if not history:
        st.info("暂无历史记录。完成一次识别和热量估算后会自动保存。")
        bottom_nav("历史记录")
        return

    frame = pd.DataFrame(history)
    frame["置信度"] = frame["confidence"].map(confidence_text)
    frame = frame.rename(
        columns={
            "predicted_name_cn": "食物",
            "weight_g": "重量(g)",
            "total_calorie": "估算热量(kcal)",
            "gpt_advice": "建议摘要",
            "created_at": "时间",
        }
    )
    st.dataframe(
        frame[["食物", "重量(g)", "估算热量(kcal)", "置信度", "时间", "建议摘要"]],
        hide_index=True,
        use_container_width=True,
    )
    bottom_nav("历史记录")


def calorie_table_page(db) -> None:
    brand_header("Food-101 子集热量参考", "热量表")
    page_title("食物热量表", "查询系统支持食物类别的每 100g 热量和默认份量。", "SQLite food_calorie")
    query_col, category_col = st.columns([2, 1])
    with query_col:
        query = st.text_input("搜索食物名称", placeholder="例如：披萨 / pizza")
    with category_col:
        category = st.selectbox("分类筛选", ["全部", "主食", "快餐", "甜点", "肉类", "沙拉"])

    foods = db.list_foods(category=category, query=query)
    if not foods:
        st.info("没有找到匹配的食物。")
        bottom_nav("热量表")
        return
    for row in foods:
        st.markdown(
            f"""
            <div class="result-card">
              <strong>{row["name_cn"]}</strong>
              <span class="small-label"> · {row["class_name"]} · {row["category"]}</span><br>
              <span class="kcal-small">{row["calorie_per_100g"]:.0f} kcal / 100g</span>
              <span class="small-label">　默认份量 {row["default_weight_g"]:.0f}g</span><br>
              <span class="small-label">{row.get("note", "")}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    bottom_nav("热量表")


def stats_page(db) -> None:
    brand_header("估算摄入趋势与常见食物", "统计分析")
    page_title("统计分析", "查看记录次数、累计热量、今日热量和近 7 日趋势。", "趋势参考")
    history = db.list_history()
    total_records = len(history)
    total_calorie = sum(float(row["total_calorie"]) for row in history)
    today = pd.Timestamp.now().strftime("%Y-%m-%d")
    today_calorie = sum(float(row["total_calorie"]) for row in history if str(row["created_at"]).startswith(today))

    c1, c2, c3 = st.columns(3)
    c1.metric("累计记录", f"{total_records} 次")
    c2.metric("累计热量", f"{total_calorie:.0f} kcal")
    c3.metric("今日热量", f"{today_calorie:.0f} kcal")

    daily_stats = get_daily_stats(db)
    if daily_stats.empty:
        st.info("暂无统计数据。")
    else:
        st.subheader("近 7 日估算热量")
        st.bar_chart(daily_stats.set_index("date")["total_calorie"], use_container_width=True)

    ranking = get_food_ranking(db)
    if not ranking.empty:
        st.subheader("常见食物排行")
        st.dataframe(
            ranking.rename(
                columns={"predicted_name_cn": "食物", "count": "次数", "total_calorie": "累计热量(kcal)"}
            ),
            hide_index=True,
            use_container_width=True,
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
