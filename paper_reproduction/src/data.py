from __future__ import annotations

from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset


class NiftiDataset(Dataset):
    def __init__(
        self,
        manifest: pd.DataFrame,
        split: str,
        augment: bool = False,
        seed: int = 2026,
    ) -> None:
        self.frame = manifest.loc[manifest["split"] == split].reset_index(drop=True).copy()
        if self.frame.empty:
            raise ValueError(f"No rows for split={split!r}")
        if "qc_pass" in self.frame and not self.frame["qc_pass"].map(_as_bool).all():
            bad = self.frame.loc[~self.frame["qc_pass"].map(_as_bool), "image_id"].tolist()
            raise ValueError(f"QC-failed rows in {split}: {bad[:10]}")
        self.augment = augment
        self.seed = seed

    def __len__(self) -> int:
        return len(self.frame)

    def __getitem__(self, index: int) -> dict[str, object]:
        row = self.frame.iloc[index]
        volume = np.asarray(nib.load(str(Path(row["path"]))).dataobj, dtype=np.float32)
        if volume.shape != (56, 56, 56):
            raise ValueError(f"Unexpected shape {volume.shape} for {row['path']}")
        if not np.isfinite(volume).all():
            raise ValueError(f"Non-finite volume: {row['path']}")
        if self.augment:
            rng = np.random.default_rng(self.seed + index + int(torch.initial_seed() % 1_000_000))
            scale = rng.uniform(0.95, 1.05)
            shift = rng.uniform(-0.05, 0.05)
            volume = volume * scale + shift
            if rng.random() < 0.35:
                volume = volume + rng.normal(0.0, 0.02, size=volume.shape).astype(np.float32)
        tensor = torch.from_numpy(np.ascontiguousarray(volume[None, ...]))
        return {
            "image": tensor,
            "label": torch.tensor(int(row["label"]), dtype=torch.long),
            "image_id": str(row["image_id"]),
            "subject": str(row["subject"]),
            "group": str(row["group"]),
            "split": str(row["split"]),
        }


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}

