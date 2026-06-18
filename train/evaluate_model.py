from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch
from torch.utils.data import DataLoader

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from train.train_model import build_model, build_transforms


def evaluate_model(
    dataset_root: str | Path = "dataset/food101_subset",
    model_path: str | Path = "models/food_resnet18.pth",
    class_names_path: str | Path = "models/class_names.json",
    batch_size: int = 16,
    num_workers: int = 0,
) -> dict[str, float]:
    """在测试集上评估 ResNet18 模型的 Top-1 和 Top-3 准确率。

    Args:
        dataset_root: 数据集根目录（需包含 test/ 子目录）
        model_path: 模型权重文件路径
        class_names_path: 类别名称 JSON 路径
        batch_size: 批大小
        num_workers: DataLoader 工作进程数

    Returns:
        包含 accuracy、top3_accuracy、sample_count 的字典
    """
    try:
        from torchvision import datasets
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "评估需要 torchvision，请先安装依赖：pip install -r requirements.txt"
        ) from exc

    dataset_root = Path(dataset_root)
    model_path = Path(model_path)
    class_names_path = Path(class_names_path)
    if not model_path.exists():
        raise FileNotFoundError(f"模型文件不存在: {model_path}")
    if not (dataset_root / "test").exists():
        raise FileNotFoundError("数据集必须包含 test/ 目录。")

    # 读取类别名称
    with class_names_path.open("r", encoding="utf-8") as file:
        class_names = json.load(file)
    _, eval_transform = build_transforms()
    dataset = datasets.ImageFolder(dataset_root / "test", transform=eval_transform)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers)

    # 加载模型
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = build_model(len(class_names), freeze_backbone=False).to(device)
    checkpoint = torch.load(model_path, map_location=device)
    state_dict = checkpoint.get("model_state_dict", checkpoint) if isinstance(checkpoint, dict) else checkpoint
    model.load_state_dict(state_dict)
    model.eval()

    # 遍历测试集计算准确率
    correct_top1 = 0
    correct_top3 = 0
    total = 0
    with torch.no_grad():
        for inputs, labels in loader:
            inputs = inputs.to(device)
            labels = labels.to(device)
            outputs = model(inputs)
            _, top1 = outputs.max(1)
            _, top3 = outputs.topk(k=min(3, len(class_names)), dim=1)
            correct_top1 += (top1 == labels).sum().item()
            correct_top3 += sum(label.item() in row.tolist() for label, row in zip(labels, top3, strict=False))
            total += labels.size(0)

    return {
        "accuracy": round(correct_top1 / max(total, 1), 4),          # Top-1 准确率
        "top3_accuracy": round(correct_top3 / max(total, 1), 4),      # Top-3 准确率
        "sample_count": float(total),                                 # 总测试样本数
    }


def main() -> None:
    """命令行入口：解析参数并运行评估。"""
    parser = argparse.ArgumentParser(description="评估 NutriSnap ResNet18 模型。")
    parser.add_argument("--dataset-root", default="dataset/food101_subset")
    parser.add_argument("--model-path", default="models/food_resnet18.pth")
    parser.add_argument("--class-names-path", default="models/class_names.json")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--num-workers", type=int, default=0)
    args = parser.parse_args()
    print(
        evaluate_model(
            dataset_root=args.dataset_root,
            model_path=args.model_path,
            class_names_path=args.class_names_path,
            batch_size=args.batch_size,
            num_workers=args.num_workers,
        )
    )


if __name__ == "__main__":
    main()
