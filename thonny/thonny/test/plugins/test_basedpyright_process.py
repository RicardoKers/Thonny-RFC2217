import os
from types import SimpleNamespace

from thonny.plugins import basedpyright


def test_windows_python_package_launches_node_directly(tmp_path, monkeypatch):
    scripts = tmp_path / "Scripts"
    server = tmp_path / "basedpyright"
    node_package = tmp_path / "nodejs_wheel"
    for directory in [scripts, server, node_package]:
        directory.mkdir()
    script = server / "langserver.index.js"
    node = node_package / "node.exe"
    script.touch()
    node.touch()
    specs = {
        "basedpyright": SimpleNamespace(origin=str(server / "__init__.py")),
        "nodejs_wheel": SimpleNamespace(origin=str(node_package / "__init__.py")),
    }
    monkeypatch.setattr(basedpyright, "os", SimpleNamespace(name="nt", path=os.path))
    monkeypatch.setattr(basedpyright.sysconfig, "get_path", lambda _: str(scripts))
    monkeypatch.setattr(basedpyright.importlib.util, "find_spec", specs.get)
    launcher = str(scripts / "basedpyright-langserver.exe")

    assert basedpyright._get_server_command(launcher) == [str(node), str(script), "--stdio"]
    node.unlink()
    assert basedpyright._get_server_command(launcher) == [launcher, "--stdio"]


def test_external_language_server_launcher_is_preserved(tmp_path, monkeypatch):
    monkeypatch.setattr(basedpyright, "os", SimpleNamespace(name="nt", path=os.path))
    monkeypatch.setattr(basedpyright.sysconfig, "get_path", lambda _: str(tmp_path / "Scripts"))
    launcher = str(tmp_path / "external" / "basedpyright-langserver.cmd")
    assert basedpyright._get_server_command(launcher) == [launcher, "--stdio"]


def test_posix_language_server_launcher_is_preserved(monkeypatch):
    monkeypatch.setattr(basedpyright, "os", SimpleNamespace(name="posix", path=os.path))
    assert basedpyright._get_server_command("/usr/bin/basedpyright-langserver") == [
        "/usr/bin/basedpyright-langserver",
        "--stdio",
    ]
