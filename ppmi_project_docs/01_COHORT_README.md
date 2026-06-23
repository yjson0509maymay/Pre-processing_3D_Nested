# 01_COHORT_INPUTS_AND_MANIFESTS

코호트 선정 결과와 전처리 실행에 직접 사용한 manifest를 보관합니다.

## 하위 폴더

- `FINAL_SELECTED_COHORT_303/`: 303명 최종 선정표, 다운로드 목록, 요약 이미지
- `RUNTIME_MANIFESTS/`: 파이프라인이 읽는 `data.csv`, 전체 로컬 인벤토리 `metadata.csv`

## 핵심 파일

- `RUNTIME_MANIFESTS/data.csv`: 전처리 대상 303행. `sample_id`, Subject, Image Data ID, Group, label, DICOM 경로를 포함합니다.
- `RUNTIME_MANIFESTS/metadata.csv`: 로컬 DICOM 폴더와 원천 메타데이터를 결합한 전체 인벤토리입니다.
- `FINAL_SELECTED_COHORT_303/T2_download_cohort_303_unique_subjects.xlsx`: 사람이 확인하기 좋은 통합 선정표입니다.

`data.csv`의 경로가 실제 DICOM 위치와 일치하는지 확인한 뒤 전처리를 실행하십시오.
