# Non-linear Registration Update

The preprocessing pipeline now adds an antspyx SyN non-linear registration step after the existing FSL FLIRT affine registration.

Updated flow:

```text
DICOM
-> 01_raw_nifti
-> 02_bet
-> 03_n4
-> 04_mni152_affine
-> 05_ants_nonlinear
-> 06_normalized
-> 07_resized
```

Why this was added:

- The main Scientific Reports paper says preprocessing follows references 21 and 22.
- Reference 21 describes affine and non-linear registration with Antspyx.
- The previous implementation used FSL FLIRT affine registration only.
- The new implementation keeps FLIRT as a robust affine initialization and then applies antspyx SyN registration in template space.

Important path change:

- Previous final model input: `06_resized/`
- New final model input after non-linear registration: `07_resized/`

Install note:

```bash
pip install antspyx
```

FSL and ANTs command-line tools are still required separately for BET, FLIRT, and N4BiasFieldCorrection.
