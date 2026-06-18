from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import torch
from torch import nn, optim
from torch.utils.data import DataLoader


def _load_torchvision_training_tools():
    """延迟加载 torchvision（仅在训练时引入依赖）。"""
    try:
        from torchvision import datasets, models, transforms
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "训练需要 torchvision。使用 pip install -r requirements.txt 安装依赖。"
        ) from exc
    return datasets, models, transforms


def build_transforms():
    """构建训练集和验证集的数据增强/预处理流水线。"""
    _, _, transforms = _load_torchvision_training_tools()
    train_transform = transforms.Compose(
        [
            transforms.RandomResizedCrop(224),          # 随机裁剪缩放
            transforms.RandomHorizontalFlip(),           # 随机水平翻转
            transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.15),  # 颜色抖动
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),  # ImageNet 标准化
        ]
    )
    eval_transform = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )
    return train_transform, eval_transform


def build_model(num_classes: int, freeze_backbone: bool = True):
    """构建 ResNet18 迁移学习模型。

    Args:
        num_classes: 分类数（本项目为 12）
        freeze_backbone: 是否冻结主干网络（只训练最后的全连接层）

    Returns:
        构造好的 PyTorch 模型
    """
    _, models, _ = _load_torchvision_training_tools()
    weights = models.ResNet18_Weights.DEFAULT
    model = models.resnet18(weights=weights)
    if freeze_backbone:
        for parameter in model.parameters():
            parameter.requires_grad = False  # 冻结主干
    model.fc = nn.Linear(model.fc.in_features, num_classes)  # 替换全连接层
    return model


def _make_loaders(dataset_root: Path, batch_size: int, num_workers: int):
    """创建训练集和验证集的 DataLoader。"""
    datasets, _, _ = _load_torchvision_training_tools()
    train_transform, eval_transform = build_transforms()
    image_datasets = {
        "train": datasets.ImageFolder(dataset_root / "train", transform=train_transform),
        "val": datasets.ImageFolder(dataset_root / "val", transform=eval_transform),
    }
    loaders = {
        split: DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=(split == "train"),  # 训练集打乱，验证集不打乱
            num_workers=num_workers,
        )
        for split, dataset in image_datasets.items()
    }
    return image_datasets, loaders


def train_model(
    dataset_root: str | Path = "dataset/food101_subset",
    output_model: str | Path = "models/food_resnet18.pth",
    output_classes: str | Path = "models/class_names.json",
    epochs: int = 5,
    batch_size: int = 16,
    learning_rate: float = 0.001,
    freeze_backbone: bool = True,
    num_workers: int = 0,
) -> dict[str, float]:
    """训练 ResNet18 模型并保存最佳权重。

    Args:
        dataset_root: 数据集根目录（需含 train/ 和 val/）
        output_model: 模型权重输出路径
        output_classes: 类别名称 JSON 输出路径
        epochs: 训练轮数
        batch_size: 批次大小
        learning_rate: 学习率
        freeze_backbone: 是否冻结主干网络
        num_workers: DataLoader 工作进程数

    Returns:
        包含最佳验证准确率的字典
    """
    dataset_root = Path(dataset_root)
    output_model = Path(output_model)
    output_classes = Path(output_classes)
    if not (dataset_root / "train").exists() or not (dataset_root / "val").exists():
        raise FileNotFoundError(
            "数据集中必须包含 train/ 和 val/ 目录。请先运行 prepare_food101_subset.py。"
        )

    device = "cuda" if torch.cuda.is_available() else "cpu"
    image_datasets, loaders = _make_loaders(dataset_root, batch_size, num_workers)
    class_names = image_datasets["train"].classes
    model = build_model(len(class_names), freeze_backbone=freeze_backbone).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam((param for param in model.parameters() if param.requires_grad), lr=learning_rate)

    best_model_state = copy.deepcopy(model.state_dict())
    best_accuracy = 0.0
    for epoch in range(epochs):
        print(f"Epoch {epoch + 1}/{epochs}")
        for split in ["train", "val"]:
            model.train(split == "train")
            running_loss = 0.0
            running_corrects = 0
            total = 0
            for inputs, labels in loaders[split]:
                inputs = inputs.to(device)
                labels = labels.to(device)
                optimizer.zero_grad()
                with torch.set_grad_enabled(split == "train"):
                    outputs = model(inputs)
                    _, preds = torch.max(outputs, 1)
                    loss = criterion(outputs, labels)
                    if split == "train":
                        loss.backward()
                        optimizer.step()
                batch_size_actual = inputs.size(0)
                running_loss += loss.item() * batch_size_actual
                running_corrects += torch.sum(preds == labels.data).item()
                total += batch_size_actual

            epoch_loss = running_loss / max(total, 1)
            epoch_accuracy = running_corrects / max(total, 1)
            print(f"  {split}: loss={epoch_loss:.4f} accuracy={epoch_accuracy:.4f}")
            # 保存验证集上的最佳模型
            if split == "val" and epoch_accuracy > best_accuracy:
                best_accuracy = epoch_accuracy
                best_model_state = copy.deepcopy(model.state_dict())

    # 保存模型权重和类别名称
    output_model.parent.mkdir(parents=True, exist_ok=True)
    output_classes.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model_state_dict": best_model_state, "class_names": class_names}, output_model)
    with output_classes.open("w", encoding="utf-8") as file:
        json.dump(class_names, file, ensure_ascii=False, indent=2)
    return {"best_val_accuracy": round(best_accuracy, 4)}


def main() -> None:
    """命令行入口：解析训练参数并启动训练。"""
    parser = argparse.ArgumentParser(description="训练 ResNet18 用于 NutriSnap Food-101 子集分类。")
    parser.add_argument("--dataset-root", default="dataset/food101_subset")
    parser.add_argument("--output-model", default="models/food_resnet18.pth")
    parser.add_argument("--output-classes", default="models/class_names.json")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--unfreeze-backbone", action="store_true")
    parser.add_argument("--num-workers", type=int, default=0)
    args = parser.parse_args()
    result = train_model(
        dataset_root=args.dataset_root,
        output_model=args.output_model,
        output_classes=args.output_classes,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        freeze_backbone=not args.unfreeze_backbone,
        num_workers=args.num_workers,
    )
    print(result)


if __name__ == "__main__":
    main()
