from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

from .data import NiftiDataset
from .models import build_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract 1,000-D deep features.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    device = torch.device(args.device)
    checkpoint = torch.load(args.checkpoint, map_location=device, weights_only=False)
    model = build_model(checkpoint["model_name"]).to(device)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    manifest = pd.read_csv(args.manifest, dtype={"subject": str, "image_id": str})

    all_features, all_labels, all_ids, all_subjects, all_splits = [], [], [], [], []
    with torch.no_grad():
        for split in ("train", "val", "test"):
            dataset = NiftiDataset(manifest, split, augment=False)
            loader = DataLoader(
                dataset, batch_size=args.batch_size, shuffle=False,
                num_workers=args.num_workers, pin_memory=device.type == "cuda"
            )
            for batch in loader:
                _, features = model(batch["image"].to(device), return_features=True)
                all_features.append(features.cpu().numpy().astype(np.float32))
                all_labels.extend(batch["label"].numpy().tolist())
                all_ids.extend(batch["image_id"])
                all_subjects.extend(batch["subject"])
                all_splits.extend(batch["split"])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.output,
        features=np.concatenate(all_features),
        labels=np.asarray(all_labels, dtype=np.int64),
        image_ids=np.asarray(all_ids),
        subjects=np.asarray(all_subjects),
        splits=np.asarray(all_splits),
        model_name=np.asarray(checkpoint["model_name"]),
    )
    print(f"Saved {len(all_ids)} rows x {all_features[0].shape[1]} features to {args.output}")


if __name__ == "__main__":
    main()

