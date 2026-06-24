import argparse
import csv
import importlib.util
import os
import re
import shutil
import subprocess
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import dicom2nifti
import dicom2nifti.settings as dcm_settings
import nibabel as nib
import numpy as np
import pydicom
from scipy.ndimage import zoom


dcm_settings.disable_validate_slice_increment()

TARGET_SHAPE = (56, 56, 56)

STAGES = [
    ("01_raw_nifti", "DICOM converted to a reoriented 3D NIfTI volume."),
    ("02_robex", "ROBEX brain extraction output."),
    ("03_n4", "ANTs N4 bias-field corrected brain volume."),
    ("04_pd25_syn", "antspyx SyN non-linear registration to a PD25 Parkinson template."),
    ("05_minmax", "Non-zero brain voxels min-max normalized to [0, 1]."),
    ("06_resized", "Final model-comparison input resized to 56 x 56 x 56 voxels."),
]


def read_rows(path):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_rows(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_preparing(path):
    spec = importlib.util.spec_from_file_location("paper_preparing", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def platform_path(path):
    match = re.match(r"^([A-Za-z]):[\\/](.*)$", path)
    if os.name != "nt" and match:
        drive = match.group(1).lower()
        tail = match.group(2).replace("\\", "/")
        return f"/mnt/{drive}/{tail}"
    return path


def require_file(path, label):
    if not path or not os.path.exists(path):
        raise RuntimeError(f"{label} not found: {path}")


def require_command(command):
    if os.path.exists(command):
        return command
    found = shutil.which(command)
    if found:
        return found
    raise RuntimeError(f"Required command not found: {command}")


def run_command(command, step_name):
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"{step_name} failed: {message}")
    return result


def read_echo_time(path):
    try:
        ds = pydicom.dcmread(
            path,
            stop_before_pixels=True,
            specific_tags=["EchoTime"],
            force=True,
        )
        value = getattr(ds, "EchoTime", None)
        return float(value) if value not in (None, "") else None
    except Exception:
        return None


def select_t2_echo_files(dicom_dir):
    files = [
        str(Path(dicom_dir) / name)
        for name in os.listdir(dicom_dir)
        if name.lower().endswith(".dcm")
    ]
    echo_groups = {}
    for path in files:
        echo_time = read_echo_time(path)
        if echo_time is None:
            continue
        echo_groups.setdefault(round(echo_time, 4), []).append(path)
    if len(echo_groups) <= 1:
        return files, next(iter(echo_groups), None), False
    selected_te = max(echo_groups)
    return echo_groups[selected_te], selected_te, True


def convert_t2_dicom(dicom_dir, output_path):
    selected_files, echo_time, echo_filtered = select_t2_echo_files(dicom_dir)
    input_dir = dicom_dir
    filtered_dir = None
    converted_dir = tempfile.mkdtemp(prefix="pd25_t2_nifti_")
    try:
        if echo_filtered:
            filtered_dir = tempfile.mkdtemp(prefix="pd25_t2_echo_")
            for index, source in enumerate(selected_files):
                shutil.copy2(source, os.path.join(filtered_dir, f"slice_{index:06d}.dcm"))
            input_dir = filtered_dir

        dicom2nifti.convert_directory(input_dir, converted_dir, compression=True, reorient=True)
        candidates = []
        for name in os.listdir(converted_dir):
            if not (name.endswith(".nii") or name.endswith(".nii.gz")):
                continue
            path = os.path.join(converted_dir, name)
            image = nib.load(path)
            data = image.get_fdata(dtype=np.float32)
            if data.ndim == 4:
                data = data[..., -1]
                image = nib.Nifti1Image(data.astype(np.float32), image.affine, image.header)
                collapsed = os.path.join(converted_dir, "collapsed_" + name)
                nib.save(image, collapsed)
                path = collapsed
            if data.ndim == 3:
                candidates.append((int(np.prod(data.shape)), path, data.shape))
        if not candidates:
            raise RuntimeError("DICOM conversion produced no 3D NIfTI volume")
        _, selected_path, shape = max(candidates, key=lambda item: item[0])
        shutil.copy2(selected_path, output_path)
        return echo_time, echo_filtered, "x".join(map(str, shape))
    finally:
        shutil.rmtree(converted_dir, ignore_errors=True)
        if filtered_dir:
            shutil.rmtree(filtered_dir, ignore_errors=True)


def load_nifti(path):
    img = nib.load(path)
    data = img.get_fdata(dtype=np.float32)
    if data.ndim != 3:
        raise RuntimeError(f"Expected 3D NIfTI, got shape {data.shape}: {path}")
    return img, data


def run_pyrobex(input_path, output_path, seed=0):
    try:
        from pyrobex.robex import robex
    except ImportError as exc:
        raise RuntimeError(
            "pyrobex is required for ROBEX brain extraction. "
            "Install it with: pip install pyrobex"
        ) from exc

    image = nib.load(input_path)
    stripped, mask = robex(image, seed=seed)
    mask_path = output_path.replace(".nii.gz", "_mask.nii.gz").replace(".nii", "_mask.nii")
    nib.save(stripped, output_path)
    nib.save(mask, mask_path)
    return output_path


def run_robex_command(input_path, output_path, robex_command):
    command = require_command(robex_command)
    mask_path = output_path.replace(".nii.gz", "_mask.nii.gz").replace(".nii", "_mask.nii")
    if command.endswith(".sh"):
        robex_call = ["bash", command, input_path, output_path, mask_path]
    else:
        robex_call = [command, input_path, output_path, mask_path]
    run_command(robex_call, "ROBEX brain extraction")
    return output_path


def run_robex(input_path, output_path, robex_mode, robex_command, seed=0):
    if robex_mode == "pyrobex":
        return run_pyrobex(input_path, output_path, seed=seed)
    if robex_mode == "command":
        return run_robex_command(input_path, output_path, robex_command)
    raise RuntimeError(f"Unsupported ROBEX mode: {robex_mode}")


def run_pd25_antspyx_syn(input_path, output_path, pd25_template, transform_type="SyN"):
    require_file(pd25_template, "PD25 template")
    try:
        import ants
    except ImportError as exc:
        raise RuntimeError(
            "antspyx is required for PD25 non-linear registration. "
            "Install it with: pip install antspyx"
        ) from exc

    fixed = ants.image_read(pd25_template)
    moving = ants.image_read(input_path)
    registration = ants.registration(
        fixed=fixed,
        moving=moving,
        type_of_transform=transform_type,
    )
    ants.image_write(registration["warpedmovout"], output_path)
    return output_path


def normalize_minmax(input_path, output_path):
    img, data = load_nifti(input_path)
    finite = np.isfinite(data)
    brain_mask = finite & (data != 0)
    if not np.any(brain_mask):
        raise RuntimeError("Cannot min-max normalize: no non-zero brain voxels found.")
    values = data[brain_mask]
    min_value = float(values.min())
    max_value = float(values.max())
    if max_value - min_value < 1e-6:
        raise RuntimeError("Cannot min-max normalize: intensity range is too small.")
    normalized = np.zeros_like(data, dtype=np.float32)
    normalized[brain_mask] = (data[brain_mask] - min_value) / (max_value - min_value)
    nib.save(nib.Nifti1Image(normalized, img.affine, img.header), output_path)
    return output_path


def resize_nifti(input_path, output_path, target_shape=TARGET_SHAPE, order=1):
    img, data = load_nifti(input_path)
    factors = np.array(target_shape, dtype=float) / np.array(data.shape, dtype=float)
    resized_data = zoom(data, factors, order=order)
    new_affine = img.affine.copy()
    new_affine[:3, :3] = img.affine[:3, :3] / factors
    nib.save(
        nib.Nifti1Image(resized_data.astype(np.float32), new_affine, img.header),
        output_path,
    )
    return output_path


def stage_path(root, stage, sample_id):
    return str(Path(root) / stage / f"{sample_id}.nii.gz")


def ensure_readmes(output_root):
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    root_text = (
        "# PD25 ROBEX Parkinson-specialized preprocessing\n\n"
        "Pipeline: DICOM -> ROBEX -> ANTs N4 -> antspyx SyN registration to a "
        "PD25 Parkinson template -> min-max normalization -> 56x56x56 resize.\n\n"
        "This branch is intended for comparison with the MNI152/BET/z-score pipeline.\n"
    )
    (root / "README.md").write_text(root_text, encoding="utf-8")
    for index, (name, description) in enumerate(STAGES):
        folder = root / name
        folder.mkdir(parents=True, exist_ok=True)
        previous_name = "raw DICOM from data.csv" if index == 0 else STAGES[index - 1][0]
        next_name = "model comparison input" if index == len(STAGES) - 1 else STAGES[index + 1][0]
        text = (
            f"# {name}\n\nPurpose: {description}\n\n"
            f"Input: `{previous_name}`\n\nOutput: one `.nii.gz` per sample.\n\n"
            f"Next: `{next_name}`\n"
        )
        (folder / "README.md").write_text(text, encoding="utf-8")
    logs = root / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / "README.md").write_text("# logs\n\nPurpose: Batch and per-sample logs.\n", encoding="utf-8")


