#!/usr/bin/env bash
set -euo pipefail

cd /mnt/e/ppmi_dti
source .venv_wsl/bin/activate

OUTPUT_ROOT=/mnt/e/ppmi_dti/preprocessed/t2_pd25_robex_303
LOG_DIR="$OUTPUT_ROOT/logs"
ANTS_TMP=/mnt/e/ppmi_dti/tmp/pd25_ants_tmp
mkdir -p "$LOG_DIR" "$ANTS_TMP"

export TMPDIR="$ANTS_TMP"
export TEMP="$ANTS_TMP"
export TMP="$ANTS_TMP"
export ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS=1

PD25_TEMPLATE="${PD25_TEMPLATE:-/mnt/e/ppmi_dti/templates/pd25_20170213/PD25-T1MPRAGE-template-1mm.nii.gz}"

{
  echo "Started: $(date --iso-8601=seconds)"
  python pipeline/run_pd25_robex_preprocessing.py \
    --data-csv /mnt/e/ppmi_dti/raw/data.csv \
    --output-root "$OUTPUT_ROOT" \
    --pd25-template "$PD25_TEMPLATE" \
    --robex-mode pyrobex \
    --preparing-path /mnt/e/ppmi_dti/preparing/preparing.py \
    --workers 2
  echo "Finished: $(date --iso-8601=seconds)"
} 2>&1 | tee "$LOG_DIR/full_run_console.log"
