from types import SimpleNamespace

import pytest

from thonny.editors import Editor
from thonny.workbench import Workbench


class EditorStub:
    is_local = Editor.is_local
    is_untitled = Editor.is_untitled
    get_target_path = Editor.get_target_path

    def __init__(self, uri):
        self._uri = uri

    def get_uri(self):
        return self._uri


def make_workbench(cwd, project=None, uri=None):
    editor = EditorStub(uri) if uri is not None else None
    return SimpleNamespace(
        get_local_cwd=lambda: str(cwd),
        get_local_project_path=lambda: str(project) if project is not None else None,
        get_editor_notebook=lambda: SimpleNamespace(get_current_editor=lambda: editor),
    )


def test_standalone_local_file_uses_its_directory_instead_of_home(tmp_path):
    home = tmp_path / "home"
    script = tmp_path / "examples" / "blink.py"
    workbench = make_workbench(home, uri=script.as_uri())

    assert Workbench._get_language_server_workspace_path(workbench) == str(script.parent)


def test_explicit_project_takes_precedence_over_active_file_directory(tmp_path):
    project = tmp_path / "project"
    script = tmp_path / "elsewhere" / "script.py"
    workbench = make_workbench(tmp_path, project=project, uri=script.as_uri())

    assert Workbench._get_language_server_workspace_path(workbench) == str(project)


@pytest.mark.parametrize("uri", [None, "untitled:1", "remote:/main.py"])
def test_no_saved_local_file_uses_local_working_directory(tmp_path, uri):
    workbench = make_workbench(tmp_path, uri=uri)

    assert Workbench._get_language_server_workspace_path(workbench) == str(tmp_path)


def test_initialize_root_uri_and_workspace_folder_agree(tmp_path):
    captured = []
    workbench = make_workbench(tmp_path, uri=(tmp_path / "examples" / "blink.py").as_uri())
    workbench._get_language_server_workspace_path = lambda: (
        Workbench._get_language_server_workspace_path(workbench)
    )
    workbench.shut_down_language_servers = lambda: None
    workbench._language_server_proxy_classes = [lambda params: captured.append(params)]
    workbench._ls_proxies = []
    workbench.get_option = lambda name: "en_US"
    workbench.in_debug_mode = lambda: False

    Workbench.start_or_restart_language_servers(workbench)

    expected_uri = (tmp_path / "examples").as_uri()
    assert len(captured) == 1
    assert captured[0].rootUri == expected_uri
    assert captured[0].workspaceFolders[0].uri == expected_uri
