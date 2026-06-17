from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from services.predictor import FoodPredictor, predict_image


def _food_like_image() -> Image.Image:
    image = Image.new("RGB", (224, 224), color=(185, 105, 55))
    draw = ImageDraw.Draw(image)
    draw.ellipse((30, 26, 194, 190), fill=(235, 174, 82), outline=(116, 72, 35), width=8)
    draw.ellipse((68, 68, 104, 104), fill=(196, 48, 42))
    draw.ellipse((118, 60, 154, 96), fill=(196, 48, 42))
    draw.rectangle((74, 122, 166, 152), fill=(80, 150, 88))
    return image


def test_predictor_reports_model_missing_without_demo_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("NUTRISNAP_DEMO_MODE", "false")
    predictor = FoodPredictor(model_path=tmp_path / "missing.pth", class_names_path=tmp_path / "missing.json")
    image = _food_like_image()

    result = predictor.predict_image(image)

    assert result["status"] == "model_missing"
    assert "模型未加载" in result["message"]


def test_predict_image_can_return_explicit_demo_result(monkeypatch):
    monkeypatch.setenv("NUTRISNAP_DEMO_MODE", "true")
    image = _food_like_image()

    result = predict_image(image)

    assert result["status"] == "demo"
    assert result["predicted_class"] == "pizza"
    assert result["predicted_name_cn"] == "披萨"
    assert result["confidence"] == 0.93
    assert result["top3"][0]["class_name"] == "pizza"


def test_demo_mode_rejects_blank_non_food_image(monkeypatch):
    monkeypatch.setenv("NUTRISNAP_DEMO_MODE", "true")
    image = Image.new("RGB", (224, 224), color="white")

    result = predict_image(image)

    assert result["status"] == "invalid_image"
    assert result["reason"] == "blank_or_flat_image"
    assert "餐食" in result["message"]


def test_demo_mode_rejects_screen_or_document_image(monkeypatch):
    monkeypatch.setenv("NUTRISNAP_DEMO_MODE", "true")
    image = Image.new("RGB", (900, 420), color="white")
    draw = ImageDraw.Draw(image)
    for index in range(7):
        y = 28 + index * 54
        fill = (24, 24, 24) if index % 2 == 0 else (248, 248, 248)
        draw.rectangle((24, y, 876, y + 40), fill=fill)
        text_fill = (235, 235, 235) if index % 2 == 0 else (45, 45, 45)
        draw.text((44, y + 11), f"002{index}  37.{index}9  10.00%  table text", fill=text_fill)

    result = predict_image(image)

    assert result["status"] == "invalid_image"
    assert result["reason"] == "screen_or_document_image"
    assert "截图" in result["message"]


def test_uploaded_stock_screenshot_fixture_is_rejected(monkeypatch):
    monkeypatch.setenv("NUTRISNAP_DEMO_MODE", "true")
    fixture = Path(r"C:\Users\22462\AppData\Local\Temp\codex-clipboard-d36d438a-2a41-42e5-9280-8eb5cba5fe99.png")
    if not fixture.exists():
        pytest.skip("clipboard screenshot fixture is not available")

    result = predict_image(Image.open(fixture))

    assert result["status"] == "invalid_image"
    assert result["reason"] == "screen_or_document_image"
