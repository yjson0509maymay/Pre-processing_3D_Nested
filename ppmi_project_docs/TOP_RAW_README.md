# raw

원본 DICOM과 원천 메타데이터 영역입니다.

- `data/`: 실제 DICOM 데이터 트리
- `Metadata/`: 다운로드 메타데이터
- `zip/`: 다운로드 압축 파일
- `data.csv`: 현재 전처리 실행용 303건 manifest
- `metadata.csv`: 로컬 DICOM 전체 인벤토리

원본 DICOM은 수정하지 말고, 변환 결과는 `T2_303_PREPROCESSING_PROJECT/04_STAGE_RESULTS/`에 저장하십시오.
