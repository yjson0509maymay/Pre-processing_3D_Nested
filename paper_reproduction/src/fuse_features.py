from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cross_decomposition import CCA
from sklearn.decomposition import PCA
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from .train import classification_metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train-only PCA/CCA feature fusion.")
    parser.add_argument("--cnn-features", type=Path, required=True)
    parser.add_argument("--resnet-features", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--pca-components", type=int, default=64)
    parser.add_argument("--cca-components", type=int, default=32)
    parser.add_argument("--seed", type=int, default=2026)
    return parser.parse_args()


def load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key] for key in data.files}


def assert_aligned(left: dict[str, np.ndarray], right: dict[str, np.ndarray]) -> None:
    for key in ("image_ids", "subjects", "labels", "splits"):
        if not np.array_equal(left[key], right[key]):
            raise ValueError(f"Feature files are not aligned on {key}")


def make_classifiers(seed: int):
    return {
        "svm": SVC(C=1.0, kernel="rbf", class_weight="balanced", probability=True, random_state=seed),
        "knn": KNeighborsClassifier(n_neighbors=5, weights="distance"),
        "random_forest": RandomForestClassifier(
            n_estimators=500, class_weight="balanced", random_state=seed, n_jobs=-1
        ),
        "gradient_boosting": GradientBoostingClassifier(random_state=seed),
    }


def main() -> None:
    args = parse_args()
    cnn = load_npz(args.cnn_features)
    resnet = load_npz(args.resnet_features)
    assert_aligned(cnn, resnet)
    x1 = cnn["features"].astype(np.float64)
    x2 = resnet["features"].astype(np.float64)
    y = cnn["labels"].astype(int)
    splits = cnn["splits"].astype(str)
    masks = {name: splits == name for name in ("train", "val", "test")}
    if any(not mask.any() for mask in masks.values()):
        raise ValueError("train, val, and test rows are all required")

    # Every learned transform is fit on training subjects only.
    scale1, scale2 = StandardScaler(), StandardScaler()
    x1_train = scale1.fit_transform(x1[masks["train"]])
    x2_train = scale2.fit_transform(x2[masks["train"]])
    max_pca = min(args.pca_components, x1_train.shape[0] - 1, x1_train.shape[1], x2_train.shape[1])
    pca1 = PCA(n_components=max_pca, whiten=True, random_state=args.seed)
    pca2 = PCA(n_components=max_pca, whiten=True, random_state=args.seed)
    pca1.fit(x1_train)
    pca2.fit(x2_train)
    transformed1 = pca1.transform(scale1.transform(x1))
    transformed2 = pca2.transform(scale2.transform(x2))

    cca_components = min(args.cca_components, max_pca, masks["train"].sum() - 1)
    cca = CCA(n_components=cca_components, max_iter=2000, tol=1e-6)
    cca.fit(transformed1[masks["train"]], transformed2[masks["train"]])
    canonical1, canonical2 = cca.transform(transformed1, transformed2)
    fused = np.concatenate([canonical1, canonical2], axis=1).astype(np.float32)

    results = {}
    predictions = []
    trained = {}
    for name, classifier in make_classifiers(args.seed).items():
        classifier.fit(fused[masks["train"]], y[masks["train"]])
        trained[name] = classifier
        results[name] = {}
        for split in ("val", "test"):
            pred = classifier.predict(fused[masks[split]])
            results[name][split] = classification_metrics(y[masks[split]].tolist(), pred.tolist())
            split_indices = np.flatnonzero(masks[split])
            for index, prediction in zip(split_indices, pred):
                predictions.append({
                    "classifier": name,
                    "image_id": str(cnn["image_ids"][index]),
                    "subject": str(cnn["subjects"][index]),
                    "split": split,
                    "true_label": int(y[index]),
                    "predicted_label": int(prediction),
                })

    selected = max(results, key=lambda name: results[name]["val"]["macro_f1"])
    report = {
        "selection_rule": "highest validation macro_f1",
        "selected_classifier": selected,
        "test_used_for_selection": False,
        "pca_components": max_pca,
        "cca_components": cca_components,
        "results": results,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "metrics.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    pd.DataFrame(predictions).to_csv(args.output_dir / "predictions.csv", index=False)
    np.savez_compressed(
        args.output_dir / "fused_features.npz",
        features=fused,
        labels=y,
        image_ids=cnn["image_ids"],
        subjects=cnn["subjects"],
        splits=cnn["splits"],
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

