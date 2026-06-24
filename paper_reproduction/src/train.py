from __future__ import annotations

import argparse
import json
import platform
import random
import time
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
import torch
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)
from torch import nn
from torch.utils.data import DataLoader

from . import INDEX_TO_LABEL
from .data import NiftiDataset
from .models import build_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a leakage-aware 3D MRI classifier.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--model", choices=["paper_cnn", "resnet3d"], required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--patience", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=None)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--no-augment", action="store_true")
    return parser.parse_args()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


def worker_seed(worker_id: int) -> None:
    seed = torch.initial_seed() % (2**32)
    np.random.seed(seed)
    random.seed(seed)


def make_loader(dataset: NiftiDataset, batch_size: int, workers: int, shuffle: bool, seed: int) -> DataLoader:
    generator = torch.Generator().manual_seed(seed)
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=workers,
        pin_memory=torch.cuda.is_available(),
        persistent_workers=workers > 0,
        worker_init_fn=worker_seed,
        generator=generator,
    )


def elapsed_since(started: float, device: torch.device | None = None) -> float:
    if device is not None and device.type == "cuda":
        torch.cuda.synchronize(device)
    return time.perf_counter() - started


def classification_metrics(y_true: list[int], y_pred: list[int]) -> dict[str, object]:
    labels = [0, 1, 2]
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, zero_division=0
    )
    per_class = {}
    for i, label in enumerate(labels):
        tn = cm.sum() - (cm[i, :].sum() + cm[:, i].sum() - cm[i, i])
        fp = cm[:, i].sum() - cm[i, i]
        specificity = float(tn / (tn + fp)) if (tn + fp) else 0.0
        per_class[INDEX_TO_LABEL[label]] = {
            "precision": float(precision[i]),
            "recall_sensitivity": float(recall[i]),
            "specificity": specificity,
            "f1": float(f1[i]),
            "support": int(support[i]),
        }
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro")),
        "weighted_f1": float(f1_score(y_true, y_pred, average="weighted")),
        "confusion_matrix": cm.tolist(),
        "per_class": per_class,
    }


