# 02_PIPELINE_CODE

T2 303명 전처리와 관련된 실행 코드의 통합 사본입니다.

## 파일

- `run_staged_preprocessing.py`: DICOM부터 56³ 모델 입력까지 단계별 전처리를 수행합니다.
- `build_manifests.py`: 원본 DICOM 인벤토리와 코호트 CSV를 결합해 manifest를 생성합니다.
- `generate_preprocessing_visuals.py`: 한 피험자의 단계별 3-plane 및 before/after QC 이미지를 만듭니다.
- `preparing.py`: BET, N4, FLIRT, 정규화, resize 함수의 구현입니다.
- `build_t2_workbook.mjs`: 코호트 CSV를 XLSX 요약 파일로 변환합니다.

## 외부 도구

- Python: numpy, nibabel, pydicom, dicom2nifti, matplotlib
- FSL: BET, FLIRT, MNI152 template
- ANTs: N4BiasFieldCorrection
- 실행 환경: WSL/Linux 가상환경 `E:\ppmi_dti\.venv_wsl`

코드를 수정할 때는 이 폴더를 기준본으로 사용하고, 변경 이력을 별도로 기록하십시오.
