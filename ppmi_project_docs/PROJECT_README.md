# T2 303명 MRI 전처리 통합 프로젝트

PPMI T2 MRI 303개 샘플의 코호트 선정, 실행 코드, 설정, 단계별 NIfTI 결과, 로그, QC 이미지 및 보고서를 한 폴더에 정리한 프로젝트입니다.

## 실행 요약

| 항목 | 값 |
|---|---:|
| 전체 샘플 | 303 |
| 성공 | 300 |
| 실패 | 3 |
| 클래스 | Control 110 / Prodromal 58 / PD 135 |
| 최종 shape | 56 × 56 × 56 |

## 폴더 순서

1. `01_COHORT_INPUTS_AND_MANIFESTS/`: 선정 코호트와 실제 실행 입력 CSV
2. `02_PIPELINE_CODE/`: 전처리 및 시각화 코드
3. `03_RUN_CONFIG_AND_COMMANDS/`: 실행 명령과 실패 샘플 기록
4. `04_STAGE_RESULTS/`: 01~06 단계별 NIfTI, 로그, 시각화
5. `05_REPORTS_ARCHITECTURE_AND_QC/`: 아키텍처 PNG/PPTX/SVG와 생성 코드
6. `90_AUXILIARY_DOWNLOAD_AND_SELECTION_HISTORY/`: 다운로드·선정 과정의 보조 산출물

## 전처리 흐름

`DICOM → 01_raw_nifti → 02_bet → 03_n4 → 04_mni152 → 05_normalized → 06_resized`

- DICOM 변환 시 여러 Echo가 있으면 가장 큰 Echo Time을 선택합니다.
- BET로 뇌 외 조직을 제거합니다.
- ANTs N4로 intensity bias를 보정합니다.
- FSL FLIRT 12-DOF로 MNI152 공간에 정합합니다.
- 비영점 voxel을 z-score 정규화하고 `[-5, 5]`로 clipping합니다.
- 최종적으로 `56 × 56 × 56` 크기로 변환합니다.

## 재실행

WSL에서 `03_RUN_CONFIG_AND_COMMANDS/run_t2_303_preprocessing.sh`를 실행합니다. 기존 결과가 있으면 단계별로 건너뛰며, 강제 재처리가 필요할 때만 Python 명령에 `--overwrite`를 추가합니다.

## 기존 경로 호환

기존 경로 `E:\ppmi_dti\preprocessed\t2_paper_303`은 이 프로젝트의 `04_STAGE_RESULTS`를 가리키는 디렉터리 연결로 유지됩니다. 기존 분석 코드에서 경로를 즉시 변경하지 않아도 됩니다.

## 실패 샘플

3건의 실패 사유는 `03_RUN_CONFIG_AND_COMMANDS/FAILED_SAMPLES.md`에 정리되어 있습니다. 실패 샘플을 해결하기 전 모델 학습에는 성공한 300건만 사용하십시오.
