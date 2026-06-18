from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.schemas import FOOD101_SUBSET_CLASSES


def split_indices(indices: list[int], seed: int = 42) -> tuple[list[int], list[int], list[int]]:
    """将索引列表按 70:15:15 比例划分为训练集、验证集、测试集。"""
    shuffled = list(indices)
    random.Random(seed).shuffle(shuffled)
    train_end = int(len(shuffled) * 0.70)
    val_end = train_end + int(len(shuffled) * 0.15)
    return shuffled[:train_end], shuffled[train_end:val_end], shuffled[val_end:]


def download_food101_raw(raw_root: str | Path = "dataset/food101_raw") -> Path:
    """使用 torchvision 下载 Food-101 完整数据集，返回图片目录路径。"""
    raw_root = Path(raw_root)
    try:
        from torchvision.datasets import Food101
    except ImportError as exc:
        raise RuntimeError("下载 Food-101 需要安装 torchvision。") from exc

    for split in ["train", "test"]:
        Food101(root=str(raw_root), split=split, download=True)
    return raw_root / "food-101" / "images"


def prepare_food101_subset(
    source_root: str | Path = "dataset/food101_raw/food-101/images",
    output_root: str | Path = "dataset/food101_subset",
    limit_per_class: int | None = None,
    seed: int = 42,
) -> None:
    """从 Food-101 全量数据中提取 12 类子集，按 70:15:15 分 train/val/test。

    Args:
        source_root: Food-101 完整图片目录
        output_root: 子集输出目录
        limit_per_class: 每类最多取多少张（None 表示全部）
        seed: 随机种子
    """
    source_root = Path(source_root)
    output_root = Path(output_root)
    if not source_root.exists():
        raise FileNotFoundError(
            f"Food-101 图片目录不存在: {source_root}。"
            "请先下载 Food-101，或通过 --source-root 指定已有图片目录。"
        )

    # 创建 train/val/test 子目录结构
    for split in ["train", "val", "test"]:
        for class_name in FOOD101_SUBSET_CLASSES:
            (output_root / split / class_name).mkdir(parents=True, exist_ok=True)

    # 遍历 12 类，复制图片并按比例分配
    for class_name in FOOD101_SUBSET_CLASSES:
        class_dir = source_root / class_name
        if not class_dir.exists():
            raise FileNotFoundError(f"Food-101 类别目录不存在: {class_dir}")
        images = sorted(class_dir.glob("*.jpg"))
        if limit_per_class is not None:
            images = images[:limit_per_class]
        train_idx, val_idx, test_idx = split_indices(list(range(len(images))), seed=seed)
        split_map = {"train": train_idx, "val": val_idx, "test": test_idx}
        for split, indices in split_map.items():
            for index in indices:
                shutil.copy2(images[index], output_root / split / class_name / images[index].name)

    # 保存类别名称列表
    with (output_root / "class_names.json").open("w", encoding="utf-8") as file:
        json.dump(FOOD101_SUBSET_CLASSES, file, ensure_ascii=False, indent=2)


def validate_food101_subset(output_root: str | Path = "dataset/food101_subset") -> dict[str, Any]:
    """验证 Food-101 子集结构完整性，返回验收报告。"""
    output_root = Path(output_root)
    report: dict[str, Any] = {
        "output_root": str(output_root),
        "expected_classes": FOOD101_SUBSET_CLASSES,
        "splits": {},
        "missing_classes": {},
        "empty_classes": {},
        "total_images": 0,
        "class_names_matches": False,
        "is_valid": False,
    }

    for split in ["train", "val", "test"]:
        report["splits"][split] = {}
        report["missing_classes"][split] = []
        report["empty_classes"][split] = []
        for class_name in FOOD101_SUBSET_CLASSES:
            class_dir = output_root / split / class_name
            if not class_dir.exists():
                report["missing_classes"][split].append(class_name)
                report["splits"][split][class_name] = 0
                continue
            image_count = sum(1 for path in class_dir.iterdir() if path.suffix.lower() in {".jpg", ".jpeg", ".png"})
            report["splits"][split][class_name] = image_count
            report["total_images"] += image_count
            if image_count == 0:
                report["empty_classes"][split].append(class_name)

    class_names_path = output_root / "class_names.json"
    if class_names_path.exists():
        try:
            class_names = json.loads(class_names_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            class_names = None
        report["class_names_matches"] = class_names == FOOD101_SUBSET_CLASSES

    has_missing = any(report["missing_classes"][split] for split in ["train", "val", "test"])
    has_empty = any(report["empty_classes"][split] for split in ["train", "val", "test"])
    report["is_valid"] = bool(report["class_names_matches"] and not has_missing and not has_empty)
    return report


def main() -> None:
    """命令行入口：解析参数并执行数据准备或验证。"""
    parser = argparse.ArgumentParser(description="准备 NutriSnap Food-101 子集。")
    parser.add_argument("--source-root", default="dataset/food101_raw/food-101/images")
    parser.add_argument("--raw-root", default="dataset/food101_raw")
    parser.add_argument("--output-root", default="dataset/food101_subset")
    parser.add_argument("--limit-per-class", type=int, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--download", action="store_true", help="先使用 torchvision 下载 Food-101。")
    parser.add_argument("--validate-only", action="store_true", help="仅验证已准备的子集。")
    parser.add_argument("--report-json", default=None, help="可选的验收报告 JSON 输出路径。")
    args = parser.parse_args()
    source_root = args.source_root
    if args.download and not args.validate_only:
        source_root = download_food101_raw(args.raw_root)
    if not args.validate_only:
        prepare_food101_subset(source_root, args.output_root, args.limit_per_class, args.seed)
    report = validate_food101_subset(args.output_root)
    report_text = json.dumps(report, ensure_ascii=False, indent=2)
    print(report_text)
    if args.report_json:
        Path(args.report_json).write_text(report_text, encoding="utf-8")


if __name__ == "__main__":
    main()
