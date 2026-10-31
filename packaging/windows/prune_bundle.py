"""Remove a narrow set of runtime-independent files from a Windows bundle.

The cleanup preserves Node, Basedpyright JavaScript, type stubs and licenses.
Jedi is excluded through runtime requirements rather than deleted here.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
from pathlib import Path

REPARSE_POINT = 0x400
DIRECTORIES = (
    Path("Lib/test"),
    Path("Lib/site-packages/nodejs_wheel/lib"),
)
BASEDPYRIGHT_DIST = Path("Lib/site-packages/basedpyright/dist")


def _reject_reparse_point(path: Path) -> None:
    details = path.lstat()
    if stat.S_ISLNK(details.st_mode) or getattr(details, "st_file_attributes", 0) & REPARSE_POINT:
        raise ValueError(f"Refusing a symlink or reparse point: {path}")


def _validate_bundle(bundle: Path) -> Path:
    absolute = Path(os.path.abspath(bundle))
    # Check before resolve(), which would otherwise hide an aliased bundle root.
    for path in [absolute, *absolute.parents]:
        _reject_reparse_point(path)
    resolved = absolute.resolve(strict=True)
    if not resolved.is_dir() or resolved == Path(resolved.anchor):
        raise ValueError("The bundle must be a dedicated application directory")
    for relative in [Path("python.exe"), Path("Lib/site-packages/nodejs_wheel/node.exe")]:
        if not (resolved / relative).is_file():
            raise ValueError(f"Missing required bundle component: {relative.as_posix()}")
    if not (resolved / BASEDPYRIGHT_DIST).is_dir():
        raise ValueError("The Basedpyright runtime directory is missing")
    return resolved


def _validated_target(bundle: Path, relative: Path) -> Path:
    target = bundle / relative
    resolved = target.resolve(strict=True)
    if resolved == bundle or not resolved.is_relative_to(bundle):
        raise ValueError(f"Cleanup target escapes the bundle: {relative}")
    current = target
    while current != bundle:
        _reject_reparse_point(current)
        current = current.parent
    return target


def measure_tree(root: Path) -> dict[str, int]:
    """Count files without traversing any link or Windows directory junction."""
    total_bytes = 0
    files = 0
    pending = [root]
    while pending:
        directory = pending.pop()
        _reject_reparse_point(directory)
        with os.scandir(directory) as entries:
            for entry in entries:
                path = Path(entry.path)
                _reject_reparse_point(path)
                if entry.is_dir(follow_symlinks=False):
                    pending.append(path)
                elif entry.is_file(follow_symlinks=False):
                    files += 1
                    total_bytes += entry.stat(follow_symlinks=False).st_size
    return {"files": files, "bytes": total_bytes}


def prune_bundle(bundle: Path) -> dict:
    bundle = _validate_bundle(bundle)
    # Complete the safety scan and target validation before the first mutation.
    before = measure_tree(bundle)
    candidates = [relative for relative in DIRECTORIES if (bundle / relative).exists()]
    candidates.extend(
        path.relative_to(bundle)
        for path in sorted((bundle / BASEDPYRIGHT_DIST).glob("pyright*.js.map"))
        if path.is_file()
    )
    targets = [(relative, _validated_target(bundle, relative)) for relative in candidates]
    removed = []
    for relative, target in targets:
        _validated_target(bundle, relative)
        if target.is_dir():
            details = measure_tree(target)
            shutil.rmtree(target)
        else:
            details = {"files": 1, "bytes": target.stat().st_size}
            target.unlink()
        removed.append({"path": relative.as_posix(), **details})
    after = measure_tree(bundle)
    return {
        "before": before,
        "after": after,
        "saved": {key: before[key] - after[key] for key in before},
        "removed": removed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = prune_bundle(args.bundle)
    output = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output, encoding="utf-8")
    print(output, end="")


if __name__ == "__main__":
    main()
