# 04_STAGE_RESULTS

T2 303명 전처리의 단계별 NIfTI 결과와 실행 부산물을 보관합니다. 각 단계 폴더의 출력이 다음 단계의 입력입니다.

| 순서 | 폴더 | 내용 | 현재 파일 수 |
|---:|---|---|---:|
| 1 | `01_raw_nifti/` | DICOM을 변환·재지향한 3D NIfTI | 302 |
| 2 | `02_bet/` | FSL BET 뇌 추출 결과 | 302 |
| 3 | `03_n4/` | ANTs N4 bias 보정 결과 | 301 |
| 4 | `04_mni152/` | MNI152 정합 NIfTI 및 변환 행렬 | 601 |
| 5 | `05_normalized/` | z-score 정규화 결과 | 301 |
| 6 | `06_resized/` | 최종 56×56×56 모델 입력 | 301 |
| - | `logs/` | 실행 로그, 샘플별 상태·시간 CSV | 3 |
| - | `visualization/` | 단계별 QC 이미지와 발표용 그림 | 샘플 폴더 1개 |

파일 수 차이는 실패 샘플과 MNI 변환 행렬 파일 때문입니다. 모델 학습 전에 `logs/preprocessing_log.csv`에서 `status=ok`인 샘플만 선택하십시오.
