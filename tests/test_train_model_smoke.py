from __future__ import annotations

import json

import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from train import train_model as train_module


class TinyDataset:
    classes = ["pizza", "sushi"]


def test_train_model_runs_smoke_training_and_writes_outputs(tmp_path, monkeypatch):
    dataset_root = tmp_path / "dataset"
    (dataset_root / "train").mkdir(parents=True)
    (dataset_root / "val").mkdir(parents=True)
    output_model = tmp_path / "models" / "food_resnet18.pth"
    output_classes = tmp_path / "models" / "class_names.json"

    inputs = torch.randn(4, 3, 8, 8)
    labels = torch.tensor([0, 1, 0, 1])

    def fake_make_loaders(dataset_root_arg, batch_size, num_workers):
        assert dataset_root_arg == dataset_root
        assert batch_size == 2
        assert num_workers == 0
        loader = DataLoader(TensorDataset(inputs, labels), batch_size=batch_size)
        return {"train": TinyDataset(), "val": TinyDataset()}, {"train": loader, "val": loader}

    def fake_build_model(num_classes, freeze_backbone=True):
        assert num_classes == 2
        return nn.Sequential(nn.Flatten(), nn.Linear(3 * 8 * 8, num_classes))

    monkeypatch.setattr(train_module, "_make_loaders", fake_make_loaders)
    monkeypatch.setattr(train_module, "build_model", fake_build_model)

    result = train_module.train_model(
        dataset_root=dataset_root,
        output_model=output_model,
        output_classes=output_classes,
        epochs=1,
        batch_size=2,
        learning_rate=0.001,
        num_workers=0,
    )

    assert "best_val_accuracy" in result
    assert output_model.exists()
    assert json.loads(output_classes.read_text(encoding="utf-8")) == ["pizza", "sushi"]
