from __future__ import annotations

from pathlib import Path


def test_app_routes_five_pages_and_about_page_has_no_tech_stack_card():
    app_source = Path("app.py").read_text(encoding="utf-8")
    pages_source = Path("ui/pages.py").read_text(encoding="utf-8")

    assert '["食物识别", "历史记录", "热量表", "统计分析", "系统说明"]' in app_source
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
