from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class ImageContentAssessment:
    """图片内容质检结果的数据类。

    Attributes:
        is_valid: 图片是否合格（看起来像食物照片）
        reason: 不合格的原因标签
        message: 给用户的中文提示信息
        metrics: 各类质检指标的数值
    """
    is_valid: bool
    reason: str
    message: str
    metrics: dict[str, float]


def assess_food_image(image: Image.Image) -> ImageContentAssessment:
    """对图片进行轻量级内容检查，判断是否适合做食物分类。

    检查维度：尺寸是否过小、内容是否过于单一、是否像截图/文档。
    """
    # 转 RGB 并获取尺寸
    rgb_image = image.convert("RGB")
    width, height = rgb_image.size
    # 尺寸过小直接拒绝
    if width < 96 or height < 96:
        return ImageContentAssessment(
            is_valid=False,
            reason="image_too_small",
            message="图片尺寸过小，无法可靠识别食物。请上传清晰的餐食照片。",
            metrics={"width": float(width), "height": float(height)},
        )

    # 缩放到 256px 以内，计算亮度、饱和度等指标
    thumb = rgb_image.copy()
    thumb.thumbnail((256, 256))
    array = np.asarray(thumb, dtype=np.float32)
    red = array[:, :, 0]
    green = array[:, :, 1]
    blue = array[:, :, 2]
    luma = 0.299 * red + 0.587 * green + 0.114 * blue  # 亮度（Y 分量）

    # 饱和度计算：每个像素的 max(RGB) - min(RGB) / max(RGB)
    max_channel = array.max(axis=2)
    min_channel = array.min(axis=2)
    saturation = np.divide(
        max_channel - min_channel,
        max_channel,
        out=np.zeros_like(max_channel),
        where=max_channel > 0,
    )

    # 各类指标
    white_ratio = float(np.mean(luma > 240))          # 白色像素占比
    black_ratio = float(np.mean(luma < 35))            # 黑色像素占比
    low_saturation_ratio = float(np.mean(saturation < 0.12))  # 低饱和度区域占比
    neutral_extreme_ratio = float(np.mean((saturation < 0.08) & ((luma > 235) | (luma < 45))))  # 极亮/极暗中性色占比
    luma_std = float(np.std(luma))          # 亮度标准差（反映明暗变化）
    colorfulness = _image_colorfulness(array)  # 色彩丰富度
    edge_density = _edge_density(luma)          # 边缘密度
    aspect_ratio = max(width / height, height / width)  # 宽高比

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

    # 内容过于单一：亮度变化小 且 色彩不丰富 → 可能是纯色图或模糊图
    if luma_std < 8 and colorfulness < 8:
        return ImageContentAssessment(
            is_valid=False,
            reason="blank_or_flat_image",
            message="图片内容过于单一，无法可靠识别食物。请上传包含餐食主体的清晰照片。",
            metrics=metrics,
        )

    # 判断是否像截图/文档：高比例的中性极端色、低饱和度、色彩有限、特定宽高比或边缘密度
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

    # 通过所有检查
    return ImageContentAssessment(
        is_valid=True,
        reason="food_like_image",
        message="图片通过基础内容检查。",
        metrics=metrics,
    )


def _image_colorfulness(array: np.ndarray) -> float:
    """计算图像色彩丰富度（Hasler and Süsstrunk 算法）。"""
    red = array[:, :, 0]
    green = array[:, :, 1]
    blue = array[:, :, 2]
    red_green = red - green
    yellow_blue = 0.5 * (red + green) - blue
    std_root = float(np.sqrt(np.std(red_green) ** 2 + np.std(yellow_blue) ** 2))
    mean_root = float(np.sqrt(np.mean(red_green) ** 2 + np.mean(yellow_blue) ** 2))
    return std_root + 0.3 * mean_root


def _edge_density(luma: np.ndarray) -> float:
    """计算图像边缘密度（相邻像素亮度差大于阈值的比例）。"""
    if luma.shape[0] < 2 or luma.shape[1] < 2:
        return 0.0
    horizontal = np.abs(np.diff(luma, axis=1))
    vertical = np.abs(np.diff(luma, axis=0))
    return float((np.mean(horizontal > 35) + np.mean(vertical > 35)) / 2)


def preprocess_image(image: Image.Image):
    """将 PIL 图像转换为 ResNet18 标准输入：224×224、归一化的 PyTorch 张量。

    优先使用 torchvision.transforms，若不可用则回退到手动实现。
    """
    try:
        from torchvision import transforms
    except ModuleNotFoundError:
        return _preprocess_without_torchvision(image)

    transform = transforms.Compose(
        [
            transforms.Resize((224, 224)),                                       # 缩放到 224×224
            transforms.ToTensor(),                                                # HWC → CHW，归一化到 [0, 1]
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),  # ImageNet 标准化
        ]
    )
    return transform(image.convert("RGB"))


def _preprocess_without_torchvision(image: Image.Image):
    """不使用 torchvision 时的降级预处理实现。"""
    import torch

    resized = image.convert("RGB").resize((224, 224))
    array = np.asarray(resized, dtype=np.float32) / 255.0
    tensor = torch.from_numpy(array).permute(2, 0, 1)  # HWC → CHW
    mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
    return (tensor - mean) / std
