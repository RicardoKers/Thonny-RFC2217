import ast
import tkinter as tk
from types import SimpleNamespace

import pytest

from thonny.config import ConfigurationManager
from thonny.plugins.micropython import mp_front


class ConnectionPage(mp_front.BareMetalMicroPythonConfigPage):
    """Use the real connection widgets without unrelated options and package UI."""

    backend_name = "ESP32"

    @property
    def allow_webrepl(self):
        return True

    def create_and_add_stubs_page(self, proxy_class):
        return self.create_and_add_empty_page("Type stubs")

    def _init_options_page(self):
        pass

    def _init_advanced_page(self):
        pass


@pytest.fixture
def settings(tmp_path, monkeypatch):
    config = ConfigurationManager(str(tmp_path / "configuration.ini"))
    config.set_default("ESP32.port", None)
    config.set_default("ESP32.rfc2217_url", mp_front.DEFAULT_RFC2217_URL)
    config.set_default("ESP32.webrepl_url", mp_front.DEFAULT_WEBREPL_URL)
    config.set_default("ESP32.webrepl_password", "")
    monkeypatch.setattr(mp_front, "get_workbench", lambda: config)
    monkeypatch.setattr("thonny.running.get_workbench", lambda: config)
    monkeypatch.setattr(mp_front, "list_serial_ports", lambda **kwargs: [])
    return config


@pytest.fixture(scope="module")
def tk_root():
    owns_root = tk._default_root is None
    try:
        root = tk._default_root or tk.Tk()
    except tk.TclError as e:
        pytest.skip(f"Tk display is unavailable: {e}")
    root.withdraw()
    yield root
    if owns_root:
        root.destroy()


@pytest.fixture
def options_dialog(settings, tk_root, monkeypatch):
    from thonny import config_ui
    from thonny.plugins import backend_config_page

    settings.set_default("run.backend_name", "ESP32")
    settings.get_options_snapshot = settings.get_snapshot
    spec = SimpleNamespace(
        name="ESP32",
        description="MicroPython (ESP32)",
        sort_key="35",
        config_page_constructor=ConnectionPage,
    )
    settings.get_backends = lambda: {"ESP32": spec}
    settings.get_editor_notebook = lambda: SimpleNamespace(
        try_close_remote_files_from_another_machine=lambda *args: True
    )
    settings.report_exception = lambda message: pytest.fail(message)
    monkeypatch.setattr(config_ui, "get_workbench", lambda: settings)
    monkeypatch.setattr(backend_config_page, "get_workbench", lambda: settings)
    dialogs = []

    def create(port):
        settings.set_option("ESP32.port", port)
        dialog = config_ui.ConfigurationDialog(
            tk_root, [("backend", "Interpreter", backend_config_page.BackendConfigurationPage, 1)]
        )
        dialogs.append(dialog)
        return dialog, dialog._page_records[0][2]._current_page

    yield create
    for dialog in dialogs:
        if dialog.winfo_exists():
            dialog.destroy()


def test_options_ok_applies_url_edit_without_eager_option_changes(settings, options_dialog):
    dialog, page = options_dialog("rfc2217://127.0.0.1:4000")
    page._rfc2217_url_var.set("rfc2217://localhost:4000")
    assert dialog.get_changed_options() == []
    dialog._ok_button.invoke()
    assert not dialog.winfo_exists()
    assert dialog.backend_restart_required
    assert settings.get_option("ESP32.port") == "rfc2217://localhost:4000"
    assert settings.get_option("ESP32.rfc2217_url") == "rfc2217://localhost:4000"


def test_options_unchanged_ok_does_not_restart_backend(settings, options_dialog):
    dialog, page = options_dialog("rfc2217://127.0.0.1:4000")
    assert not page._connection_is_modified()
    dialog._ok_button.invoke()
    assert not dialog.backend_restart_required
    assert settings.get_option("ESP32.port") == "rfc2217://127.0.0.1:4000"


def test_options_ok_applies_rfc_transport_selection(settings, options_dialog):
    dialog, page = options_dialog("COM7")
    page._port_desc_variable.set(mp_front.RFC2217_OPTION_DESC)
    page._rfc2217_url_var.set("rfc2217://localhost:4000")
    assert dialog.get_changed_options() == []
    dialog._ok_button.invoke()
    assert dialog.backend_restart_required
    assert settings.get_option("ESP32.port") == "rfc2217://localhost:4000"


