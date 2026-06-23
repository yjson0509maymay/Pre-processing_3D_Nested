# PPMI T2 MRI paper reproduction

This directory turns the Scientific Reports paper
"Bio-inspired feature selection for early diagnosis of Parkinson's disease
through optimization of deep 3D nested learning" (2024) into a reproducible
experiment.

The code intentionally separates two goals:

1. `paper_like`: approximate the architecture and comparisons described in the paper.
2. `strict`: prevent subject leakage and keep the test set untouched until the end.

Use `strict` results as the main scientific result. Treat `paper_like` as a
methodological reproduction only.

## Data expected

- Cohort CSV with `Image Data ID`, `Subject`, and `Group` columns.
- One preprocessed NIfTI per row, named like
  `sub-3001_I224573.nii.gz`.
- Final volume shape: `56 x 56 x 56`.
- Labels: `Control`, `Prodromal`, and `PD`.

The current preprocessing output was observed at:

```text
E:\ppmi_dti\preprocessed\t2_paper_303\06_resized
```

All paths are command-line arguments, so the project can be copied to the GPU
computer without editing source code.

## Setup on the GPU computer

```bash
python -m venv .venv
# Activate the environment, then install a CUDA-compatible PyTorch build first.
pip install -r requirements.txt
```

## 1. Build and audit the manifest

```bash
python -m src.build_manifest \
  --cohort-csv /path/to/T2_final_cohort_303_unique_subjects.csv \
  --image-dir /path/to/t2_paper_303/06_resized \
  --output-dir runs/manifest \
  --seed 2026
```

This creates:

- `dataset_manifest.csv`: file mapping, labels, QC fields, and fixed split.
- `dataset_audit.json`: counts, missing files, duplicate subjects, and QC summary.

Do not start training unless missing files, duplicate subjects, non-finite
volumes, and shape failures are all zero.

## 2. Train the two imaging models

Run from the `paper_reproduction` directory:

```bash
python -m src.train \
  --manifest runs/manifest/dataset_manifest.csv \
  --model paper_cnn \
  --output-dir runs/paper_cnn \
  --seed 2026

python -m src.train \
  --manifest runs/manifest/dataset_manifest.csv \
  --model resnet3d \
  --output-dir runs/resnet3d \
  --seed 2026
```

For a quick pipeline check, append `--epochs 2 --num-workers 0`.

## 3. Extract features

```bash
python -m src.extract_features \
  --manifest runs/manifest/dataset_manifest.csv \
  --checkpoint runs/paper_cnn/best.pt \
  --output runs/features_cnn.npz

python -m src.extract_features \
  --manifest runs/manifest/dataset_manifest.csv \
  --checkpoint runs/resnet3d/best.pt \
  --output runs/features_resnet.npz
```

## 4. CCA fusion and classical classifiers

```bash
python -m src.fuse_features \
  --cnn-features runs/features_cnn.npz \
  --resnet-features runs/features_resnet.npz \
  --output-dir runs/fusion \
  --seed 2026
```

CCA, scaling, and dimensionality reduction are fit on the training set only.
The classifier is selected on validation macro-F1 and evaluated once on test.

## 5. Optional WOA feature selection

Run this only after the non-optimized fusion pipeline is stable:

```bash
python -m src.woa_feature_selection \
  --features runs/fusion/fused_features.npz \
  --output-dir runs/woa \
  --population 100 \
  --iterations 200 \
  --independent-runs 20 \
  --seed 2026
```

Those paper-like settings are computationally expensive. For a smoke test use
`--population 5 --iterations 2 --independent-runs 1`.

## Outputs that must be retained

- Manifest and audit JSON
- Exact command/configuration
- Best checkpoint and training history
- Per-subject predictions
- Confusion matrix and class-wise metrics
- Software versions, seed, and GPU model

See `PAPER_ANALYSIS_AND_EXPERIMENT_DESIGN.md` for the rationale, planned
experiments, and deviations from the paper.
