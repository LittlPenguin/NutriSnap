from __future__ import annotations

from train.prepare_food101_subset import FOOD101_SUBSET_CLASSES, split_indices


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
