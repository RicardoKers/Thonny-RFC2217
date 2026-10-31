"""Measure actual Basedpyright restart/exit behavior without a board or GUI."""

import ctypes
import json
import os
import time
from ctypes import wintypes
from pathlib import Path
from types import SimpleNamespace

import thonny
from thonny import lsp_types
from thonny.plugins.basedpyright import BasedpyrightProxy

ROOT = Path(__file__).resolve().parents[1]


def cpu_seconds(process):
    creation, exit_time, kernel, user = [wintypes.FILETIME() for _ in range(4)]
    get_times = ctypes.windll.kernel32.GetProcessTimes
    get_times.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    if not get_times(
        process._handle, *(ctypes.byref(t) for t in [creation, exit_time, kernel, user])
    ):
        raise ctypes.WinError()
    return sum((t.dwHighDateTime << 32) + t.dwLowDateTime for t in [kernel, user]) / 10_000_000


def working_set_mb(process):
    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (name, ctypes.c_size_t)
            for name in [
                "PeakWorkingSetSize",
                "WorkingSetSize",
                "QuotaPeakPagedPoolUsage",
                "QuotaPagedPoolUsage",
                "QuotaPeakNonPagedPoolUsage",
                "QuotaNonPagedPoolUsage",
                "PagefileUsage",
                "PeakPagefileUsage",
            ]
        ]

    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    get_memory = ctypes.windll.psapi.GetProcessMemoryInfo
    get_memory.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    if not get_memory(process._handle, ctypes.byref(counters), counters.cb):
        raise ctypes.WinError()
    return counters.WorkingSetSize / 1024**2


def main():
    if os.name != "nt":
        raise SystemExit("The CPU/process measurement in this probe requires Windows.")
    os.environ["PATH"] = str(ROOT / ".venv/Scripts") + os.pathsep + os.environ["PATH"]
    user_dir = ROOT / "test-results/lsp-probe"
    user_dir.mkdir(parents=True, exist_ok=True)
    thonny._thonny_user_dir = str(user_dir)
    stubs = ROOT / ".thonny-user/stubs/ESP32"
    stubs.mkdir(parents=True, exist_ok=True)
    workbench = SimpleNamespace(
        event_generate=lambda *args: None,
        in_debug_mode=lambda: False,
        after=lambda *args: None,
        report_exception=lambda: (_ for _ in ()).throw(RuntimeError("LSP processing failed")),
        get_local_project_path=lambda: None,
    )
    backend = SimpleNamespace(
        interpreter_is_cpython_compatible=lambda: False,
        has_local_interpreter=lambda: False,
        get_user_stubs_location=lambda: str(stubs),
    )
    thonny._workbench = workbench
    thonny._runner = SimpleNamespace(get_backend_proxy=lambda: backend)
    source = ROOT / "examples/blink_gpio4.py"
    workspace_uri = source.parent.as_uri()
    results = []
    previous = []

    def pump(proxy, seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            proxy._process_messages_from_server()
            time.sleep(0.02)

    for cycle in range(1, 5):
        params = lsp_types.InitializeParams(
            processId=os.getpid(),
            capabilities=lsp_types.ClientCapabilities(),
            rootUri=workspace_uri,
            workspaceFolders=[lsp_types.WorkspaceFolder(uri=workspace_uri, name="examples")],
        )
        proxy = BasedpyrightProxy(params)
        try:
            deadline = time.monotonic() + 15
            while not proxy.is_initialized() and time.monotonic() < deadline:
                pump(proxy, 0.05)
            assert proxy.is_initialized(), "Basedpyright failed to initialize"
            assert Path(proxy._proc.args[0]).name.lower() == "node.exe", proxy._proc.args
            proxy.notify_did_open_text_document(
                lsp_types.DidOpenTextDocumentParams(
                    textDocument=lsp_types.TextDocumentItem(
                        uri=source.as_uri(),
                        languageId="python",
                        version=1,
                        text=source.read_text(encoding="utf-8"),
                    )
                )
            )
            pump(proxy, 4)
            start = time.monotonic()
            start_cpu = cpu_seconds(proxy._proc)
            pump(proxy, 3)
            elapsed = time.monotonic() - start
            cpu = cpu_seconds(proxy._proc) - start_cpu
            result = dict(
                cycle=cycle,
                pid=proxy._proc.pid,
                workspace=workspace_uri,
                idle_cpu_seconds=round(cpu, 4),
                sample_seconds=round(elapsed, 2),
                idle_cpu_percent_of_one_core=round(100 * cpu / elapsed, 2),
                working_set_mb=round(working_set_mb(proxy._proc), 1),
            )
        finally:
            shutdown_start = time.monotonic()
            proxy.shut_down()
        assert proxy._proc.returncode == 0, proxy._proc.returncode
        assert all(proc.poll() is not None for proc in previous), "A previous server remains alive"
        result.update(
            exit_code=proxy._proc.returncode,
            shutdown_seconds=round(time.monotonic() - shutdown_start, 3),
        )
        results.append(result)
        previous.append(proxy._proc)
        print(json.dumps(result), flush=True)

    output = ROOT / "test-results/language-server.json"
    output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("PASS: four actual language servers initialized and exited; no previous server alive.")


if __name__ == "__main__":
    main()