def test_options_invalid_url_keeps_dialog_open_and_settings_unchanged(
    settings, options_dialog, monkeypatch
):
    dialog, page = options_dialog("rfc2217://127.0.0.1:4000")
    errors = []
    monkeypatch.setattr(
        mp_front.messagebox, "showerror", lambda *args, **kwargs: errors.append(args)
    )
    page._rfc2217_url_var.set("rfc2217://localhost:70000")
    dialog._ok_button.invoke()
    assert errors
    assert dialog.winfo_exists()
    assert not dialog.backend_restart_required
    assert settings.get_option("ESP32.port") == "rfc2217://127.0.0.1:4000"
    assert settings.get_option("ESP32.rfc2217_url") == mp_front.DEFAULT_RFC2217_URL
    page._rfc2217_url_var.set("rfc2217://localhost:4000")
    dialog._cancel_button.invoke()
    assert settings.get_option("ESP32.port") == "rfc2217://127.0.0.1:4000"
    assert not dialog.backend_restart_required


def test_connection_form_persists_and_restores_url(settings, tk_root, monkeypatch):
    page = ConnectionPage(tk_root)
    assert mp_front.RFC2217_OPTION_DESC in page._port_combo["values"]
    assert page._port_combo.instate(["readonly"])
    page._port_desc_variable.set(mp_front.RFC2217_OPTION_DESC)
    page._rfc2217_url_var.set("rfc2217://127.0.0.1:4000")
    assert page.get_selected_port() is None
    assert page.apply([])
    assert page.should_restart([])
    settings.save()
    page.destroy()

    restored = ConfigurationManager(settings._filename)
    monkeypatch.setattr(mp_front, "get_workbench", lambda: restored)
    reopened = ConnectionPage(tk_root)
    try:
        assert reopened.rfc2217_selected()
        assert reopened._rfc2217_url_var.get() == "rfc2217://127.0.0.1:4000"
        reopened._refresh_ports()
        assert reopened.rfc2217_selected()
        assert reopened.get_new_machine_id() == "rfc2217://127.0.0.1:4000"
    finally:
        reopened.destroy()


@pytest.mark.parametrize(
    "url",
    [
        "",
        "127.0.0.1:4000",
        "socket://127.0.0.1:4000",
        "rfc2217://:4000",
        "rfc2217://localhost",
        "rfc2217://localhost:0",
        "rfc2217://localhost:65536",
        "rfc2217://localhost:abc",
        "rfc2217://user:secret@localhost:4000",
    ],
)
def test_invalid_url_does_not_modify_settings(settings, tk_root, monkeypatch, url):
    settings.set_option("ESP32.port", "COM7")
    errors = []
    monkeypatch.setattr(
        mp_front.messagebox, "showerror", lambda *args, **kwargs: errors.append(args)
    )
    page = ConnectionPage(tk_root)
    try:
        page._port_desc_variable.set(mp_front.RFC2217_OPTION_DESC)
        page._rfc2217_url_var.set(url)
        assert page.apply([]) is False
        assert settings.get_option("ESP32.port") == "COM7"
        assert settings.get_option("ESP32.rfc2217_url") == mp_front.DEFAULT_RFC2217_URL
        assert errors
    finally:
        page.destroy()


def test_switching_to_webrepl_retains_rfc_endpoint(settings, tk_root):
    settings.set_option("ESP32.port", "rfc2217://remote.example:4000")
    page = ConnectionPage(tk_root)
    try:
        assert page.apply([])
        page._port_desc_variable.set(mp_front.WEBREPL_OPTION_DESC)
        page._webrepl_url_var.set("ws://192.168.4.1:8266/")
        page._webrepl_password_var.set("password")
        assert page.apply([])
        assert settings.get_option("ESP32.port") == "webrepl"
        assert settings.get_option("ESP32.rfc2217_url") == "rfc2217://remote.example:4000"
        assert settings.get_option("ESP32.webrepl_password") == "password"
        page._port_desc_variable.set(mp_front.RFC2217_OPTION_DESC)
        assert page.get_selected_port_name() == "rfc2217://remote.example:4000"
    finally:
        page.destroy()


def test_local_serial_selection_uses_existing_port(settings, tk_root, monkeypatch):
    serial_port = SimpleNamespace(
        device="COM7",
        product="USB serial",
        interface=None,
        description="USB serial (COM7)",
        vid=0x303A,
        pid=0x1001,
        manufacturer="Vendor",
        serial_number="123",
    )
    monkeypatch.setattr(mp_front, "list_serial_ports", lambda **kwargs: [serial_port])
    page = ConnectionPage(tk_root)
    try:
        page._port_desc_variable.set(mp_front.get_serial_port_label(serial_port))
        assert page.get_selected_port() is serial_port
        assert page.apply([])
        assert settings.get_option("ESP32.port") == "COM7"
    finally:
        page.destroy()


