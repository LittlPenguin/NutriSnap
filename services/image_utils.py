from __future__ import annotations

import numpy as np
from PIL import Image


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
