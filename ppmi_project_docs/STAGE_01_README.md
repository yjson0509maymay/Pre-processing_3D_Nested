# 01_raw_nifti

- 입력: `data.csv`가 가리키는 원본 DICOM 폴더
- 처리: Echo 선택, DICOM → NIfTI, reorient, 4D일 경우 마지막 volume 선택
- 출력: 샘플당 `sample_id.nii.gz` 1개
- 다음 단계: `02_bet/`

원본 DICOM 자체가 아니며, 파이프라인에서 처음 생성되는 3D 볼륨입니다.
