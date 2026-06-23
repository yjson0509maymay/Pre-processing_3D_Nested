import argparse
import csv
import os
import re
from pathlib import Path


LABELS = {"Control": 0, "Prodromal": 1, "PD": 2}
IMAGE_ID_RE = re.compile(r"^I\d+$", re.IGNORECASE)


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fieldnames):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def inventory_raw(ppmi_root):
    inventory = {}
    root = Path(ppmi_root).resolve()
    for dirpath, _, filenames in os.walk(root):
        dcm_files = [name for name in filenames if name.lower().endswith(".dcm")]
        if not dcm_files:
            continue
        path = Path(dirpath).resolve()
        image_id = path.name.upper()
        if not IMAGE_ID_RE.match(image_id):
            raise RuntimeError(f"DICOM folder is not an Image ID directory: {path}")
        subject = path.relative_to(root).parts[0]
        if image_id in inventory:
            raise RuntimeError(f"Duplicate Image ID folder found: {image_id}")
        inventory[image_id] = {
            "subject_from_path": subject,
            "raw_dicom_dir": str(path),
            "dicom_file_count": len(dcm_files),
        }
    return inventory


def main():
    parser = argparse.ArgumentParser(description="Build raw inventory and analysis manifests.")
    parser.add_argument("--ppmi-root", required=True)
    parser.add_argument("--source-metadata", required=True)
    parser.add_argument("--cohort", required=True)
    parser.add_argument("--data-output", required=True)
    parser.add_argument("--metadata-output", required=True)
    args = parser.parse_args()

    source_rows = read_csv(args.source_metadata)
    cohort_rows = read_csv(args.cohort)
    source_by_id = {row["Image Data ID"].upper(): row for row in source_rows}
    inventory = inventory_raw(args.ppmi_root)

    metadata_rows = []
    for image_id in sorted(inventory, key=lambda value: int(value[1:])):
        disk = inventory[image_id]
        source = source_by_id.get(image_id, {})
        metadata_rows.append({
            "Image Data ID": image_id,
            "Subject": source.get("Subject", disk["subject_from_path"]),
            "Group": source.get("Group", ""),
            "Sex": source.get("Sex", ""),
            "Age": source.get("Age", ""),
            "Visit": source.get("Visit", ""),
            "Modality": source.get("Modality", ""),
            "Description": source.get("Description", ""),
            "Type": source.get("Type", ""),
            "Acq Date": source.get("Acq Date", ""),
            "Format": source.get("Format", ""),
            "raw_dicom_dir": disk["raw_dicom_dir"],
            "dicom_file_count": disk["dicom_file_count"],
            "metadata_match": "yes" if source else "no",
        })

    data_rows = []
    seen_subjects = set()
    seen_images = set()
    missing = []
    for row in cohort_rows:
        image_id = row["Image Data ID"].upper()
        subject = row["Subject"]
        if image_id not in inventory:
            missing.append(image_id)
            continue
        if subject in seen_subjects:
            raise RuntimeError(f"Cohort contains duplicate Subject: {subject}")
        if image_id in seen_images:
            raise RuntimeError(f"Cohort contains duplicate Image ID: {image_id}")
        seen_subjects.add(subject)
        seen_images.add(image_id)
        disk = inventory[image_id]
        group = row["Group"]
        data_rows.append({
            "sample_id": f"sub-{subject}_{image_id}",
            "Subject": subject,
            "Image Data ID": image_id,
            "Group": group,
            "label": LABELS[group],
            "Sex": row.get("Sex", ""),
            "Age": row.get("Age", ""),
            "Visit": row.get("Visit", ""),
            "Description": row.get("Description", ""),
            "Acq Date": row.get("Acq Date", ""),
            "raw_dicom_dir": disk["raw_dicom_dir"],
            "dicom_file_count": disk["dicom_file_count"],
        })

    if missing:
        raise RuntimeError(f"Selected Image IDs missing from raw data: {', '.join(missing)}")

    metadata_fields = [
        "Image Data ID", "Subject", "Group", "Sex", "Age", "Visit", "Modality",
        "Description", "Type", "Acq Date", "Format", "raw_dicom_dir",
        "dicom_file_count", "metadata_match",
    ]
    data_fields = [
        "sample_id", "Subject", "Image Data ID", "Group", "label", "Sex", "Age",
        "Visit", "Description", "Acq Date", "raw_dicom_dir", "dicom_file_count",
    ]
    write_csv(args.metadata_output, metadata_rows, metadata_fields)
    write_csv(args.data_output, data_rows, data_fields)
    print(f"metadata.csv rows: {len(metadata_rows)}")
    print(f"data.csv rows: {len(data_rows)}")
    for group in LABELS:
        print(f"{group}: {sum(row['Group'] == group for row in data_rows)}")


if __name__ == "__main__":
    main()
