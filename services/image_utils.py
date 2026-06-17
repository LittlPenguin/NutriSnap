from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class ImageContentAssessment:
    is_valid: bool
    reason: str
    message: str
    metrics: dict[str, float]


def assess_food_image(image: Image.Image) -> ImageContentAssessment:
    """Run a lightweight sanity check before food classification."""

    rgb_image = image.convert("RGB")
    width, height = rgb_image.size
    if width < 96 or height < 96:
        return ImageContentAssessment(
            is_valid=False,
            reason="image_too_small",
            message="图片尺寸过小，无法可靠识别食物。请上传清晰的餐食照片。",
            metrics={"width": float(width), "height": float(height)},
        )

    thumb = rgb_image.copy()
    thumb.thumbnail((256, 256))
    array = np.asarray(thumb, dtype=np.float32)
    red = array[:, :, 0]
    green = array[:, :, 1]
    blue = array[:, :, 2]
    luma = 0.299 * red + 0.587 * green + 0.114 * blue

    max_channel = array.max(axis=2)
    min_channel = array.min(axis=2)
    saturation = np.divide(
        max_channel - min_channel,
        max_channel,
        out=np.zeros_like(max_channel),
        where=max_channel > 0,
    )

    white_ratio = float(np.mean(luma > 240))
    black_ratio = float(np.mean(luma < 35))
    low_saturation_ratio = float(np.mean(saturation < 0.12))
    neutral_extreme_ratio = float(np.mean((saturation < 0.08) & ((luma > 235) | (luma < 45))))
    luma_std = float(np.std(luma))
    colorfulness = _image_colorfulness(array)
    edge_density = _edge_density(luma)
    aspect_ratio = max(width / height, height / width)

    metrics = {
        "width": float(width),
        "height": float(height),
        "aspect_ratio": round(float(aspect_ratio), 4),
        "white_ratio": round(white_ratio, 4),
        "black_ratio": round(black_ratio, 4),
        "low_saturation_ratio": round(low_saturation_ratio, 4),
        "neutral_extreme_ratio": round(neutral_extreme_ratio, 4),
        "luma_std": round(luma_std, 4),
        "colorfulness": round(colorfulness, 4),
        "edge_density": round(edge_density, 4),
    }

    if luma_std < 8 and colorfulness < 8:
        return ImageContentAssessment(
            is_valid=False,
            reason="blank_or_flat_image",
            message="图片内容过于单一，无法可靠识别食物。请上传包含餐食主体的清晰照片。",
            metrics=metrics,
        )

    is_screen_or_document = (
        neutral_extreme_ratio > 0.72
        and low_saturation_ratio > 0.82
        and colorfulness < 28
        and (aspect_ratio > 1.55 or edge_density > 0.025 or white_ratio + black_ratio > 0.68)
    )
    if is_screen_or_document:
        return ImageContentAssessment(
            is_valid=False,
            reason="screen_or_document_image",
            message="这张图更像截图、表格或文字内容，不像食物照片。请上传餐盘、菜品或食品本体的照片。",
            metrics=metrics,
        )

    return ImageContentAssessment(
        is_valid=True,
        reason="food_like_image",
        message="图片通过基础内容检查。",
        metrics=metrics,
    )


def _image_colorfulness(array: np.ndarray) -> float:
    red = array[:, :, 0]
    green = array[:, :, 1]
    blue = array[:, :, 2]
    red_green = red - green
    yellow_blue = 0.5 * (red + green) - blue
    std_root = float(np.sqrt(np.std(red_green) ** 2 + np.std(yellow_blue) ** 2))
    mean_root = float(np.sqrt(np.mean(red_green) ** 2 + np.mean(yellow_blue) ** 2))
    return std_root + 0.3 * mean_root


def _edge_density(luma: np.ndarray) -> float:
    if luma.shape[0] < 2 or luma.shape[1] < 2:
        return 0.0
    horizontal = np.abs(np.diff(luma, axis=1))
    vertical = np.abs(np.diff(luma, axis=0))
    return float((np.mean(horizontal > 35) + np.mean(vertical > 35)) / 2)


def preprocess_image(image: Image.Image):
    """Convert a PIL image to the normalized 224x224 tensor expected by ResNet18."""

    try:
        from torchvision import transforms
    except ModuleNotFoundError:
        return _preprocess_without_torchvision(image)

    transform = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )
    return transform(image.convert("RGB"))


def _preprocess_without_torchvision(image: Image.Image):
    import torch

    resized = image.convert("RGB").resize((224, 224))
    array = np.asarray(resized, dtype=np.float32) / 255.0
    tensor = torch.from_numpy(array).permute(2, 0, 1)
    mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
    return (tensor - mean) / std
