# PPMI DTI 작업 공간 안내

이 디렉터리는 PPMI 기반 T2 MRI 전처리와 관련 자료를 보관하는 최상위 작업 공간입니다.

## 가장 먼저 볼 폴더

- `T2_303_PREPROCESSING_PROJECT/`: T2 피험자 303명 코호트의 코드, 실행 설정, 단계별 결과, 로그, QC, 보고서를 한곳에 모은 통합 프로젝트입니다.
- `raw/`: 원본 DICOM, 메타데이터, 실행용 manifest가 있는 원천 데이터 영역입니다.
- `논문/`: 논문, 기획서, 참고 문서입니다.

## 최상위 폴더 설명

| 폴더 | 용도 | 주의사항 |
|---|---|---|
| `.venv/` | Windows Python 가상환경 | 자동 생성 환경이므로 수동 편집하지 않습니다. |
| `.venv_wsl/` | WSL/Linux 전처리 가상환경 | FSL, ANTs 연계 실행에 사용합니다. |
| `T2_303_PREPROCESSING_PROJECT/` | 현재 정리된 T2 303명 프로젝트 | 새 작업은 이 폴더를 기준으로 진행합니다. |
| `pipeline/` | 이전 위치의 파이프라인 코드 | 통합본은 프로젝트의 `02_PIPELINE_CODE/`에 있습니다. |
| `preparing/` | 초기 변환·전처리 실험 코드와 중간 산출물 | 재현 가능한 통합 실행본과 구분합니다. |
| `preprocessed/` | 이전 전처리 결과 경로 및 호환 연결 | `t2_paper_303`은 통합 결과 폴더로 연결됩니다. |
| `raw/` | 원본 데이터와 원천 메타데이터 | 원본 DICOM은 수정하지 않습니다. |
| `temp_nifti/` | 임시 NIfTI 변환 파일 | 최종 분석 입력으로 사용하지 않습니다. |
| `논문/` | 논문 및 프로젝트 참고 문서 | 분석 코드와 분리 보관합니다. |
| `버림/` | 보류·폐기 후보 파일 | 삭제 전 재검토용이며 분석 입력으로 사용하지 않습니다. |

## 대표 실행 결과

- 대상: 303 samples / 303 unique subjects
- 성공: 300
- 실패: 3
- 최종 모델 입력: `T2_303_PREPROCESSING_PROJECT/04_STAGE_RESULTS/06_resized/`
- 전체 실행 로그: `T2_303_PREPROCESSING_PROJECT/04_STAGE_RESULTS/logs/full_run_console.log`

자세한 내용은 `T2_303_PREPROCESSING_PROJECT/README.md`를 확인하십시오.
