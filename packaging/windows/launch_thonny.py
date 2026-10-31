"""Bootstrap the independent Windows distribution using its private runtime."""

import configparser
import json
import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def prepare_profile():
    if (ROOT / "portable.ini").exists():
        profile = ROOT / "user_data"
    else:
        profile = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "ThonnyRFC2217"
    profile.mkdir(parents=True, exist_ok=True)
    # This distribution always owns a separate profile, including backend children.
    os.environ["THONNY_USER_DIR"] = str(profile)
    os.environ["PATH"] = (
        str(ROOT / "Scripts") + os.pathsep + str(ROOT) + os.pathsep + os.environ.get("PATH", "")
    )
    for name in [
        "PYTHONHOME",
        "PYTHONPATH",
        "PYTHONSTARTUP",
        "PYTHONINSPECT",
        "TCL_LIBRARY",
        "TK_LIBRARY",
    ]:
        os.environ.pop(name, None)

    configuration = profile / "configuration.ini"
    settings = configparser.ConfigParser(interpolation=None)
    if configuration.exists():
        settings.read(configuration, encoding="utf-8")
    defaults = {
        "general": {"single_instance": "True"},
        "run": {"backend_name": "ESP32", "working_directory": str(ROOT / "examples")},
        "ESP32": {"port": "rfc2217://127.0.0.1:4000", "rfc2217_url": "rfc2217://127.0.0.1:4000"},
    }
    changed = False
    for section, values in defaults.items():
        if not settings.has_section(section):
            settings.add_section(section)
        for name, value in values.items():
            if not settings.has_option(section, name):
                settings.set(section, name, value)
                changed = True
    # A portable folder may have moved since its previous launch.
    if not Path(settings.get("run", "working_directory")).is_dir():
        settings.set("run", "working_directory", str(ROOT / "examples"))
        changed = True
    if changed:
        temporary = configuration.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as target:
            settings.write(target)
        temporary.replace(configuration)
    return profile


def smoke_test():
    import importlib.metadata
    import tkinter

    import serial

    import minny
    import thonny
    from thonny.plugins.basedpyright import _get_server_command

    os.environ["PATH"] = str(ROOT / "Scripts") + os.pathsep + os.environ.get("PATH", "")
    assert Path(sys.prefix).resolve() == ROOT
    assert Path(minny.__file__).resolve().is_relative_to(ROOT)
    assert Path(thonny.__file__).resolve().is_relative_to(ROOT)
    import shutil

    command = _get_server_command(shutil.which("basedpyright-langserver"))
    assert Path(command[0]).name.lower() == "node.exe"
    root = tkinter.Tk()
    root.withdraw()
    root.destroy()
    return {
        "distribution": "Thonny RFC2217",
        "python": sys.version.split()[0],
        "thonny": importlib.metadata.version("thonny"),
        "minny": importlib.metadata.version("minny"),
        "pyserial": serial.VERSION,
        "tk": tkinter.TkVersion,
        "node_direct": True,
        "private_runtime": True,
    }


def main():
    if "--smoke-test" in sys.argv:
        result = smoke_test()
        output = ROOT / "smoke-test.json"
        output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result), flush=True)
        return
    profile = prepare_profile()
    try:
        # Avoid reopening unavailable paths copied by a user from another machine.
        os.chdir(ROOT / "examples")
        args = sys.argv[1:]
        sys.argv = [str(ROOT / "ThonnyRFC2217.exe"), "--profile", "rfc2217", *args]
        from thonny.main import run

        run()
    except Exception:
        (profile / "launcher-error.log").write_text(traceback.format_exc(), encoding="utf-8")
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, traceback.format_exc(), "Thonny RFC2217", 0x10)
        raise


if __name__ == "__main__":
    main()
