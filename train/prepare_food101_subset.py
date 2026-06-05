from __future__ import annotations

import argparse
import json
import random
import shutil
from pathlib import Path

from services.schemas import FOOD101_SUBSET_CLASSES


def split_indices(indices: list[int], seed: int = 42) -> tuple[list[int], list[int], list[int]]:
    shuffled = list(indices)
    random.Random(seed).shuffle(shuffled)
    train_end = int(len(shuffled) * 0.70)
    val_end = train_end + int(len(shuffled) * 0.15)
    return shuffled[:train_end], shuffled[train_end:val_end], shuffled[val_end:]


def prepare_food101_subset(
    source_root: str | Path = "dataset/food101_raw/food-101/images",
    output_root: str | Path = "dataset/food101_subset",
    limit_per_class: int | None = None,
    seed: int = 42,
) -> None:
    source_root = Path(source_root)
    output_root = Path(output_root)
    if not source_root.exists():
        raise FileNotFoundError(
            f"Food-101 image directory not found: {source_root}. "
            "Download Food-101 first or pass --source-root to an existing images directory."
        )

    for split in ["train", "val", "test"]:
        for class_name in FOOD101_SUBSET_CLASSES:
            (output_root / split / class_name).mkdir(parents=True, exist_ok=True)

    for class_name in FOOD101_SUBSET_CLASSES:
        class_dir = source_root / class_name
        if not class_dir.exists():
            raise FileNotFoundError(f"Missing Food-101 class directory: {class_dir}")
        images = sorted(class_dir.glob("*.jpg"))
        if limit_per_class is not None:
            images = images[:limit_per_class]
        train_idx, val_idx, test_idx = split_indices(list(range(len(images))), seed=seed)
        split_map = {"train": train_idx, "val": val_idx, "test": test_idx}
        for split, indices in split_map.items():
            for index in indices:
                shutil.copy2(images[index], output_root / split / class_name / images[index].name)

    with (output_root / "class_names.json").open("w", encoding="utf-8") as file:
        json.dump(FOOD101_SUBSET_CLASSES, file, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare the NutriSnap Food-101 subset.")
    parser.add_argument("--source-root", default="dataset/food101_raw/food-101/images")
    parser.add_argument("--output-root", default="dataset/food101_subset")
    parser.add_argument("--limit-per-class", type=int, default=None)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    prepare_food101_subset(args.source_root, args.output_root, args.limit_per_class, args.seed)


if __name__ == "__main__":
    main()
