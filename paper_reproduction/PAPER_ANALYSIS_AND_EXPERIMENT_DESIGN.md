# Paper analysis and experiment design

## 1. Paper being reproduced

- Priyadharshini et al., Scientific Reports 14, 23394 (2024)
- DOI: 10.1038/s41598-024-74405-5
- Task: three-class classification of Control, Prodromal, and Parkinson's
  disease from whole-brain T2-weighted MRI.
- Reported cohort: 303 images; Control 110, Prodromal 58, PD 135.
- Reported input: DICOM converted to NIfTI, skull stripping, field correction,
  registration/normalization, augmentation, and resize to 56 x 56 x 56.

## 2. Paper pipeline

1. Train a 24-layer 3D CNN and an improved 3D ResNet.
2. Extract 1,000 features from each network.
3. Fuse the two representations using canonical correlation analysis (CCA).
4. Use the Whale Optimization Algorithm (WOA) for feature selection.
5. Compare SVM, KNN, random forest, and gradient boosting classifiers.
6. Report accuracy, precision, recall, and F1.

The paper reports approximately 93.4% accuracy for the 3D CNN, 90% for its
3D ResNet analysis, 94.8% after fusion at 15-fold CV, and 97.2% after WOA at
15-fold CV.

## 3. Reproducibility limitations identified

The following details are missing, inconsistent, or scientifically risky:

- The paper alternates among a 70/15/15 split, 5-fold validation, and 15-fold
  validation without fully specifying how they are nested.
- It says that a separate dataset was used for validation but does not identify
  that dataset.
- It does not state whether CCA and WOA were fit inside each training fold.
  Fitting either before splitting leaks label-related structure into validation.
- Augmentation parameters and whether augmentation was restricted to training
  data are not reported.
- Exact layer channel counts, kernel sizes, padding, dropout, random seeds, and
  stopping rules are incomplete.
- Some tables and prose swap or conflict in model names and metric ordering.
- Accuracy is emphasized despite class imbalance and the small Prodromal group.
- No confidence intervals or repeated-seed variability are reported.

Therefore, an exact numerical reproduction is not guaranteed. The defensible
goal is a transparent implementation of the described idea plus a stricter
validation track.

## 4. Primary scientific question

Can whole-brain preprocessed T2 MRI discriminate Control, Prodromal, and PD in
held-out PPMI subjects, and does CCA fusion add reliable performance beyond a
single 3D network?

Primary endpoint: test macro-F1.

Secondary endpoints:

- Balanced accuracy
- Per-class sensitivity and specificity
- Prodromal one-vs-rest AUROC
- Multiclass log loss
- Calibration error
- Accuracy for comparison with the paper

## 5. Cohort lock and QC

Before modeling, create a locked manifest containing:

- Subject and Image Data ID
- Group, sex, age, visit, and acquisition date
- Absolute or machine-relative NIfTI path
- Shape, voxel spacing, finite-value status, mean, standard deviation, and
  nonzero fraction
- Split assignment and split seed

Exclusion criteria are fixed before training:

- Missing or unreadable NIfTI
- Non-3D volume
- Shape other than 56 x 56 x 56
- NaN or infinite values
- Empty or nearly empty brain volume
- Duplicate subject across rows

The current observed state is 303 NIfTI files and 303 `ok` log rows. Older
documentation mentioning three failures is stale and must not be used as the
cohort source of truth.

## 6. Split policy

### Strict track (primary)

- Fixed subject-level stratified 70/15/15 train/validation/test split.
- The test set is opened once after model and hyperparameter selection.
- All learned transforms, including class weighting, scaling, PCA, CCA, and
  WOA, are fit using training data only.
- Validation selects epoch, architecture, and classifier.
- Repeat the entire development procedure with seeds 2026, 2027, 2028, 2029,
  and 2030; retain the same untouched test definition for the primary result.

### Paper-like track (secondary)

- Stratified 5-, 10-, and 15-fold CV to compare with Table 6.
- Every preprocessing transform after NIfTI generation, feature fusion, and
  feature selection must occur inside each fold.
- Report this as methodological reproduction, not external validation.

## 7. Planned experiments

| ID | Model | Purpose | Selection metric |
|---|---|---|---|
| E0 | Majority and multinomial logistic baselines | Sanity floor | Validation macro-F1 |
| E1 | Compact 3D CNN | Low-variance imaging baseline | Validation macro-F1 |
| E2 | Paper-like 3D CNN | Reproduce Model 1 | Validation macro-F1 |
| E3 | 3D ResNet | Reproduce Model 2 | Validation macro-F1 |
| E4 | CNN features + classical classifiers | Reproduce FC analysis | Validation macro-F1 |
| E5 | ResNet features + classical classifiers | Reproduce FC-4 analysis | Validation macro-F1 |
| E6 | Train-only PCA + CCA fusion | Test fusion benefit | Validation macro-F1 |
| E7 | WOA-selected fused features | Test optimization claim | Validation macro-F1 |
| E8 | Sex/age/scanner sensitivity analysis | Assess confounding | Test subgroup metrics |

E7 is attempted only if E6 beats the best single-network result on validation.
This avoids spending substantial compute optimizing a representation with no
demonstrated incremental value.

## 8. Training policy

- Loss: class-weighted cross entropy.
- Optimizer: AdamW; initial learning rate 1e-3 for CNN, 1e-4 for ResNet.
- Maximum epochs: 100; early stopping patience: 15.
- Batch size: choose the largest of 4, 8, or 16 that fits GPU memory.
- Augmentation, training only: small intensity scale/shift and Gaussian noise.
  Spatial left-right flipping is off by default because asymmetry may be
  biologically meaningful.
- Checkpoint criterion: validation macro-F1.
- Mixed precision on CUDA.

## 9. Statistical reporting

- Give point estimates and subject-level bootstrap 95% confidence intervals.
- Compare paired test predictions with bootstrap differences in macro-F1.
- Report all three class confusion matrices and per-class recall.
- Do not claim superiority from overlapping confidence intervals or a single
  favorable random seed.
- State that PPMI-only testing is internal validation, not generalization to a
  new clinical site.

## 10. Stop/go rules

- Stop if the manifest audit has any unresolved duplicate, missing, non-finite,
  or shape-invalid sample.
- Stop if a shuffled-label run performs materially above chance; investigate
  leakage.
- Do not run WOA until the non-optimized CCA pipeline is stable.
- Do not use the test set to choose CCA components, WOA parameters, classifier,
  threshold, or epoch.
- A final result is publishable only with complete configuration, environment,
  seeds, predictions, and confidence intervals.

