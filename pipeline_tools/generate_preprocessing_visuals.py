import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np


STAGES = [
    ("01_raw_nifti", "Raw NIfTI"),
    ("02_bet", "Brain extraction (BET)"),
    ("03_n4", "N4 bias correction"),
    ("04_mni152_affine", "MNI152 affine registration"),
    ("05_ants_nonlinear", "ANTs SyN non-linear registration"),
    ("06_normalized", "Intensity normalization"),
    ("07_resized", "Resize 56 x 56 x 56"),
]


def load_volume(path):
    data = nib.load(path).get_fdata(dtype=np.float32)
    data = np.nan_to_num(data)
    nonzero = data[data != 0]
    values = nonzero if nonzero.size else data.ravel()
    low, high = np.percentile(values, [1, 99])
    if high <= low:
        high = low + 1
    return np.clip((data - low) / (high - low), 0, 1)


def slices(volume):
    x, y, z = [size // 2 for size in volume.shape]
    return [
        np.rot90(volume[x, :, :]),
        np.rot90(volume[:, y, :]),
        np.rot90(volume[:, :, z]),
    ]


def save_montage(volume, title, path):
    fig, axes = plt.subplots(1, 3, figsize=(12, 4), facecolor="white")
    for axis, image, plane in zip(axes, slices(volume), ["Sagittal", "Coronal", "Axial"]):
        axis.imshow(image, cmap="gray", vmin=0, vmax=1)
        axis.set_title(plane, fontsize=11)
        axis.axis("off")
    fig.suptitle(title, fontsize=16, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.9])
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def save_pair(before, after, title, path):
    fig, axes = plt.subplots(2, 3, figsize=(12, 7), facecolor="white")
    for column, (plane, before_slice, after_slice) in enumerate(
        zip(["Sagittal", "Coronal", "Axial"], slices(before), slices(after))
    ):
        axes[0, column].imshow(before_slice, cmap="gray", vmin=0, vmax=1)
        axes[0, column].set_title(f"Before - {plane}", fontsize=10)
        axes[1, column].imshow(after_slice, cmap="gray", vmin=0, vmax=1)
        axes[1, column].set_title(f"After - {plane}", fontsize=10)
        axes[0, column].axis("off")
        axes[1, column].axis("off")
    fig.suptitle(title, fontsize=16, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def save_pipeline(volumes, path):
    fig, axes = plt.subplots(2, 3, figsize=(15, 9), facecolor="white")
    for axis, ((_, title), volume) in zip(axes.ravel(), zip(STAGES, volumes)):
        axis.imshow(slices(volume)[2], cmap="gray", vmin=0, vmax=1)
        axis.set_title(title, fontsize=12, fontweight="bold")
        axis.axis("off")
    fig.suptitle("T2 MRI Preprocessing Pipeline", fontsize=20, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(path, dpi=240, bbox_inches="tight")
    plt.close(fig)


def find_sample(output_root, requested):
    if requested:
        return requested
    final_dir = Path(output_root) / "07_resized"
    candidates = sorted(final_dir.glob("sub-*.nii.gz"))
    if not candidates:
        raise RuntimeError("No completed sample found in 07_resized")
    return candidates[0].name.removesuffix(".nii.gz")


def main():
    parser = argparse.ArgumentParser(description="Generate preprocessing before/after figures.")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--sample-id", default="")
    args = parser.parse_args()

    sample_id = find_sample(args.output_root, args.sample_id)
    output_dir = Path(args.output_root) / "visualization" / sample_id
    output_dir.mkdir(parents=True, exist_ok=True)
    volumes = []
    for stage, _ in STAGES:
        path = Path(args.output_root) / stage / f"{sample_id}.nii.gz"
        if not path.exists():
            raise RuntimeError(f"Missing stage output: {path}")
        volumes.append(load_volume(path))

    save_montage(volumes[0], "01 Raw NIfTI", output_dir / "01_raw.png")
    for index in range(1, len(STAGES)):
        stage, title = STAGES[index]
        prefix = f"{index + 1:02d}_{stage.split('_', 1)[1]}"
        save_montage(volumes[index - 1], f"{title} - Before", output_dir / f"{prefix}_before.png")
        save_montage(volumes[index], f"{title} - After", output_dir / f"{prefix}_after.png")
        save_pair(
            volumes[index - 1],
            volumes[index],
            title,
            output_dir / f"PPT_{prefix}_before_after.png",
        )
    save_montage(volumes[-1], "Final Preprocessed T2 MRI", output_dir / "final_preprocessed.png")
    save_pipeline(volumes, output_dir / "PPT_full_pipeline_overview.png")

    readme = f"""# Preprocessing visualization - {sample_id}\n\nPurpose: Track one subject through every preprocessing stage.\n\nInput: stage NIfTI files from `01_raw_nifti` through `07_resized`.\n\nOutput: individual before/after montages and PPT-ready comparison figures.\n\n`PPT_full_pipeline_overview.png` is the recommended single-slide overview.\n"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")
    print(f"Visualization sample: {sample_id}")
    print(f"Output: {output_dir}")


if __name__ == "__main__":
    main()
