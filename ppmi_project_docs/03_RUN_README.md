# 03_RUN_CONFIG_AND_COMMANDS

재실행 명령, 실행 경로, 실패 샘플 설명을 보관합니다.

## 실행 파일

- `run_t2_303_preprocessing.sh`: WSL에서 전체 303건 전처리를 실행합니다.
- `FAILED_SAMPLES.md`: 현재 실패한 3개 샘플과 원인을 기록합니다.

## 실행 전 확인

1. `01_COHORT_INPUTS_AND_MANIFESTS/RUNTIME_MANIFESTS/data.csv`가 존재하는지 확인합니다.
2. 원본 DICOM 폴더가 `E:\ppmi_dti\raw` 아래에 있는지 확인합니다.
3. WSL에서 FSL과 ANTs 명령이 실행되는지 확인합니다.
4. `04_STAGE_RESULTS/logs/`에 충분한 저장 공간이 있는지 확인합니다.

## 실행

```bash
cd /mnt/e/ppmi_dti/T2_303_PREPROCESSING_PROJECT
bash 03_RUN_CONFIG_AND_COMMANDS/run_t2_303_preprocessing.sh
```
