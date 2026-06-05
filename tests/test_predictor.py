from __future__ import annotations

from PIL import Image

from services.predictor import FoodPredictor, predict_image


def test_predictor_reports_model_missing_without_demo_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("NUTRISNAP_DEMO_MODE", "false")
    predictor = FoodPredictor(model_path=tmp_path / "missing.pth", class_names_path=tmp_path / "missing.json")
    image = Image.new("RGB", (224, 224), color="white")

    result = predictor.predict_image(image)

    assert result["status"] == "model_missing"
    assert "模型未加载" in result["message"]


def test_predict_image_can_return_explicit_demo_result(monkeypatch):
    monkeypatch.setenv("NUTRISNAP_DEMO_MODE", "true")
    image = Image.new("RGB", (224, 224), color="white")

    result = predict_image(image)

    assert result["status"] == "demo"
    assert result["predicted_class"] == "pizza"
    assert result["predicted_name_cn"] == "披萨"
    assert result["confidence"] == 0.93
    assert result["top3"][0]["class_name"] == "pizza"
