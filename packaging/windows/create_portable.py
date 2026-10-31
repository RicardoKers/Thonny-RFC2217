"""Create the portable ZIP from a clean application bundle."""

import argparse
from pathlib import Path
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", default="0.1.0")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    prefix = "Thonny-RFC2217-" + args.version
    with zipfile.ZipFile(args.output, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(args.bundle.rglob("*")):
            if path.is_file() and not any(part in {"__pycache__", ".pytest_cache", "user_data"} for part in path.parts):
                archive.write(path, prefix + "/" + path.relative_to(args.bundle).as_posix())
        archive.writestr(prefix + "/portable.ini", "; Store settings in user_data next to the application.\n")
    with zipfile.ZipFile(args.output) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise RuntimeError("ZIP integrity failure: " + bad)
    print(args.output)


if __name__ == "__main__":
    main()