def format_stage_timings(result):
    parts = []
    for key in [
        "01_seconds",
        "02_seconds",
        "03_seconds",
        "04_seconds",
        "05_seconds",
        "06_seconds",
    ]:
        if key in result and result[key] != "":
            parts.append(f"{key[:2]}={result[key]} sec")
    return ", ".join(parts) if parts else "all stages skipped"


def stable_numeric_seed(value):
    digits = re.sub(r"\D", "", str(value))
    return int(digits) if digits else 0


def process_sample(row, config):
    start_total = time.perf_counter()
    sample_id = row["sample_id"]
    preparing = load_preparing(config["preparing_path"])
    timings = {}
    result = {
        "sample_id": sample_id,
        "Subject": row["Subject"],
        "Image Data ID": row["Image Data ID"],
        "Group": row["Group"],
        "time_unit": "seconds",
        "status": "ok",
        "message": "",
        "selected_echo_time": "",
        "echo_filtered": "no",
        "original_shape": "",
        "final_shape": "56x56x56",
    }
    paths = {stage: stage_path(config["output_root"], stage, sample_id) for stage, _ in STAGES}
    try:
        if config["overwrite"] or not os.path.exists(paths["01_raw_nifti"]):
            started = time.perf_counter()
            echo_time, echo_filtered, shape = convert_t2_dicom(
                platform_path(row["raw_dicom_dir"]), paths["01_raw_nifti"]
            )
            timings["01_seconds"] = time.perf_counter() - started
            result["selected_echo_time"] = "" if echo_time is None else echo_time
            result["echo_filtered"] = "yes" if echo_filtered else "no"
            result["original_shape"] = shape
        else:
            image = nib.load(paths["01_raw_nifti"])
            result["original_shape"] = "x".join(map(str, image.shape))

        operations = [
            ("02_robex", run_robex, (paths["01_raw_nifti"], paths["02_robex"], config["robex_mode"], config["robex_command"], stable_numeric_seed(row["Image Data ID"]))),
            ("03_n4", preparing.run_n4_field_correction, (paths["02_robex"], paths["03_n4"])),
            ("04_pd25_syn", run_pd25_antspyx_syn, (paths["03_n4"], paths["04_pd25_syn"], config["pd25_template"], config["transform_type"])),
            ("05_minmax", normalize_minmax, (paths["04_pd25_syn"], paths["05_minmax"])),
            ("06_resized", resize_nifti, (paths["05_minmax"], paths["06_resized"])),
        ]
        for stage, function, arguments in operations:
            if config["overwrite"] or not os.path.exists(paths[stage]):
                started = time.perf_counter()
                function(*arguments)
                timings[stage[:2] + "_seconds"] = time.perf_counter() - started
    except Exception as exc:
        result["status"] = "failed"
        result["message"] = str(exc)
    result.update({key: round(value, 3) for key, value in timings.items()})
    result["total_seconds"] = round(time.perf_counter() - start_total, 3)
    return result


