"""Build a relocatable full CPython/Tk application, without freezing the backend."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(command, **kwargs):
    print("Running:", " ".join(map(str, command)), flush=True)
    subprocess.run(list(map(str, command)), check=True, **kwargs)


def copy_runtime(base, destination):
    destination.mkdir(parents=True)
    for name in ["Lib", "DLLs", "tcl"]:
        ignore = (
            shutil.ignore_patterns("site-packages", "__pycache__", "*.pyc")
            if name == "Lib"
            else shutil.ignore_patterns("__pycache__", "*.pyc")
        )
        shutil.copytree(base / name, destination / name, ignore=ignore)
    for path in base.iterdir():
        if path.is_file() and (
            path.suffix.lower() in [".exe", ".dll"] or path.name == "LICENSE.txt"
        ):
            shutil.copy2(
                path,
                destination / ("PYTHON_LICENSE.txt" if path.name == "LICENSE.txt" else path.name),
            )
    (destination / "thonny_python.ini").write_text(
        "; Private Python for Thonny RFC2217\n", encoding="utf-8"
    )


def make_portable_scripts(python, bundle, env):
    # pip's generated Windows .exe launchers embed an absolute build-machine
    # interpreter path. Relative command wrappers keep console tools relocatable.
    query = "import json; from importlib.metadata import distributions; print(json.dumps([(d.metadata['Name'], e.name) for d in distributions() for e in d.entry_points if e.group == 'console_scripts']))"
    entries = json.loads(subprocess.check_output([python, "-I", "-c", query], env=env, text=True))
    scripts = bundle / "Scripts"
    for executable in scripts.glob("*.exe"):
        executable.unlink()
    for distribution, name in entries:
        if name == "thonny" or any(c in name for c in '/\\:"<>|?*'):
            continue
        script = (
            "import sys\nfrom importlib.metadata import distribution\n"
            f"entry = next(e for e in distribution({distribution!r}).entry_points if e.group == 'console_scripts' and e.name == {name!r})\n"
            "if __name__ == '__main__':\n    sys.exit(entry.load()())\n"
        )
        (scripts / (name + "-script.py")).write_text(script, encoding="utf-8")
        (scripts / (name + ".cmd")).write_text(
            f'@echo off\n"%~dp0..\\python.exe" -I "%~dp0{name}-script.py" %*\n',
            encoding="utf-8",
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=HERE.parents[1])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--base-python", type=Path, default=Path(sys.base_prefix))
    parser.add_argument("--version", default="0.1.0")
    parser.add_argument("--reuse", action="store_true")
    args = parser.parse_args()
    source = args.source_root.resolve()
    bundle = args.output_dir.resolve()
    if sys.version_info[:3] != (3, 11, 9) or sys.maxsize <= 2**32:
        raise SystemExit("Build this release with the validated CPython 3.11.9 x64 runtime.")
    if not args.reuse:
        if bundle.exists():
            raise SystemExit("Output already exists; choose a new directory or use --reuse.")
        print("Copying private CPython/Tk runtime", flush=True)
        copy_runtime(args.base_python.resolve(), bundle)
    python = bundle / "python.exe"
    env = dict(os.environ, PYTHONNOUSERSITE="1", PIP_DISABLE_PIP_VERSION_CHECK="1")
    for name in ["PYTHONHOME", "PYTHONPATH", "PYTHONSTARTUP", "TCL_LIBRARY", "TK_LIBRARY"]:
        env.pop(name, None)
    run([python, "-I", "-m", "ensurepip", "--upgrade"], env=env)
    wheels = bundle.parent / "wheels"
    wheels.mkdir(exist_ok=True)
    run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-deps",
            "--wheel-dir",
            wheels,
            source / "minny",
            source / "thonny",
        ],
        env=env,
    )
    project_wheels = [*wheels.glob("minny-*.whl"), *wheels.glob("thonny-*.whl")]
    assert len(project_wheels) == 2, project_wheels
    run(
        [
            python,
            "-I",
            "-m",
            "pip",
            "install",
            "--no-warn-script-location",
            "-r",
            HERE / "requirements-runtime.txt",
            *project_wheels,
        ],
        env=env,
    )
    run([python, "-I", "-m", "pip", "check"], env=env)
    make_portable_scripts(python, bundle, env)
    for name in ["launch_thonny.py"]:
        shutil.copy2(HERE / name, bundle / name)
    shutil.copytree(source / "examples", bundle / "examples", dirs_exist_ok=True)
    for name in ["README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "PROVENANCE.md"]:
        shutil.copy2(source / name, bundle / name)
    shutil.copytree(source / "thonny/licenses", bundle / "licenses/thonny", dirs_exist_ok=True)
    (bundle / "licenses/minny").mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / "minny/LICENSE", bundle / "licenses/minny/LICENSE")
    compiler = Path(os.environ["WINDIR"]) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
    run(
        [
            compiler,
            "/nologo",
            "/target:winexe",
            "/platform:x64",
            "/optimize+",
            "/reference:System.Windows.Forms.dll",
            "/reference:System.Core.dll",
            f"/win32icon:{source / 'thonny/thonny/res/thonny.ico'}",
            f"/out:{bundle / 'ThonnyRFC2217.exe'}",
            HERE / "Launcher.cs",
        ]
    )
    run([python, "-I", bundle / "launch_thonny.py", "--smoke-test"], env=env)
    run([sys.executable, HERE / "collect_licenses.py", "--bundle", bundle, "--source-root", source])
    installed = subprocess.check_output(
        [
            python,
            "-I",
            "-c",
            "from importlib.metadata import distributions; print('\\n'.join(sorted(d.metadata['Name']+'=='+d.version for d in distributions())))",
        ],
        env=env,
        text=True,
    )
    (bundle / "requirements-bundled.txt").write_text(installed, encoding="utf-8")
    metadata = dict(
        distribution="Thonny RFC2217",
        version=args.version,
        python="3.11.9",
        architecture="x64",
        source="https://github.com/RicardoKers/Thonny-RFC2217",
    )
    (bundle / "distribution.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    for name in ["thonny-6.0.0.dev1.dist-info", "minny-0.0.1a2.dist-info"]:
        direct_url = bundle / "Lib/site-packages" / name / "direct_url.json"
        if direct_url.is_file():
            direct_url.unlink()
    # Compiled caches embed build-machine paths and can be recreated at runtime.
    for path in bundle.rglob("*.pyc"):
        path.unlink()
    print("Bundle ready:", bundle, flush=True)


if __name__ == "__main__":
    main()
