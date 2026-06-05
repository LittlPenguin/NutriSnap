from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from PIL import Image

from services.schemas import CLASS_NAME_CN, DEFAULT_CLASS_NAMES_PATH, DEFAULT_MODEL_PATH, DEMO_PREDICTION


def _demo_enabled() -> bool:
    return os.getenv("NUTRISNAP_DEMO_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}


class FoodPredictor:
    def __init__(
        self,
        model_path: str | Path = DEFAULT_MODEL_PATH,
        class_names_path: str | Path = DEFAULT_CLASS_NAMES_PATH,
        device: str | None = None,
    ) -> None:
        self.model_path = Path(model_path)
        self.class_names_path = Path(class_names_path)
        self.device = device
        self._model = None
        self._class_names: list[str] | None = None

    def predict_image(self, image: Image.Image) -> dict[str, Any]:
        if _demo_enabled():
            return dict(DEMO_PREDICTION)
        if not self.model_path.exists() or not self.class_names_path.exists():
            return {
                "status": "model_missing",
                "message": "模型未加载：请先训练模型，或将 NUTRISNAP_DEMO_MODE=true 用于课程演示。",
            }

        model, class_names, device = self._load_model()

        import torch

        from services.image_utils import preprocess_image

        tensor = preprocess_image(image).unsqueeze(0).to(device)
        with torch.no_grad():
            logits = model(tensor)
            probabilities = torch.softmax(logits, dim=1)[0]
            top_values, top_indices = torch.topk(probabilities, k=min(3, len(class_names)))

        top3 = []
        for value, index in zip(top_values.tolist(), top_indices.tolist(), strict=False):
            class_name = class_names[index]
            top3.append(
                {
                    "class_name": class_name,
                    "name_cn": CLASS_NAME_CN.get(class_name, class_name),
                    "confidence": round(float(value), 4),
                }
            )
        best = top3[0]
        return {
            "status": "success",
            "predicted_class": best["class_name"],
            "predicted_name_cn": best["name_cn"],
            "confidence": best["confidence"],
            "top3": top3,
            "message": "识别完成，热量为辅助估算值。",
        }

    def _load_model(self):
        if self._model is not None and self._class_names is not None:
            return self._model, self._class_names, self.device

        import torch
        from torchvision import models

        with self.class_names_path.open("r", encoding="utf-8") as file:
            class_names = json.load(file)
        if not isinstance(class_names, list) or not class_names:
            raise ValueError("class_names.json must contain a non-empty list")

        device = self.device or ("cuda" if torch.cuda.is_available() else "cpu")
        model = models.resnet18(weights=None)
        model.fc = torch.nn.Linear(model.fc.in_features, len(class_names))
        checkpoint = torch.load(self.model_path, map_location=device)
        state_dict = checkpoint.get("model_state_dict", checkpoint) if isinstance(checkpoint, dict) else checkpoint
        model.load_state_dict(state_dict)
        model.to(device)
        model.eval()

        self._model = model
        self._class_names = class_names
        self.device = device
        return model, class_names, device


def predict_image(image: Image.Image) -> dict[str, Any]:
    return FoodPredictor().predict_image(image)
