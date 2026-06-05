from __future__ import annotations

from io import BytesIO

import pandas as pd
import streamlit as st
from PIL import Image, UnidentifiedImageError

from services.calorie_service import CalorieService
from services.database import get_database
from services.gpt_advice_service import generate_gpt_advice
from services.predictor import predict_image
from services.schemas import USER_GOALS
from services.stats_service import get_daily_stats, get_food_ranking

st.set_page_config(
    page_title="NutriSnap 轻食记录",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --nutri-bg: #F7FAF6;
            --nutri-primary: #5CA878;
            --nutri-accent: #F4A261;
            --nutri-text: #1F2933;
            --nutri-muted: #6B7280;
            --nutri-border: #E5E7EB;
            --nutri-good: #EEF8F1;
            --nutri-warn: #FFF4E6;
        }
        .stApp { background: var(--nutri-bg); color: var(--nutri-text); }
        .main-title { margin-bottom: 0.1rem; }
        .subtle { color: var(--nutri-muted); font-size: 0.95rem; }
        .metric-card {
            background: #FFFFFF;
            border: 1px solid var(--nutri-border);
            border-radius: 8px;
            padding: 1rem;
            min-height: 96px;
        }
        .result-card {
            background: #FFFFFF;
            border: 1px solid var(--nutri-border);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 0.75rem;
        }
        .advice-card {
            background: var(--nutri-good);
            border: 1px solid #D8EBDD;
            border-radius: 8px;
            padding: 1rem;
            margin-top: 0.75rem;
        }
        .warning-card {
            background: var(--nutri-warn);
            border: 1px solid #F8D5A8;
            border-radius: 8px;
            padding: 1rem;
            margin-top: 0.75rem;
        }
        .calorie-number { color: var(--nutri-accent); font-size: 2.3rem; font-weight: 750; line-height: 1.1; }
        .small-label { color: var(--nutri-muted); font-size: 0.85rem; }
        div.stButton > button {
            border-radius: 8px;
            border: 1px solid var(--nutri-primary);
            background: var(--nutri-primary);
            color: white;
            width: 100%;
        }
        div.stButton > button:hover {
            border: 1px solid #4B9367;
            background: #4B9367;
            color: white;
        }
        @media (max-width: 760px) {
            .block-container { padding-left: 1rem; padding-right: 1rem; }
            .main-title { font-size: 1.75rem; }
            .calorie-number { font-size: 2rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_resource
def load_db():
    return get_database()


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
        st.markdown(
            f"""
            <div class="warning-card">
              <strong>{prediction.get("message", "模型暂不可用")}</strong><br>
              <span class="small-label">可先训练模型，或在 .env 中开启 NUTRISNAP_DEMO_MODE=true 进行课程演示。</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    status_label = "演示结果" if prediction.get("status") == "demo" else "识别结果"
    st.markdown(
        f"""
        <div class="result-card">
          <div class="small-label">{status_label}</div>
          <h3>{prediction["predicted_name_cn"]}</h3>
          <p>置信度：<strong>{confidence_text(prediction["confidence"])}</strong></p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    top3 = prediction.get("top3", [])
    if top3:
        st.write("Top-3 预测")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "食物": item["name_cn"],
                        "类别": item["class_name"],
                        "置信度": confidence_text(item["confidence"]),
                    }
                    for item in top3
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )


def recognition_page(db) -> None:
    st.markdown('<h1 class="main-title">NutriSnap</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtle">今天也记一餐。热量为估算值，仅供饮食记录参考。</p>', unsafe_allow_html=True)

    left, right = st.columns([1, 1], gap="large")
    with left:
        st.subheader("上传食物图片")
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
            st.markdown(
                f"""
                <div class="result-card">
                  <div class="small-label">估算热量</div>
                  <div class="calorie-number">{calorie_result["total_calorie"]} kcal</div>
                  <p>每 100g 约 {calorie_result["calorie_per_100g"]} kcal / 100g</p>
                  <span class="small-label">热量为估算值，仅供饮食记录参考。</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        if advice_result:
            status = "GPT 饮食建议" if advice_result["status"] == "success" else "本地规则建议"
            st.markdown(
                f"""
                <div class="advice-card">
                  <strong>{status}</strong><br>
                  {advice_result["advice"]}
                </div>
                """,
                unsafe_allow_html=True,
            )


def history_page(db) -> None:
    st.header("历史记录")
    history = db.list_history()
    today = pd.Timestamp.now().strftime("%Y-%m-%d")
    today_rows = [row for row in history if str(row["created_at"]).startswith(today)]
    c1, c2 = st.columns(2)
    c1.metric("今日记录", f"{len(today_rows)} 次")
    c2.metric("今日估算", f"{sum(float(row['total_calorie']) for row in today_rows):.0f} kcal")

    if not history:
        st.info("暂无历史记录。完成一次识别和热量估算后会自动保存。")
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


def calorie_table_page(db) -> None:
    st.header("食物热量表")
    query_col, category_col = st.columns([2, 1])
    with query_col:
        query = st.text_input("搜索食物名称", placeholder="例如：披萨 / pizza")
    with category_col:
        category = st.selectbox("分类筛选", ["全部", "主食", "快餐", "甜点", "肉类", "沙拉"])

    foods = db.list_foods(category=category, query=query)
    if not foods:
        st.info("没有找到匹配的食物。")
        return
    for row in foods:
        st.markdown(
            f"""
            <div class="result-card">
              <strong>{row["name_cn"]}</strong>
              <span class="small-label"> · {row["class_name"]} · {row["category"]}</span><br>
              <span style="color:#F4A261;font-weight:700;">{row["calorie_per_100g"]:.0f} kcal / 100g</span>
              <span class="small-label">　默认份量 {row["default_weight_g"]:.0f}g</span><br>
              <span class="small-label">{row.get("note", "")}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def stats_page(db) -> None:
    st.header("统计分析")
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


def about_page() -> None:
    st.header("系统说明")
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


def main() -> None:
    inject_css()
    db = load_db()
    tabs = st.tabs(["食物识别", "历史记录", "热量表", "统计分析", "系统说明"])
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
