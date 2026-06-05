from __future__ import annotations

from pathlib import Path


def test_app_routes_five_pages_and_about_page_has_no_tech_stack_card():
    app_source = Path("app.py").read_text(encoding="utf-8")
    pages_source = Path("ui/pages.py").read_text(encoding="utf-8")

    assert '["食物识别", "历史记录", "热量表", "统计分析", "系统说明"]' in app_source
    assert "st.query_params" in app_source
    assert "st.tabs" not in app_source
    assert "recognition_page(db)" in app_source
    assert "history_page(db)" in app_source
    assert "calorie_table_page(db)" in app_source
    assert "stats_page(db)" in app_source
    assert "about_page()" in app_source
    assert "估算热量" in pages_source
    assert "仅供饮食记录参考" in pages_source
    assert "不作为医学或营养诊断" in pages_source
    about_source = pages_source.split("def about_page() -> None:", maxsplit=1)[1]
    about_source = about_source.split("def main() -> None:", maxsplit=1)[0]
    assert "技术栈" not in about_source


def test_dual_navigation_matches_open_design_labels_and_links():
    components_source = Path("ui/components.py").read_text(encoding="utf-8")
    styles_source = Path("ui/styles.py").read_text(encoding="utf-8")

    for label in ["食物识别", "历史记录", "热量表", "统计分析", "系统说明"]:
        assert label in components_source
    for short_label in ["识别", "历史", "热量表", "统计", "说明"]:
        assert short_label in components_source
    for text in ['href="?page=', "desktop-nav", "bottom-nav", "nav-item", "active"]:
        assert text in components_source
    for selector in [".desktop-nav a", ".nav-item", ".bottom-nav"]:
        assert selector in styles_source


def test_about_page_matches_open_design_boundary_sections():
    pages_source = Path("ui/pages.py").read_text(encoding="utf-8")
    about_source = pages_source.split("def about_page() -> None:", maxsplit=1)[1]

    for text in ["项目简介", "使用步骤", "模型与数据边界", "GPT-5 功能边界", "免责声明"]:
        assert text in about_source
    for text in ["不作为医学或营养诊断", "不会仅凭图片自动精确估重", "GPT-5 不参与图像识别"]:
        assert text in about_source
    assert "技术栈" not in about_source


def test_design_system_tokens_and_core_component_classes_exist():
    styles_source = Path("ui/styles.py").read_text(encoding="utf-8")
    components_source = Path("ui/components.py").read_text(encoding="utf-8")

    for token in ["#F7FAF6", "#5CA878", "#F4A261", "#EEF8F1", "#FFF4E6"]:
        assert token in styles_source
    for class_name in ["bottom-nav", "desktop-nav", "progress-list", "desktop-stat", "warning-card"]:
        assert class_name in styles_source
    for function_name in ["brand_header", "bottom_nav", "top3_progress", "calorie_result_card"]:
        assert function_name in components_source


def test_recognition_page_matches_open_design_key_states():
    pages_source = Path("ui/pages.py").read_text(encoding="utf-8")
    components_source = Path("ui/components.py").read_text(encoding="utf-8")

    for text in ["今天也记一餐", "今日已记录", "上传食物图片", "已上传预览", "本次份量", "GPT 饮食建议"]:
        assert text in pages_source
    for text in ["未上传状态", "识别完成", "GPT 生成中", "GPT 建议完成", "本地规则建议"]:
        assert text in components_source
    assert "Top-3 预测" in pages_source
    assert "模型未加载" in pages_source


def test_history_calorie_and_stats_pages_match_open_design_sections():
    pages_source = Path("ui/pages.py").read_text(encoding="utf-8")
    components_source = Path("ui/components.py").read_text(encoding="utf-8")
    styles_source = Path("ui/styles.py").read_text(encoding="utf-8")

    for text in ["历史记录列表", "GPT 失败降级", "本地规则建议", "今日记录", "今日估算"]:
        assert text in pages_source
    for text in ["食物热量表", "Food-101 子集参考数据", "266 kcal / 100g", "默认份量", "热量表边界说明"]:
        assert text in pages_source
    for text in ["近 7 日估算热量", "常见食物排行", "累计记录", "累计热量", "今日热量", "结果边界说明"]:
        assert text in pages_source

    for function_name in ["history_record_card", "food_calorie_card", "ranking_row", "estimate_boundary_card"]:
        assert function_name in components_source
    for class_name in ["history-list", "food-grid", "chart-shell", "boundary-card"]:
        assert class_name in styles_source
