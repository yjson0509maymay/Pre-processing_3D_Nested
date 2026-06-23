#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT=/mnt/e/ppmi_dti/T2_303_PREPROCESSING_PROJECT
VENV_ROOT=/mnt/e/ppmi_dti/.venv_wsl
OUTPUT_ROOT="$PROJECT_ROOT/04_STAGE_RESULTS"
LOG_DIR="$OUTPUT_ROOT/logs"

source "$VENV_ROOT/bin/activate"
mkdir -p "$LOG_DIR"

{
  echo "Started: $(date --iso-8601=seconds)"
  python "$PROJECT_ROOT/02_PIPELINE_CODE/run_staged_preprocessing.py" \
    --data-csv "$PROJECT_ROOT/01_COHORT_INPUTS_AND_MANIFESTS/RUNTIME_MANIFESTS/data.csv" \
    --output-root "$OUTPUT_ROOT" \
    --mni-template /usr/local/fsl/data/standard/MNI152_T1_1mm_brain.nii.gz \
    --preparing-path "$PROJECT_ROOT/02_PIPELINE_CODE/preparing.py" \
    --workers 4
  echo "Finished: $(date --iso-8601=seconds)"
} 2>&1 | tee "$LOG_DIR/full_run_console.log"
