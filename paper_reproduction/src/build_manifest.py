from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from . import LABEL_TO_INDEX


FILE_RE = re.compile(r"^sub-(?P<subject>[^_]+)_(?P<image_id>I\d+)\.nii\.gz$")
EXPECTED_SHAPE = (56, 56, 56)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and audit a locked MRI manifest.")
    parser.add_argument("--cohort-csv", type=Path, required=True)
    parser.add_argument("--image-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--skip-volume-qc", action="store_true")
    return parser.parse_args()


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return text[:-2] if text.endswith(".0") else text


def index_images(image_dir: Path) -> tuple[dict[str, Path], list[str]]:
    by_image_id: dict[str, Path] = {}
    malformed: list[str] = []
    for path in sorted(image_dir.glob("*.nii.gz")):
        match = FILE_RE.match(path.name)
        if not match:
            malformed.append(path.name)
            continue
        image_id = match.group("image_id")
        if image_id in by_image_id:
            raise ValueError(f"Duplicate NIfTI for {image_id}: {path} and {by_image_id[image_id]}")
        by_image_id[image_id] = path.resolve()
    return by_image_id, malformed


def inspect_volume(path: Path) -> dict[str, object]:
    try:
        image = nib.load(str(path))
        data = np.asarray(image.dataobj, dtype=np.float32)
        finite = bool(np.isfinite(data).all())
        finite_data = data[np.isfinite(data)]
        zooms = tuple(float(x) for x in image.header.get_zooms()[:3])
        return {
            "readable": True,
            "shape": "x".join(str(x) for x in data.shape),
            "shape_ok": tuple(data.shape) == EXPECTED_SHAPE,
            "voxel_spacing": "x".join(f"{x:.6g}" for x in zooms),
            "finite": finite,
            "mean": float(finite_data.mean()) if finite_data.size else None,
            "std": float(finite_data.std()) if finite_data.size else None,
            "nonzero_fraction": float(np.count_nonzero(data) / data.size) if data.size else 0.0,
            "qc_error": "",
        }
    except Exception as exc:  # audit must record failures instead of aborting early
        return {
            "readable": False,
            "shape": "",
            "shape_ok": False,
            "voxel_spacing": "",
            "finite": False,
            "mean": None,
            "std": None,
            "nonzero_fraction": None,
            "qc_error": repr(exc),
        }


def assign_split(frame: pd.DataFrame, seed: int) -> pd.Series:
    indices = np.arange(len(frame))
    train_idx, holdout_idx = train_test_split(
        indices,
        test_size=0.30,
        random_state=seed,
        stratify=frame["label"],
    )
    val_idx, test_idx = train_test_split(
        holdout_idx,
        test_size=0.50,
        random_state=seed + 1,
        stratify=frame.iloc[holdout_idx]["label"],
    )
    split = pd.Series("", index=frame.index, dtype="object")
    split.iloc[train_idx] = "train"
    split.iloc[val_idx] = "val"
    split.iloc[test_idx] = "test"
    return split


def main() -> None:
    args = parse_args()
    cohort = pd.read_csv(args.cohort_csv, dtype=str)
    required = {"Image Data ID", "Subject", "Group"}
    missing_columns = sorted(required.difference(cohort.columns))
    if missing_columns:
        raise ValueError(f"Missing cohort columns: {missing_columns}")

    cohort["image_id"] = cohort["Image Data ID"].map(clean_text)
    cohort["subject"] = cohort["Subject"].map(clean_text)
    cohort["group"] = cohort["Group"].map(clean_text)
    unknown_groups = sorted(set(cohort["group"]) - set(LABEL_TO_INDEX))
    if unknown_groups:
        raise ValueError(f"Unknown groups: {unknown_groups}")

    images, malformed = index_images(args.image_dir)
    cohort["path"] = cohort["image_id"].map(lambda x: str(images[x]) if x in images else "")
    cohort["file_exists"] = cohort["path"].ne("")
    cohort["label"] = cohort["group"].map(LABEL_TO_INDEX).astype(int)

    qc_rows = []
    for path_text in cohort["path"]:
        if not path_text:
            qc_rows.append({
                "readable": False, "shape": "", "shape_ok": False,
                "voxel_spacing": "", "finite": False, "mean": None,
                "std": None, "nonzero_fraction": None, "qc_error": "missing file",
            })
        elif args.skip_volume_qc:
            qc_rows.append({
                "readable": True, "shape": "not_checked", "shape_ok": True,
                "voxel_spacing": "not_checked", "finite": True, "mean": None,
                "std": None, "nonzero_fraction": None, "qc_error": "",
            })
        else:
            qc_rows.append(inspect_volume(Path(path_text)))
    qc = pd.DataFrame(qc_rows)
    output = pd.concat([cohort.reset_index(drop=True), qc], axis=1)

    duplicate_subjects = sorted(output.loc[output["subject"].duplicated(False), "subject"].unique())
    duplicate_images = sorted(output.loc[output["image_id"].duplicated(False), "image_id"].unique())
    output["split"] = assign_split(output, args.seed)

    valid = (
        output["file_exists"]
        & output["readable"]
        & output["shape_ok"]
        & output["finite"]
        & output["nonzero_fraction"].fillna(0).gt(0.01)
    )
    output["qc_pass"] = valid

    audit = {
        "cohort_csv": str(args.cohort_csv.resolve()),
        "image_dir": str(args.image_dir.resolve()),
        "seed": args.seed,
        "expected_shape": list(EXPECTED_SHAPE),
        "rows": int(len(output)),
        "indexed_nifti": int(len(images)),
        "malformed_filenames": malformed,
        "missing_files": output.loc[~output["file_exists"], "image_id"].tolist(),
        "duplicate_subjects": duplicate_subjects,
        "duplicate_image_ids": duplicate_images,
        "unreadable": output.loc[~output["readable"], "image_id"].tolist(),
        "shape_failures": output.loc[~output["shape_ok"], "image_id"].tolist(),
        "nonfinite": output.loc[~output["finite"], "image_id"].tolist(),
        "qc_pass": int(output["qc_pass"].sum()),
        "class_counts": output["group"].value_counts().sort_index().to_dict(),
        "split_counts": output.groupby(["split", "group"]).size().unstack(fill_value=0).to_dict(orient="index"),
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output_dir / "dataset_manifest.csv", index=False)
    (args.output_dir / "dataset_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))

    blockers = [
        audit["missing_files"], duplicate_subjects, duplicate_images,
        audit["unreadable"], audit["shape_failures"], audit["nonfinite"],
    ]
    if any(blockers):
        raise SystemExit("Audit failed. Resolve blockers before training.")


if __name__ == "__main__":
    main()

