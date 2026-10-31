import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "packaging/windows/prune_bundle.py"
SPEC = importlib.util.spec_from_file_location("prune_bundle", SCRIPT)
pruning = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pruning)


def put(root, name, content=b"runtime"):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


@pytest.fixture
def bundle(tmp_path):
    root = tmp_path / "bundle"
    for name in [
        "python.exe",
        "Lib/site-packages/nodejs_wheel/node.exe",
        "Lib/site-packages/basedpyright/dist/pyright-langserver.js",
        "Lib/site-packages/basedpyright/dist/typeshed-fallback/stdlib/builtins.pyi",
        "Lib/site-packages/pip/__init__.py",
        "licenses/runtime/Node.js/LICENSE.txt",
    ]:
        put(root, name)
    return root


def test_removes_only_auxiliary_files_and_reports_exact_savings(bundle):
    removable = [
        "Lib/test/test_math.py",
        "Lib/test/nested/data.txt",
        "Lib/site-packages/nodejs_wheel/lib/node_modules/npm/package.json",
        "Lib/site-packages/nodejs_wheel/lib/node_modules/corepack/dist/lib/corepack.cjs",
        "Lib/site-packages/basedpyright/dist/pyright.js.map",
        "Lib/site-packages/basedpyright/dist/pyright-langserver.js.map",
    ]
    for name in removable:
        put(bundle, name, b"auxiliary")
    # Similar filenames outside the declared policy are kept.
    keep = [
        "Lib/site-packages/basedpyright/dist/other.js.map",
        "Lib/site-packages/basedpyright/test/runtime.py",
        "examples/test.py",
    ]
    for name in keep:
        put(bundle, name)

    report = pruning.prune_bundle(bundle)

    assert report["saved"] == {"files": len(removable), "bytes": len(removable) * 9}
    assert all(not (bundle / name).exists() for name in removable)
    assert all((bundle / name).is_file() for name in keep)
    assert (bundle / "Lib/site-packages/nodejs_wheel/node.exe").is_file()
    assert (bundle / "Lib/site-packages/pip/__init__.py").is_file()
    assert (bundle / "licenses/runtime/Node.js/LICENSE.txt").is_file()
    assert (bundle / "Lib/site-packages/basedpyright/dist/pyright-langserver.js").is_file()
    assert (
        bundle / "Lib/site-packages/basedpyright/dist/typeshed-fallback/stdlib/builtins.pyi"
    ).is_file()
    assert not any(str(bundle) in item["path"] for item in report["removed"])


def test_second_cleanup_is_idempotent(bundle):
    put(bundle, "Lib/test/test_math.py")
    pruning.prune_bundle(bundle)
    assert pruning.prune_bundle(bundle)["saved"] == {"files": 0, "bytes": 0}


def test_missing_node_aborts_before_removing_anything(bundle):
    removable = put(bundle, "Lib/test/test_math.py")
    (bundle / "Lib/site-packages/nodejs_wheel/node.exe").unlink()
    with pytest.raises(ValueError, match="Missing required bundle component"):
        pruning.prune_bundle(bundle)
    assert removable.is_file()


def test_target_outside_bundle_is_rejected(bundle, tmp_path):
    outside = put(tmp_path, "outside/sentinel.txt")
    with pytest.raises(ValueError, match="escapes the bundle"):
        pruning._validated_target(bundle, Path("../outside"))
    assert outside.read_bytes() == b"runtime"


@pytest.mark.parametrize("location", ["root", "cleanup-target"])
def test_windows_junction_is_rejected_before_any_cleanup(bundle, monkeypatch, location):
    removable = put(bundle, "Lib/test/test_math.py")
    junction = bundle if location == "root" else bundle / "Lib/site-packages/nodejs_wheel/lib"
    junction.mkdir(exist_ok=True)
    real_lstat = Path.lstat

    def lstat(path):
        details = real_lstat(path)
        if path == junction:
            return SimpleNamespace(st_mode=details.st_mode, st_file_attributes=0x400)
        return details

    monkeypatch.setattr(Path, "lstat", lstat)
    with pytest.raises(ValueError, match="reparse point"):
        pruning.prune_bundle(bundle)
    assert removable.is_file()


def test_aliased_root_is_rejected(bundle, tmp_path):
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(bundle, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"Directory symlink creation is unavailable: {error}")
    with pytest.raises(ValueError, match="symlink or reparse point"):
        pruning.prune_bundle(alias)