def parse_args():
    parser = argparse.ArgumentParser(description="PD25 ROBEX Parkinson-specialized T2 preprocessing.")
    parser.add_argument("--data-csv", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--pd25-template", required=True)
    parser.add_argument("--robex-mode", choices=["pyrobex", "command"], default="pyrobex")
    parser.add_argument("--robex-command", default=os.environ.get("ROBEX_COMMAND", "runROBEX.sh"))
    parser.add_argument("--preparing-path", required=True)
    parser.add_argument("--transform-type", default="SyN")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    rows = read_rows(args.data_csv)
    if args.limit > 0:
        rows = rows[: args.limit]
    ensure_readmes(args.output_root)
    require_file(args.pd25_template, "PD25 template")
    if args.robex_mode == "command":
        require_command(args.robex_command)

    config = {
        "output_root": args.output_root,
        "pd25_template": args.pd25_template,
        "robex_mode": args.robex_mode,
        "robex_command": args.robex_command,
        "preparing_path": args.preparing_path,
        "transform_type": args.transform_type,
        "overwrite": args.overwrite,
    }
    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(process_sample, row, config): row for row in rows}
        for index, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            results.append(result)
            print(
                f"[{index}/{len(rows)}] {result['sample_id']} - {result['status']} "
                f"total={result['total_seconds']} sec | {format_stage_timings(result)}",
                flush=True,
            )
            fields = sorted({key for item in results for key in item})
            write_rows(Path(args.output_root) / "logs" / "preprocessing_log.csv", results, fields)

    ok = sum(item["status"] == "ok" for item in results)
    failed = len(results) - ok
    print(f"Complete: success={ok}, failed={failed}, total={len(results)}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
