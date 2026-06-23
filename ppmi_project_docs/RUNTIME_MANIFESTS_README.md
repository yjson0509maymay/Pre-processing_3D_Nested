# RUNTIME_MANIFESTS

전처리 코드가 실제로 읽는 CSV 입력 파일입니다.

- `data.csv`: 최종 코호트 303건의 sample ID, label, 원본 DICOM 경로
- `metadata.csv`: 로컬 DICOM 전체 인벤토리와 원천 메타데이터 결합표

코호트 선정 보고서와 달리 이 폴더의 `data.csv`는 실행 경로를 포함하므로, DICOM 위치를 변경하면 manifest도 다시 생성해야 합니다.
