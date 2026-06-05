from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import torch
from torch import nn, optim
from torch.utils.data import DataLoader


def _load_torchvision_training_tools():
    try:
        from torchvision import datasets, models, transforms
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Training requires torchvision. Install dependencies with: pip install -r requirements.txt"
        ) from exc
    return datasets, models, transforms


def build_transforms():
    _, _, transforms = _load_torchvision_training_tools()
    train_transform = transforms.Compose(
        [
            transforms.RandomResizedCrop(224),
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.15),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
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
    _, models, _ = _load_torchvision_training_tools()
    weights = models.ResNet18_Weights.DEFAULT
    model = models.resnet18(weights=weights)
    if freeze_backbone:
        for parameter in model.parameters():
            parameter.requires_grad = False
    model.fc = nn.Linear(model.fc.in_features, num_classes)
    return model


def _make_loaders(dataset_root: Path, batch_size: int, num_workers: int):
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
            shuffle=(split == "train"),
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
    dataset_root = Path(dataset_root)
    output_model = Path(output_model)
    output_classes = Path(output_classes)
    if not (dataset_root / "train").exists() or not (dataset_root / "val").exists():
        raise FileNotFoundError(
            "Dataset must contain train/ and val/ directories. Run prepare_food101_subset.py first."
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
            print(f"{split}: loss={epoch_loss:.4f} accuracy={epoch_accuracy:.4f}")
            if split == "val" and epoch_accuracy > best_accuracy:
                best_accuracy = epoch_accuracy
                best_model_state = copy.deepcopy(model.state_dict())

    output_model.parent.mkdir(parents=True, exist_ok=True)
    output_classes.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model_state_dict": best_model_state, "class_names": class_names}, output_model)
    with output_classes.open("w", encoding="utf-8") as file:
        json.dump(class_names, file, ensure_ascii=False, indent=2)
    return {"best_val_accuracy": round(best_accuracy, 4)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Train ResNet18 for the NutriSnap Food-101 subset.")
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
