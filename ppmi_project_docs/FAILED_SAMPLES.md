# 실패 샘플 3건

전체 303건 중 300건은 성공했고 아래 3건은 실패했습니다.

| Sample ID | Group | 실패 단계 | 원인 |
|---|---|---|---|
| `sub-3468_I287579` | Control | DICOM → NIfTI | 3D NIfTI volume이 생성되지 않음 |
| `sub-3419_I237948` | PD | N4 | NIfTI direction cosine이 orthonormal이 아니어서 ITK가 읽지 못함 |
| `sub-4073_I374132` | PD | DICOM → NIfTI | 3D NIfTI volume이 생성되지 않음 |

## 권장 조치

- DICOM 변환 실패 2건: 파일 수, series 분리, 압축 손상, 다중 Echo/4D 여부를 점검합니다.
- N4 실패 1건: BET 출력의 affine/header를 직교화한 사본으로 N4부터 재실행합니다.
- 수정 전 원본과 현재 실패 로그는 보존합니다.
- 재실행 결과는 기존 `preprocessing_log.csv`와 구분되는 별도 로그로 기록합니다.