@torch.no_grad()
def evaluate(model: nn.Module, loader: DataLoader, criterion: nn.Module, device: torch.device):
    model.eval()
    total_loss = 0.0
    y_true: list[int] = []
    y_pred: list[int] = []
    prediction_rows: list[dict[str, object]] = []
    for batch in loader:
        images = batch["image"].to(device, non_blocking=True)
        labels = batch["label"].to(device, non_blocking=True)
        logits = model(images)
        loss = criterion(logits, labels)
        probabilities = torch.softmax(logits, dim=1)
        predictions = probabilities.argmax(dim=1)
        total_loss += float(loss.item()) * labels.size(0)
        y_true.extend(labels.cpu().tolist())
        y_pred.extend(predictions.cpu().tolist())
        probs = probabilities.cpu().numpy()
        for i in range(labels.size(0)):
            prediction_rows.append({
                "image_id": batch["image_id"][i],
                "subject": batch["subject"][i],
                "group": batch["group"][i],
                "split": batch["split"][i],
                "true_label": int(labels[i].item()),
                "predicted_label": int(predictions[i].item()),
                "prob_control": float(probs[i, 0]),
                "prob_prodromal": float(probs[i, 1]),
                "prob_pd": float(probs[i, 2]),
            })
    metrics = classification_metrics(y_true, y_pred)
    metrics["loss"] = total_loss / len(loader.dataset)
    return metrics, prediction_rows


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = pd.read_csv(args.manifest, dtype={"subject": str, "image_id": str})
    required_splits = {"train", "val", "test"}
    if set(manifest["split"]) != required_splits:
        raise ValueError(f"Manifest must contain exactly {required_splits}")

    train_ds = NiftiDataset(manifest, "train", augment=not args.no_augment, seed=args.seed)
    val_ds = NiftiDataset(manifest, "val", augment=False, seed=args.seed)
    test_ds = NiftiDataset(manifest, "test", augment=False, seed=args.seed)
    train_loader = make_loader(train_ds, args.batch_size, args.num_workers, True, args.seed)
    val_loader = make_loader(val_ds, args.batch_size, args.num_workers, False, args.seed)
    test_loader = make_loader(test_ds, args.batch_size, args.num_workers, False, args.seed)

    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    model = build_model(args.model).to(device)
    learning_rate = args.learning_rate or (1e-3 if args.model == "paper_cnn" else 1e-4)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="max", factor=0.5, patience=5)

    counts = train_ds.frame["label"].value_counts().reindex([0, 1, 2]).to_numpy(dtype=float)
    class_weights = counts.sum() / (len(counts) * counts)
    criterion = nn.CrossEntropyLoss(weight=torch.tensor(class_weights, dtype=torch.float32, device=device))
    scaler = torch.cuda.amp.GradScaler(enabled=device.type == "cuda")

    config = vars(args).copy()
    config.update({
        "manifest": str(args.manifest.resolve()),
        "output_dir": str(args.output_dir.resolve()),
        "learning_rate_resolved": learning_rate,
        "class_weights": class_weights.tolist(),
        "split_counts": manifest.groupby(["split", "group"]).size().unstack(fill_value=0).to_dict(orient="index"),
        "environment": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "sklearn": sklearn.__version__,
            "cuda_available": torch.cuda.is_available(),
            "cuda_version": torch.version.cuda,
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        },
    })
    (args.output_dir / "config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    history = []
    best_score = -np.inf
    stale_epochs = 0
    started = time.perf_counter()
    for epoch in range(1, args.epochs + 1):
        epoch_started = time.perf_counter()
        model.train()
        running_loss = 0.0
        train_started = time.perf_counter()
        for batch in train_loader:
            images = batch["image"].to(device, non_blocking=True)
            labels = batch["label"].to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type, enabled=device.type == "cuda"):
                logits = model(images)
                loss = criterion(logits, labels)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            running_loss += float(loss.item()) * labels.size(0)
        train_seconds = elapsed_since(train_started, device)

        val_started = time.perf_counter()
        val_metrics, _ = evaluate(model, val_loader, criterion, device)
        val_seconds = elapsed_since(val_started, device)

        bookkeeping_started = time.perf_counter()
        scheduler.step(val_metrics["macro_f1"])
        row = {
            "epoch": epoch,
            "train_loss": running_loss / len(train_ds),
            "val_loss": val_metrics["loss"],
            "val_accuracy": val_metrics["accuracy"],
            "val_balanced_accuracy": val_metrics["balanced_accuracy"],
            "val_macro_f1": val_metrics["macro_f1"],
            "learning_rate": optimizer.param_groups[0]["lr"],
            "train_seconds": round(train_seconds, 3),
            "validation_seconds": round(val_seconds, 3),
        }
        checkpoint_started = None

        if val_metrics["macro_f1"] > best_score + 1e-6:
            best_score = val_metrics["macro_f1"]
            stale_epochs = 0
            checkpoint_started = time.perf_counter()
            torch.save({
                "model_name": args.model,
                "state_dict": model.state_dict(),
                "epoch": epoch,
                "val_metrics": val_metrics,
                "seed": args.seed,
            }, args.output_dir / "best.pt")
            row["checkpoint_seconds"] = round(elapsed_since(checkpoint_started, device), 3)
        else:
            stale_epochs += 1
            row["checkpoint_seconds"] = 0.0

        row["bookkeeping_seconds"] = round(elapsed_since(bookkeeping_started, device), 3)
        row["epoch_total_seconds"] = round(elapsed_since(epoch_started, device), 3)
        row["process_seconds"] = {
            "train": row["train_seconds"],
            "validation": row["validation_seconds"],
            "bookkeeping": row["bookkeeping_seconds"],
            "checkpoint": row["checkpoint_seconds"],
            "epoch_total": row["epoch_total_seconds"],
        }
        history.append(row)
        pd.DataFrame(history).to_csv(args.output_dir / "history.csv", index=False)
        print(json.dumps(row), flush=True)

        if stale_epochs >= args.patience:
            break

    checkpoint = torch.load(args.output_dir / "best.pt", map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["state_dict"])
    final_eval_started = time.perf_counter()
    val_metrics, val_predictions = evaluate(model, val_loader, criterion, device)
    final_val_seconds = elapsed_since(final_eval_started, device)
    test_eval_started = time.perf_counter()
    test_metrics, test_predictions = evaluate(model, test_loader, criterion, device)
    final_test_seconds = elapsed_since(test_eval_started, device)
    final = {
        "best_epoch": checkpoint["epoch"],
        "validation": val_metrics,
        "test": test_metrics,
        "final_validation_seconds": round(final_val_seconds, 3),
        "final_test_seconds": round(final_test_seconds, 3),
        "elapsed_seconds": round(elapsed_since(started, device), 3),
        "test_used_for_selection": False,
    }
    (args.output_dir / "metrics.json").write_text(
        json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    pd.DataFrame(val_predictions + test_predictions).to_csv(
        args.output_dir / "predictions.csv", index=False
    )
    print(json.dumps(final, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
