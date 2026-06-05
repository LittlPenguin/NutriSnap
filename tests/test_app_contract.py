from __future__ import annotations

from pathlib import Path


def test_app_uses_five_streamlit_tabs_and_no_about_tech_stack_card():
    source = Path("app.py").read_text(encoding="utf-8")

    assert '["食物识别", "历史记录", "热量表", "统计分析", "系统说明"]' in source
    assert "估算热量" in source
    assert "仅供饮食记录参考" in source
    assert "不作为医学或营养诊断" in source
    assert "系统说明页不展示技术栈" not in source
    about_source = source.split("def about_page() -> None:", maxsplit=1)[1]
    about_source = about_source.split("def main() -> None:", maxsplit=1)[0]
    assert "技术栈" not in about_source