def test_remote_switcher_entry_needs_no_usb_port(settings, monkeypatch):
    class Proxy(mp_front.BareMetalMicroPythonProxy):
        backend_name = "ESP32"
        backend_description = "MicroPython (ESP32)"

    url = "rfc2217://remote.example:4000"
    configuration = {"run.backend_name": "ESP32", "ESP32.port": url}
    settings.set_option("ESP32.last_configurations", [configuration])
    monkeypatch.setattr(
        mp_front, "get_port_info", lambda port: pytest.fail("Queried USB for RFC URL")
    )
    proxy = Proxy.__new__(Proxy)
    proxy._port = url
    assert proxy._should_remember_configuration(configuration)
    assert proxy.get_current_switcher_configuration() == configuration
    assert Proxy.get_switcher_entries() == [(configuration, "MicroPython (ESP32)  •  " + url, url)]
    proxy._check_remember_current_configuration()


@pytest.mark.parametrize("port", ["rfc2217://localhost:4000", "COM7", "webrepl"])
def test_launcher_preserves_transport_and_existing_serial_settings(settings, port):
    settings.set_option("ESP32.port", port)
    settings.set_option("ESP32.dtr", False)
    settings.set_option("ESP32.rts", True)
    settings.set_option("ESP32.submit_mode", "raw_paste")
    settings.set_option("ESP32.webrepl_submit_mode", "paste")
    proxy = mp_front.BareMetalMicroPythonProxy.__new__(mp_front.BareMetalMicroPythonProxy)
    proxy.backend_name = "ESP32"
    proxy._port = port
    proxy._clean_start = True
    proxy._get_time_args = lambda: {}
    proxy._get_project_args = lambda: {}
    arguments = ast.literal_eval(proxy._get_launcher_with_args()[1])
    assert arguments["port"] == port
    assert arguments["dtr"] is False
    assert arguments["rts"] is True
    assert arguments["submit_mode"] == ("paste" if port == "webrepl" else "raw_paste")
    if port == "webrepl":
        assert arguments["url"] == mp_front.DEFAULT_WEBREPL_URL
        assert arguments["password"] == ""


def test_backend_routes_minny_output_and_input_via_ide(monkeypatch):
    import io
    import queue

    from minny.io_handling import IOHandler

    from thonny.backend import MainBackend
    from thonny.common import InputSubmission, parse_message
    from thonny.plugins.micropython.mp_back import MicroPythonBackend

    class Backend(MicroPythonBackend):
        # Isolate initialization and I/O without opening a device or command reader.
        __abstractmethods__ = frozenset()

        def mainloop(self):
            self._tmgr._io_handler._send_output("device output\n", "stdout")
            self._tmgr._io_handler._send_output("device error\n", "stderr")
            self._incoming_message_queue.put(InputSubmission(data="hello\n"))
            self._tmgr._io_handler._check_for_side_commands()

    # ABC computes the set after the class body, so clear it for this test subclass.
    Backend.__abstractmethods__ = frozenset()
    submitted = []
    tmgr = SimpleNamespace(
        _io_handler=IOHandler(),
        _welcome_text="MicroPython",
        get_cwd=lambda: "/",
        get_sys_path=lambda: ["/"],
        get_default_target=lambda: "/lib",
        get_device_id=lambda: "device",
        get_welcome_text=lambda: "MicroPython",
        _submit_input=submitted.append,
    )

    def initialize_backend(self):
        self._incoming_message_queue = queue.Queue()
        self._last_sent_output = ""

    monkeypatch.setattr(MainBackend, "__init__", initialize_backend)
    output = io.StringIO()
    monkeypatch.setattr("sys.stdout", output)
    backend = Backend(tmgr, {"project_manager": "-"})
    messages = [parse_message(line) for line in output.getvalue().splitlines()]
    program_output = [msg for msg in messages if msg.event_type == "ProgramOutput"]
    assert [(msg.stream_name, msg.data) for msg in program_output] == [
        ("stdout", "device output\n"),
        ("stderr", "device error\n"),
    ]
    assert submitted == ["hello\n"]
    assert backend._last_sent_output == "device error\n"
