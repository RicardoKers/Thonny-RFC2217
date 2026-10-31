"""Collect the notices of the actual private-runtime distributions, offline.

Usage: python collect_licenses.py --bundle build/bundle --source-root .
Additional upstream notices not present in a wheel belong in the adjacent
licenses/ directory as <distribution>-<version>-LICENSE.txt. No package or
license is downloaded by this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from importlib import metadata
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
LICENSE_NAME = re.compile(r"^(?:licen[cs]e|copying|copyright|notice)(?:$|[._-])", re.I)
CODE_SUFFIXES = {".py", ".pyi", ".js", ".ts", ".c", ".h", ".go"}


def safe_component(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip(".") or "unknown"


def notice_file(path: Path | PurePosixPath) -> bool:
    return bool(LICENSE_NAME.match(path.name)) and path.suffix.lower() not in CODE_SUFFIXES


def copy_notice(source: Path, target: Path, bundle: Path, origin: str) -> dict:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return {
        "path": target.relative_to(bundle).as_posix(),
        "source": origin,
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
    }


def supplemental_license(name: str, version: str, source_root: Path) -> Path | None:
    names = {
        f"{name}-{version}-LICENSE.txt",
        f"{name.replace('_', '-')}-{version}-LICENSE.txt",
        f"{name.replace('-', '_')}-{version}-LICENSE.txt",
    }
    for directory in [HERE / "licenses", source_root / "packaging/windows/licenses"]:
        for filename in sorted(names):
            candidate = directory / filename
            if candidate.is_file():
                return candidate
    return None


def collect(bundle: Path, source_root: Path, node_license: Path | None = None) -> dict:
    bundle = bundle.resolve()
    source_root = source_root.resolve()
    site_packages = bundle / "Lib/site-packages"
    if not site_packages.is_dir():
        raise ValueError("The bundle must contain Lib/site-packages.")

    notices_root = bundle / "licenses"
    notices_root.mkdir(parents=True, exist_ok=True)
    components = []
    errors = []
    source_licenses = {
        "thonny": source_root / "thonny/LICENSE.txt",
        "minny": source_root / "minny/LICENSE",
    }
    for name, source in source_licenses.items():
        if not source.is_file():
            errors.append(f"The {name} source license is missing.")
            continue
        record = copy_notice(
            source, notices_root / name / source.name, bundle, f"{name}/{source.name}"
        )
        components.append({"name": name, "license": "MIT", "license_files": [record]})

    upstream_notices = source_root / "thonny/licenses"
    if upstream_notices.is_dir():
        shutil.copytree(upstream_notices, notices_root / "thonny", dirs_exist_ok=True)
        components.append(
            {
                "name": "Thonny upstream dependency and icon notices",
                "license": "See retained license files, including Tcl/Tk and Eclipse icons.",
                "path": "licenses/thonny",
            }
        )
    else:
        errors.append("The Thonny dependency/icon notices directory is missing.")

    python_license = bundle / "PYTHON_LICENSE.txt"
    if python_license.is_file():
        record = copy_notice(
            python_license, notices_root / "CPython-LICENSE.txt", bundle, "PYTHON_LICENSE.txt"
        )
        components.append(
            {
                "name": "CPython",
                "license": "PSF and bundled component terms",
                "license_files": [record],
            }
        )
    else:
        errors.append("The bundle must retain the CPython runtime's PYTHON_LICENSE.txt.")

    tcl_files = []
    tcl_root = bundle / "tcl"
    if tcl_root.is_dir():
        for source in sorted(tcl_root.rglob("*")):
            if source.is_file() and (notice_file(source) or source.name.lower() == "license.terms"):
                relative = source.relative_to(tcl_root)
                tcl_files.append(
                    copy_notice(
                        source,
                        notices_root / "tcl" / relative,
                        bundle,
                        "tcl/" + relative.as_posix(),
                    )
                )
    if tcl_files:
        components.append({"name": "Tcl/Tk runtime notices", "license_files": tcl_files})
    if not (notices_root / "thonny/TCLTK-LICENSE.txt").is_file() and not tcl_files:
        errors.append("No Tcl/Tk license notice was found.")

    distributions = []
    installed = sorted(
        metadata.distributions(path=[str(site_packages)]),
        key=lambda dist: (dist.metadata.get("Name", "").casefold(), dist.version),
    )
    for dist in installed:
        name = dist.metadata.get("Name") or "unknown"
        version = dist.version
        target = notices_root / "runtime" / safe_component(f"{name}-{version}")
        license_files = []
        records = []
        for entry in dist.files or []:
            relative = PurePosixPath(str(entry).replace("\\", "/"))
            if relative.is_absolute() or ".." in relative.parts or not notice_file(relative):
                continue
            source = Path(dist.locate_file(entry)).resolve()
            # Malformed metadata must not copy arbitrary files from the build machine.
            if source.is_file() and source.is_relative_to(bundle):
                records.append((relative.as_posix(), source))
        for sequence, (relative, source) in enumerate(sorted(records), 1):
            # Flatten notices to avoid adding long paths to npm/type-stub trees.
            filename = f"{sequence:03d}-{safe_component(source.name)}"
            license_files.append(copy_notice(source, target / filename, bundle, relative))

        if not license_files:
            source = source_licenses.get(name.lower()) or supplemental_license(
                name, version, source_root
            )
            if source and source.is_file():
                license_files.append(
                    copy_notice(
                        source, target / "LICENSE.txt", bundle, f"supplemental/{source.name}"
                    )
                )
            else:
                errors.append(f"No full license/notice was found for {name} {version}.")

        license_value = dist.metadata.get("License-Expression") or dist.metadata.get("License")
        if not license_value:
            license_value = (
                "; ".join(
                    item
                    for item in dist.metadata.get_all("Classifier", [])
                    if item.startswith("License ::")
                )
                or "Not specified in distribution metadata; see bundled notices."
            )
        distributions.append(
            {
                "name": name,
                "version": version,
                "license": license_value,
                "license_files": license_files,
            }
        )

    node = site_packages / "nodejs_wheel/node.exe"
    if node.is_file():
        version = next(
            (
                dist.version
                for dist in installed
                if dist.metadata.get("Name") == "nodejs-wheel-binaries"
            ),
            None,
        )
        if version is None:
            errors.append("Node is present, but nodejs-wheel-binaries metadata is missing.")
        else:
            candidates = [node_license] if node_license else []
            candidates += [
                HERE / "licenses" / f"Node-v{version}-LICENSE.txt",
                source_root / "packaging/windows/licenses" / f"Node-v{version}-LICENSE.txt",
                node.parent / "LICENSE",
            ]
            source = next((path for path in candidates if path and path.is_file()), None)
            if source is None or "Copyright Node.js contributors" not in source.read_text(
                encoding="utf-8"
            ):
                errors.append(
                    f"The full Node.js v{version} LICENSE is required; provide --node-license PATH. "
                    "The nodejs-wheel wrapper MIT license is not the Node.js license bundle."
                )
            else:
                record = copy_notice(
                    source,
                    notices_root / "Node.js" / "LICENSE.txt",
                    bundle,
                    f"https://raw.githubusercontent.com/nodejs/node/v{version}/LICENSE",
                )
                components.append(
                    {
                        "name": "Node.js",
                        "version": version,
                        "license": "MIT and bundled third-party component terms",
                        "license_files": [record],
                    }
                )

    result = {
        "schema_version": 1,
        "description": "Licenses collected from the actual bundled runtime; paths are bundle-relative.",
        "components": components,
        "distributions": distributions,
        "errors": errors,
    }
    (notices_root / "INDEX.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Bundled runtime license index",
        "",
        "Original license and copyright notices are preserved in this directory.",
        "The distribution metadata license label is an index, not a replacement for each full notice.",
        "See INDEX.json for the component inventory, notice origins, and SHA-256 hashes.",
        "",
        "| Distribution | Version | License notices |",
        "|---|---|---|",
    ]
    lines += [
        f"| {dist['name']} | {dist['version']} | {len(dist['license_files'])} |"
        for dist in distributions
    ]
    (notices_root / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--node-license", type=Path)
    args = parser.parse_args()
    result = collect(args.bundle, args.source_root, args.node_license)
    if result["errors"]:
        for error in result["errors"]:
            print("License collection error:", error)
        raise SystemExit(1)
    count = sum(len(item["license_files"]) for item in result["distributions"])
    print(f"Collected {count} notices for {len(result['distributions'])} installed distributions.")


if __name__ == "__main__":
    main()
