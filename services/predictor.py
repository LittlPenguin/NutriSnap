from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from PIL import Image

from services.schemas import CLASS_NAME_CN, DEFAULT_CLASS_NAMES_PATH, DEFAULT_MODEL_PATH, DEMO_PREDICTION


def _demo_enabled() -> bool:
    """检查环境变量 NUTRISNAP_DEMO_MODE 是否开启演示模式。"""
    return os.getenv("NUTRISNAP_DEMO_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}


class FoodPredictor:
    """基于 ResNet18 的食物图像分类预测器，支持自动设备选择、懒加载模型。"""

    def __init__(
        self,
        model_path: str | Path = DEFAULT_MODEL_PATH,
        class_names_path: str | Path = DEFAULT_CLASS_NAMES_PATH,
        device: str | None = None,
    ) -> None:
        """初始化预测器。

        Args:
            model_path: 模型权重文件路径
            class_names_path: 类别名称 JSON 文件路径
            device: 推理设备（cuda / cpu），None 表示自动选择
        """
        self.model_path = Path(model_path)
        self.class_names_path = Path(class_names_path)
        self.device = device
        self._model = None  # 模型缓存，第一次加载后复用
        self._class_names: list[str] | None = None

    def predict_image(self, image: Image.Image) -> dict[str, Any]:
        """对输入图片进行食物分类预测，返回包含状态、Top-3 结果和置信度的字典。

        支持多级降级：图片质检失败、演示模式、模型不存在、正常推理。
        """
        from services.image_utils import assess_food_image

        # 第一步：图片内容质检（尺寸、饱和度、是否截图等）
        assessment = assess_food_image(image)
        if not assessment.is_valid:
            return {
                "status": "invalid_image",
                "message": assessment.message,
                "reason": assessment.reason,
                "quality_metrics": assessment.metrics,
            }

        # 第二步：演示模式直接返回固定结果
        if _demo_enabled():
            return dict(DEMO_PREDICTION)
        # 第三步：模型或类名文件不存在
        if not self.model_path.exists() or not self.class_names_path.exists():
            return {
                "status": "model_missing",
                "message": "模型未加载：请先训练模型，或将 NUTRISNAP_DEMO_MODE=true 用于课程演示。",
            }

        # 第四步：加载模型并进行推理
        model, class_names, device = self._load_model()

        import torch

        from services.image_utils import preprocess_image

        # 预处理图片 → 加 batch 维度 → 送入设备
        tensor = preprocess_image(image).unsqueeze(0).to(device)
        with torch.no_grad():
            logits = model(tensor)
            probabilities = torch.softmax(logits, dim=1)[0]
            top_values, top_indices = torch.topk(probabilities, k=min(3, len(class_names)))

        # 构造 Top-3 结果列表
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
        """懒加载模型：如果已经加载过则直接返回缓存，否则从磁盘加载。

        加载流程：读取 class_names.json → 构建 ResNet18 → 替换全连接层 → 加载权重 → 切换到评估模式。
        """
        if self._model is not None and self._class_names is not None:
            return self._model, self._class_names, self.device

        import torch
        from torchvision import models

        # 读取类别名称列表
        with self.class_names_path.open("r", encoding="utf-8") as file:
            class_names = json.load(file)
        if not isinstance(class_names, list) or not class_names:
            raise ValueError("class_names.json 必须包含非空列表")

        # 确定设备（优先 CUDA）
        device = self.device or ("cuda" if torch.cuda.is_available() else "cpu")
        # 构建 ResNet18，不加载预训练权重（使用我们自己的微调权重）
        model = models.resnet18(weights=None)
        # 替换全连接层为适配 12 类输出的线性层
        model.fc = torch.nn.Linear(model.fc.in_features, len(class_names))
        # 加载模型权重（兼容 dict 和直接 state_dict 两种格式）
        checkpoint = torch.load(self.model_path, map_location=device)
        state_dict = checkpoint.get("model_state_dict", checkpoint) if isinstance(checkpoint, dict) else checkpoint
        model.load_state_dict(state_dict)
        model.to(device)
        model.eval()  # 切换到推理模式

        # 写入缓存
        self._model = model
        self._class_names = class_names
        self.device = device
        return model, class_names, device


def predict_image(image: Image.Image) -> dict[str, Any]:
    """快捷函数：使用默认 FoodPredictor 实例进行预测。"""
    return FoodPredictor().predict_image(image)
