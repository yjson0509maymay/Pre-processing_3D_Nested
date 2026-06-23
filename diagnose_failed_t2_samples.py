import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import nibabel as nib
import numpy as np
import pydicom


def value(ds, name, default=None):
    item = getattr(ds, name, default)
    if item is None:
        return default
    try:
        return list(item) if not isinstance(item, (str, bytes)) and hasattr(item, "__iter__") else item
    except Exception:
        return str(item)


def inspect_dicom(folder):
    records = []
    errors = []
    for path in sorted(Path(folder).glob("*.dcm")):
        try:
            ds = pydicom.dcmread(path, stop_before_pixels=True, force=True)
            records.append({
                "file": path.name,
                "series_uid": str(value(ds, "SeriesInstanceUID", "")),
                "sop_class": str(value(ds, "SOPClassUID", "")),
                "instance": value(ds, "InstanceNumber"),
                "echo_time": value(ds, "EchoTime"),
                "rows": value(ds, "Rows"),
                "cols": value(ds, "Columns"),
                "frames": value(ds, "NumberOfFrames", 1),
                "orientation": value(ds, "ImageOrientationPatient"),
                "position": value(ds, "ImagePositionPatient"),
                "slice_location": value(ds, "SliceLocation"),
                "image_type": value(ds, "ImageType"),
                "pixel_spacing": value(ds, "PixelSpacing"),
                "slice_thickness": value(ds, "SliceThickness"),
                "spacing_between_slices": value(ds, "SpacingBetweenSlices"),
            })
        except Exception as exc:
            errors.append({"file": path.name, "error": str(exc)})

    groups = defaultdict(list)
    for row in records:
        groups[(row["series_uid"], str(row["echo_time"]), row["rows"], row["cols"])].append(row)

    summaries = []
    for key, rows in groups.items():
        positions = [r["position"] for r in rows if r["position"]]
        orientations = Counter(str(r["orientation"]) for r in rows)
        slice_locations = [float(r["slice_location"]) for r in rows if r["slice_location"] is not None]
        summaries.append({
            "series_uid": key[0],
            "echo_time": key[1],
            "matrix": [key[2], key[3]],
            "file_count": len(rows),
            "unique_positions": len({str(p) for p in positions}),
            "unique_orientations": len(orientations),
            "orientation_counts": dict(orientations),
            "slice_location_minmax": [min(slice_locations), max(slice_locations)] if slice_locations else None,
            "instances_minmax": [
                min(float(r["instance"]) for r in rows if r["instance"] is not None),
                max(float(r["instance"]) for r in rows if r["instance"] is not None),
            ] if any(r["instance"] is not None for r in rows) else None,
            "frames": sorted({str(r["frames"]) for r in rows}),
            "image_types": sorted({str(r["image_type"]) for r in rows}),
            "pixel_spacings": sorted({str(r["pixel_spacing"]) for r in rows}),
            "slice_thicknesses": sorted({str(r["slice_thickness"]) for r in rows}),
            "spacing_between_slices": sorted({str(r["spacing_between_slices"]) for r in rows}),
        })

    return {
        "folder": str(folder),
        "files": len(records),
        "read_errors": errors,
        "group_count": len(groups),
        "groups": summaries,
    }


def inspect_nifti(path):
    image = nib.load(path)
    affine = np.asarray(image.affine, dtype=float)
    basis = affine[:3, :3]
    norms = np.linalg.norm(basis, axis=0)
    unit = basis / norms
    gram = unit.T @ unit
    return {
        "path": str(path),
        "shape": list(image.shape),
        "zooms": list(image.header.get_zooms()),
        "affine": affine.round(8).tolist(),
        "axis_codes": list(nib.aff2axcodes(affine)),
        "qform_code": int(image.header["qform_code"]),
        "sform_code": int(image.header["sform_code"]),
        "basis_norms": norms.round(8).tolist(),
        "normalized_gram": gram.round(8).tolist(),
        "max_off_diagonal": float(np.max(np.abs(gram - np.eye(3)))),
        "determinant": float(np.linalg.det(basis)),
    }


def main():
    folders = sys.argv[1:3]
    nifti_paths = sys.argv[3:]
    report = {
        "dicom": [inspect_dicom(folder) for folder in folders],
        "nifti": [inspect_nifti(path) for path in nifti_paths],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
