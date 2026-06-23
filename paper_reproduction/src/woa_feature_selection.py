from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.neighbors import KNeighborsClassifier

from .fuse_features import make_classifiers
from .train import classification_metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train-only binary Whale Optimization feature selection.")
    parser.add_argument("--features", type=Path, required=True, help="fused_features.npz")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--population", type=int, default=30)
    parser.add_argument("--iterations", type=int, default=50)
    parser.add_argument("--independent-runs", type=int, default=5)
    parser.add_argument("--alpha", type=float, default=0.99, help="Weight on CV classification error")
    parser.add_argument("--cv-folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=2026)
    return parser.parse_args()


def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


def binary_mask(position: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    mask = rng.random(position.shape) < sigmoid(position)
    if not mask.any():
        mask[rng.integers(0, len(mask))] = True
    return mask


def fitness(mask: np.ndarray, x: np.ndarray, y: np.ndarray, alpha: float, cv) -> float:
    classifier = KNeighborsClassifier(n_neighbors=5, weights="distance")
    accuracy = cross_val_score(classifier, x[:, mask], y, cv=cv, scoring="balanced_accuracy", n_jobs=-1).mean()
    return alpha * (1.0 - accuracy) + (1.0 - alpha) * (mask.sum() / len(mask))


def optimize(x: np.ndarray, y: np.ndarray, args: argparse.Namespace, run: int):
    rng = np.random.default_rng(args.seed + run)
    population = rng.uniform(-2, 2, size=(args.population, x.shape[1]))
    cv = StratifiedKFold(args.cv_folds, shuffle=True, random_state=args.seed + run)
    best_position = population[0].copy()
    best_mask = binary_mask(best_position, rng)
    best_fitness = fitness(best_mask, x, y, args.alpha, cv)
    curve = []
    for iteration in range(args.iterations):
        a = 2.0 - 2.0 * iteration / max(args.iterations - 1, 1)
        for i in range(args.population):
            mask = binary_mask(population[i], rng)
            score = fitness(mask, x, y, args.alpha, cv)
            if score < best_fitness:
                best_fitness, best_position, best_mask = score, population[i].copy(), mask.copy()
        for i in range(args.population):
            r1, r2 = rng.random(), rng.random()
            A, C = 2 * a * r1 - a, 2 * r2
            if rng.random() < 0.5:
                reference = best_position if abs(A) < 1 else population[rng.integers(args.population)]
                distance = np.abs(C * reference - population[i])
                population[i] = reference - A * distance
            else:
                distance = np.abs(best_position - population[i])
                spiral = rng.uniform(-1, 1)
                population[i] = distance * np.exp(spiral) * np.cos(2 * np.pi * spiral) + best_position
            population[i] = np.clip(population[i], -8, 8)
        curve.append(best_fitness)
        print(json.dumps({"run": run, "iteration": iteration + 1, "fitness": best_fitness, "features": int(best_mask.sum())}))
    return best_mask, best_fitness, curve


def main() -> None:
    args = parse_args()
    with np.load(args.features, allow_pickle=False) as data:
        x = data["features"].astype(np.float64)
        y = data["labels"].astype(int)
        splits = data["splits"].astype(str)
        image_ids = data["image_ids"].astype(str)
    train, val, test = splits == "train", splits == "val", splits == "test"
    candidates = [optimize(x[train], y[train], args, run) for run in range(args.independent_runs)]
    selected_mask, selected_fitness, curve = min(candidates, key=lambda item: item[1])

    classifiers = make_classifiers(args.seed)
    validation_results = {}
    prediction_rows = []
    for name, classifier in classifiers.items():
        classifier.fit(x[train][:, selected_mask], y[train])
        pred = classifier.predict(x[val][:, selected_mask])
        validation_results[name] = classification_metrics(y[val].tolist(), pred.tolist())
        for image_id, truth, predicted in zip(image_ids[val], y[val], pred):
            prediction_rows.append({
                "classifier": name,
                "image_id": image_id,
                "split": "val",
                "true_label": int(truth),
                "predicted_label": int(predicted),
            })
    selected_classifier = max(
        validation_results, key=lambda name: validation_results[name]["macro_f1"]
    )
    selected_model = classifiers[selected_classifier]
    test_pred = selected_model.predict(x[test][:, selected_mask])
    test_result = classification_metrics(y[test].tolist(), test_pred.tolist())
    for image_id, truth, predicted in zip(image_ids[test], y[test], test_pred):
        prediction_rows.append({
            "classifier": selected_classifier,
            "image_id": image_id,
            "split": "test",
            "true_label": int(truth),
            "predicted_label": int(predicted),
        })

    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "selected_feature_count": int(selected_mask.sum()),
        "total_feature_count": int(len(selected_mask)),
        "training_cv_fitness": float(selected_fitness),
        "selected_classifier": selected_classifier,
        "selection_rule": "highest validation macro_f1",
        "test_used_for_selection": False,
        "parameters": vars(args),
        "validation_by_classifier": validation_results,
        "test": test_result,
    }
    report["parameters"] = {k: str(v) if isinstance(v, Path) else v for k, v in report["parameters"].items()}
    (args.output_dir / "metrics.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    np.save(args.output_dir / "selected_mask.npy", selected_mask)
    np.save(args.output_dir / "convergence.npy", np.asarray(curve))
    import pandas as pd
    pd.DataFrame(prediction_rows).to_csv(args.output_dir / "predictions.csv", index=False)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
