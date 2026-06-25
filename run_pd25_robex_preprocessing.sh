#!/usr/bin/env bash
set -euo pipefail

cd /mnt/e/ppmi_dti
source .venv_wsl/bin/activate

OUTPUT_ROOT=/mnt/e/ppmi_dti/preprocessed/t2_pd25_robex_affine_syn_303
LOG_DIR="$OUTPUT_ROOT/logs"
ANTS_TMP=/mnt/e/ppmi_dti/tmp/pd25_ants_tmp
mkdir -p "$LOG_DIR" "$ANTS_TMP"

export TMPDIR="$ANTS_TMP"
export TEMP="$ANTS_TMP"
export TMP="$ANTS_TMP"
export ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS=1

PD25_TEMPLATE="${PD25_TEMPLATE:-/mnt/e/ppmi_dti/templates/pd25_20170213/PD25-T1MPRAGE-template-1mm.nii.gz}"
RUN_STAMP="$(date +%Y%m%d_%H%M%S)"
RUN_LOG="$LOG_DIR/full_run_console_${RUN_STAMP}.log"
RUN_CSV="preprocessing_log_${RUN_STAMP}.csv"

{
  echo "Started: $(date --iso-8601=seconds)"
  python pipeline/run_pd25_robex_preprocessing.py \
    --data-csv /mnt/e/ppmi_dti/raw/data.csv \
    --output-root "$OUTPUT_ROOT" \
    --pd25-template "$PD25_TEMPLATE" \
    --robex-mode pyrobex \
    --preparing-path /mnt/e/ppmi_dti/preparing/preparing.py \
    --log-name "$RUN_CSV" \
    --workers 2
  echo "Finished: $(date --iso-8601=seconds)"
} 2>&1 | tee "$RUN_LOG"
cp "$RUN_LOG" "$LOG_DIR/full_run_console_latest.log"
