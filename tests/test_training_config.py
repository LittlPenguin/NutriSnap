from __future__ import annotations

import json

from train.prepare_food101_subset import FOOD101_SUBSET_CLASSES, split_indices, validate_food101_subset


def test_food101_subset_has_expected_12_classes():
    assert FOOD101_SUBSET_CLASSES == [
        "apple_pie",
        "baby_back_ribs",
        "beef_carpaccio",
        "caesar_salad",
        "cheesecake",
        "chicken_curry",
        "dumplings",
        "french_fries",
        "hamburger",
        "pizza",
        "ramen",
        "sushi",
    ]


def test_split_indices_uses_70_15_15_ratio():
    train_idx, val_idx, test_idx = split_indices(list(range(100)), seed=42)

    assert len(train_idx) == 70
    assert len(val_idx) == 15
    assert len(test_idx) == 15
    assert set(train_idx).isdisjoint(val_idx)
    assert set(train_idx).isdisjoint(test_idx)
    assert set(val_idx).isdisjoint(test_idx)


def test_validate_food101_subset_reports_split_counts(tmp_path):
    subset_root = tmp_path / "food101_subset"
    for split in ["train", "val", "test"]:
        for class_name in FOOD101_SUBSET_CLASSES:
            class_dir = subset_root / split / class_name
            class_dir.mkdir(parents=True)
            for index in range({"train": 2, "val": 1, "test": 1}[split]):
                (class_dir / f"{index}.jpg").write_bytes(b"fake-image")
    (subset_root / "class_names.json").write_text(json.dumps(FOOD101_SUBSET_CLASSES), encoding="utf-8")

    report = validate_food101_subset(subset_root)

    assert report["is_valid"] is True
    assert report["total_images"] == len(FOOD101_SUBSET_CLASSES) * 4
    assert report["class_names_matches"] is True
    assert report["missing_classes"] == {"train": [], "val": [], "test": []}
    assert report["splits"]["train"]["pizza"] == 2
    assert report["splits"]["val"]["pizza"] == 1
    assert report["splits"]["test"]["pizza"] == 1


def test_validate_food101_subset_flags_missing_class_and_empty_split(tmp_path):
    subset_root = tmp_path / "food101_subset"
    for split in ["train", "val", "test"]:
        for class_name in FOOD101_SUBSET_CLASSES:
            if split == "val" and class_name == "pizza":
                continue
            (subset_root / split / class_name).mkdir(parents=True)
    (subset_root / "class_names.json").write_text(json.dumps(["pizza"]), encoding="utf-8")

    report = validate_food101_subset(subset_root)

    assert report["is_valid"] is False
    assert "pizza" in report["missing_classes"]["val"]
    assert report["empty_classes"]["train"] == FOOD101_SUBSET_CLASSES
    assert report["class_names_matches"] is False
