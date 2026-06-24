# PD25 ROBEX Parkinson-Specialized Preprocessing

This optional comparison pipeline creates a separate 303-subject preprocessing branch:

```text
DICOM
-> ROBEX brain extraction
-> ANTs N4 bias-field correction
-> antspyx SyN non-linear registration to a PD25 Parkinson template
-> min-max normalization
-> 56x56x56 resize for model-input comparison
```

It is separate from the current MNI152/BET/z-score pipeline so both outputs can be compared.

## Output

Default output root:

```text
E:\ppmi_dti\preprocessed\t2_pd25_robex_303
```

Stages:

```text
01_raw_nifti
02_robex
03_n4
04_pd25_syn
05_minmax
06_resized
logs
```

`05_minmax` preserves the PD25-space normalized volume before model resizing.  
`06_resized` is the `56 x 56 x 56` model-comparison input.

## Required External Files

This runner does not bundle the PD25 template or ROBEX binaries.

Set these environment variables in WSL before running:

```bash
export PD25_TEMPLATE=/mnt/e/ppmi_dti/templates/PD25-T1MPRAGE-1mm-brain.nii.gz
export ROBEX_COMMAND=/mnt/e/ppmi_dti/tools/ROBEX/runROBEX.sh
```

Then run:

```bash
cd /mnt/e/ppmi_dti
bash pipeline/run_pd25_robex_preprocessing.sh
```

The command is resumable by default. Existing stage outputs are skipped unless `--overwrite` is added to the Python command.

## Logs

The runner prints per-sample total time and stage time in seconds, and writes:

```text
E:\ppmi_dti\preprocessed\t2_pd25_robex_303\logs\preprocessing_log.csv
E:\ppmi_dti\preprocessed\t2_pd25_robex_303\logs\full_run_console.log
```
