import logging
import sys
import tempfile
from pathlib import Path

import dicom2nifti
import dicom2nifti.settings as settings


logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(name)s: %(message)s")


def run(folder, relaxed=False):
    settings.disable_validate_slice_increment()
    if relaxed:
        for name in ("disable_validate_orientation", "disable_validate_orthogonal"):
            function = getattr(settings, name, None)
            if function:
                function()
    with tempfile.TemporaryDirectory(prefix="failed_t2_convert_") as out:
        print(f"\n=== folder={folder} relaxed={relaxed} ===")
        try:
            dicom2nifti.convert_directory(folder, out, compression=True, reorient=True)
        except Exception as exc:
            print(f"TOP_LEVEL_EXCEPTION: {type(exc).__name__}: {exc}")
        outputs = list(Path(out).glob("*"))
        print("OUTPUTS:", [(p.name, p.stat().st_size) for p in outputs])


def main():
    print("AVAILABLE SETTINGS:", [name for name in dir(settings) if name.startswith(("disable_", "enable_"))])
    for folder in sys.argv[1:]:
        run(folder, relaxed=False)
        run(folder, relaxed=True)


if __name__ == "__main__":
    main()
