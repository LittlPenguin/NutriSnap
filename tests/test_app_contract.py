from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_app_routes_four_pages_and_about_falls_back_to_recognition():
    app_source = Path("app.py").read_text(encoding="utf-8")
    pages_source = Path("ui/pages.py").read_text(encoding="utf-8")

    assert '["食物识别", "历史记录", "热量表", "统计分析"]' in app_source
    assert "st.query_params" in app_source
    assert "st.tabs" not in app_source
    assert "recognition_page(db)" in app_source
    assert "history_page(db)" in app_source
    assert "calorie_table_page(db)" in app_source
    assert "stats_page(db)" in app_source
    assert "about_page()" not in app_source
    assert '"about"' not in app_source
    assert "def about_page()" not in pages_source
    assert "估算热量" in pages_source
    assert "仅供饮食记录参考" in pages_source
    assert "不作为医学或营养诊断" in pages_source


def test_dual_navigation_matches_open_design_labels_and_internal_switching():
    components_source = Path("ui/components.py").read_text(encoding="utf-8")
    styles_source = Path("ui/styles.py").read_text(encoding="utf-8")
    app_source = Path("app.py").read_text(encoding="utf-8")

    for label in ["食物识别", "历史记录", "热量表", "统计分析"]:
        assert label in components_source
    for short_label in ["识别", "历史", "热量表", "统计"]:
        assert short_label in components_source
    for removed_label in ["系统说明", '"about"']:
        assert removed_label not in components_source
    assert 'href="?page=' not in components_source
    assert 'href="?page=' not in app_source
    for text in ["desktop-nav", "bottom-nav", "nav-item", "active", "st.query_params", "st.rerun"]:
        assert text in components_source
    assert "st.pills" in components_source or "st.segmented_control" in components_source
    bottom_nav_source = components_source.split("def bottom_nav(active_page: str) -> None:", maxsplit=1)[1]
    bottom_nav_source = bottom_nav_source.split("\ndef ", maxsplit=1)[0]
    assert "st.pills" not in bottom_nav_source
    assert "st.columns(4)" in bottom_nav_source
    assert "mobile_nav_button" in styles_source
    assert "grid-template-columns: repeat(4, minmax(0, 1fr))" in styles_source
    for selector in [".desktop-nav", ".nav-item", ".bottom-nav"]:
        assert selector in styles_source


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

    for text in ["今天也记一餐", "今日已记录", "上传食物图片", "已上传预览", "本次份量", "Model 饮食建议"]:
        assert text in pages_source
    for text in ["Model 配置", "保存到本次会话", "清除页面配置，恢复 .env", "当前使用："]:
        assert text in pages_source
    for text in ["未上传状态", "识别完成", "Model 生成中", "生成完毕", "失败："]:
        assert text in components_source
    for removed_text in ["GPT 饮食建议", "GPT 配置", "GPT 生成中", "GPT 建议完成"]:
        assert removed_text not in pages_source
        assert removed_text not in components_source
    assert "Top-3 预测" in pages_source
    assert "模型未加载" in pages_source


def test_history_calorie_and_stats_pages_match_open_design_sections():
    pages_source = Path("ui/pages.py").read_text(encoding="utf-8")
    components_source = Path("ui/components.py").read_text(encoding="utf-8")
    styles_source = Path("ui/styles.py").read_text(encoding="utf-8")

    for text in ["历史记录列表", "Model 建议摘要", "今日记录", "今日估算"]:
        assert text in pages_source
    for removed_text in [
        "含 GPT 失败降级提示",
        "GPT 失败降级",
        "当 GPT API key 未配置、网络失败或响应超时时，系统仍保存历史记录，并展示本地规则建议。",
    ]:
        assert removed_text not in pages_source
    for text in ["食物热量表", "Food-101 子集参考数据", "266 kcal / 100g", "默认份量", "热量表边界说明"]:
        assert text in pages_source
    for text in ["最新上传食物图", "常见食物排行", "累计记录", "累计热量", "今日热量", "说明"]:
        assert text in pages_source
    assert "基于识别历史中的估算热量，不作为医学或营养诊断。" in pages_source
    assert "近 7 日估算热量" not in pages_source
    assert "结果边界说明" not in pages_source

    for function_name in ["history_record_card", "food_calorie_card", "ranking_row", "estimate_boundary_card"]:
        assert function_name in components_source
    for class_name in ["history-list", "food-grid", "chart-shell", "boundary-card"]:
        assert class_name in styles_source


def test_final_open_design_contract_and_blockers_are_recorded():
    app_source = Path("app.py").read_text(encoding="utf-8")
    pages_source = Path("ui/pages.py").read_text(encoding="utf-8")
    components_source = Path("ui/components.py").read_text(encoding="utf-8")
    blockers_source = Path("doc/开发阻塞记录.md").read_text(encoding="utf-8")
    agents_source = Path("AGENTS.md").read_text(encoding="utf-8")

    for route_key in ['"recognition"', '"history"', '"calories"', '"stats"']:
        assert route_key in app_source
    assert '"about"' not in app_source
    for text in ["399 kcal", "266 kcal / 100g", "150g", "估算热量", "仅供饮食记录参考"]:
        assert text in pages_source
    for text in ["progress-list", "history-row", "food-row", "chart-shell", "bottom-nav", "desktop-nav"]:
        assert text in components_source or text in pages_source
    for blocker in ["OPENAI_API_KEY", "Food-101 子集真实图片", "models/food_resnet18.pth", "浏览器模拟移动端验收"]:
        assert blocker in blockers_source
    for text in ["B-002 已解决", "is_valid: true", "总计 360 张", "B-004 不做真机校验"]:
        assert text in blockers_source
    for rule in ["每完成一个阶段必须进行一次 Git 提交", "提交信息必须使用中文", "opendesign-nutrisnap/"]:
        assert rule in agents_source


def test_four_routes_render_open_design_key_sections_and_about_falls_back():
    routes = {
        "recognition": ["NutriSnap 轻食记录", "食物识别工作台", "上传食物图片", "Top-3"],
        "history": ["NutriSnap 轻食记录", "历史记录", "今日记录", "历史记录列表"],
        "calories": ["NutriSnap 轻食记录", "食物热量表", "Food-101 子集参考数据", "399 kcal"],
        "stats": ["NutriSnap 轻食记录", "统计分析", "最新上传食物图", "常见食物排行"],
    }

    for route, expected_texts in routes.items():
        app = AppTest.from_file("app.py")
        if route != "recognition":
            app.query_params["page"] = route
        app.run(timeout=20)

        rendered_markdown = "\n".join(str(node.value) for node in app.markdown)
        assert not app.exception
        for text in expected_texts:
            assert text in rendered_markdown

    app = AppTest.from_file("app.py")
    app.query_params["page"] = "about"
    app.run(timeout=20)
    rendered_markdown = "\n".join(str(node.value) for node in app.markdown)
    assert not app.exception
    assert "食物识别工作台" in rendered_markdown
    assert "系统说明" not in rendered_markdown
