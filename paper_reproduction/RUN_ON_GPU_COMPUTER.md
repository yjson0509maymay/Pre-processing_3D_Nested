# GPU 컴퓨터 실행 체크리스트

## 시작 전

1. `paper_reproduction` 폴더와 코호트 CSV를 GPU 컴퓨터로 복사한다.
2. 전처리 영상 폴더에 `*.nii.gz` 파일이 303개인지 확인한다.
3. NVIDIA 드라이버, CUDA 호환 PyTorch, Python 가상환경을 준비한다.
4. `pip install -r requirements.txt`를 실행한다.

## 실행 순서

1. `build_manifest`: 303개 파일, 중복 피험자, shape, NaN/Inf를 검사한다.
2. `train --model paper_cnn`: 논문형 3D-CNN 기준선을 학습한다.
3. `train --model resnet3d`: 3D-ResNet을 같은 split으로 학습한다.
4. `extract_features`: 각 모델에서 1,000차원 특징을 추출한다.
5. `fuse_features`: train에서만 PCA와 CCA를 학습하고 분류기를 비교한다.
6. `woa_feature_selection`: CCA가 단일 모델보다 나을 때만 실행한다.

## 첫 실행은 smoke test로

```bash
python -m src.train --manifest runs/manifest/dataset_manifest.csv \
  --model paper_cnn --output-dir runs/smoke_cnn \
  --epochs 2 --patience 2 --batch-size 4 --num-workers 0
```

이 실행에서 데이터 로딩, GPU 메모리, loss 감소, 결과 파일 생성을 먼저
확인한다. 정상일 때 100 epoch 설정으로 본 실험을 시작한다.

## 완료 판정

- `dataset_audit.json`의 모든 오류 목록이 비어 있다.
- `config.json`, `history.csv`, `best.pt`, `metrics.json`,
  `predictions.csv`가 생성된다.
- test 결과는 validation 기반 선택이 끝난 후 한 번만 산출한다.
- 최소 5개 seed의 결과와 bootstrap 95% 신뢰구간을 보고한다.

