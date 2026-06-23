#!/usr/bin/env bash
set -euo pipefail

cd /mnt/e/ppmi_dti
source .venv_wsl/bin/activate

LOG_DIR=/mnt/e/ppmi_dti/preprocessed/t2_paper_303/logs
mkdir -p "$LOG_DIR"

{
  echo "Started: $(date --iso-8601=seconds)"
  python pipeline/run_staged_preprocessing.py \
    --data-csv /mnt/e/ppmi_dti/raw/data.csv \
    --output-root /mnt/e/ppmi_dti/preprocessed/t2_paper_303 \
    --mni-template /usr/local/fsl/data/standard/MNI152_T1_1mm_brain.nii.gz \
    --preparing-path /mnt/e/ppmi_dti/preparing/preparing.py \
    --workers 4
  echo "Finished: $(date --iso-8601=seconds)"
} 2>&1 | tee "$LOG_DIR/full_run_console.log"
