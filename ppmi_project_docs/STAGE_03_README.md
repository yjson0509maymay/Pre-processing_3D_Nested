# 03_n4

- 입력: `02_bet/`
- 처리: ANTs N4 bias-field correction
- 출력: 공간적 intensity 불균일이 완화된 NIfTI
- 다음 단계: `04_mni152/`

ITK가 affine/header를 읽지 못하면 direction cosine의 직교성을 점검하십시오.
