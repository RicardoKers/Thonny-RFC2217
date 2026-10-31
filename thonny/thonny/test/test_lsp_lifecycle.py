import io
import json
import subprocess
import sys
import threading
from queue import Queue
from types import SimpleNamespace

import pytest

from thonny import lsp_proxy, lsp_types


class TestProxy(lsp_proxy.LanguageServerProxy):
    __test__ = False

    def _create_server_process(self):
        raise NotImplementedError

    def get_supported_language_ids(self):
        return {"python"}


@pytest.fixture
def make_proxy(monkeypatch):
    workbench = SimpleNamespace(
        event_generate=lambda *args: None,
        in_debug_mode=lambda: False,
        report_exception=lambda: pytest.fail("Unexpected protocol processing error"),
    )
    monkeypatch.setattr(lsp_proxy, "get_workbench", lambda: workbench)

    def create(proc, initialized=True):
        proxy = object.__new__(TestProxy)
        proxy._proc = proc
        proxy._invalidated = False
        proxy._shutdown_accepted = False
        proxy._last_request_id = 0
        proxy._pending_handlers = {}
        proxy._unprocessed_messages_from_server = Queue()
        proxy.server_capabilities = lsp_types.ServerCapabilities() if initialized else None
        return proxy

    return create


def test_graceful_shutdown_sends_exit_and_waits_for_server(make_proxy, tmp_path):
    transcript = tmp_path / "messages.json"
    server = """
import json, sys
from pathlib import Path
messages = []
while True:
    header = sys.stdin.buffer.readline()
    if not header:
        raise SystemExit(2)
    length = int(header.split(b':')[1])
    assert sys.stdin.buffer.readline() == b'\\r\\n'
    message = json.loads(sys.stdin.buffer.read(length))
    messages.append(message['method'])
    if message['method'] == 'shutdown':
        response = json.dumps({'jsonrpc': '2.0', 'id': message['id'], 'result': None}).encode()
        header = b'Content-Length: ' + str(len(response)).encode() + b'\\r\\n\\r\\n'
        sys.stdout.buffer.write(header + response)
        sys.stdout.buffer.flush()
    elif message['method'] == 'exit':
        Path(sys.argv[1]).write_text(json.dumps(messages))
        raise SystemExit(0)
"""
    proc = subprocess.Popen(
        [sys.executable, "-u", "-c", server, str(transcript)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    proxy = make_proxy(proc)
    listener = threading.Thread(target=proxy._listen_stdout, daemon=True)
    listener.start()
    try:
        proxy.shut_down()
        assert proc.poll() == 0
        assert json.loads(transcript.read_text()) == ["shutdown", "exit"]
        listener.join(timeout=2)
        assert not listener.is_alive()
        assert proxy._unprocessed_messages_from_server.empty()
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            stream.close()


def test_uninitialized_server_is_terminated_and_reaped(make_proxy):
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    proxy = make_proxy(proc, initialized=False)
    try:
        proxy.shut_down()
        assert proc.poll() is not None
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)


def test_failed_termination_uses_kill_and_wait(make_proxy):
    calls = []

    class Process:
        stdin = io.BytesIO()

        def poll(self):
            return None

        def terminate(self):
            calls.append("terminate")

        def kill(self):
            calls.append("kill")

        def wait(self, timeout):
            calls.append("wait")
            if "kill" not in calls:
                raise subprocess.TimeoutExpired("server", timeout)

    make_proxy(Process(), initialized=False).shut_down()
    assert calls == ["terminate", "wait", "kill", "wait"]


@pytest.mark.parametrize("stream_name", ["stdout", "stderr"])
def test_reader_stops_at_eof_even_if_process_is_still_alive(make_proxy, stream_name):
    class EofStream:
        calls = 0

        def readline(self):
            self.calls += 1
            if self.calls > 1:
                raise AssertionError("EOF must not be polled in a busy loop")
            return b""

    stream = EofStream()
    proc = SimpleNamespace(poll=lambda: None, **{stream_name: stream})
    proxy = make_proxy(proc)
    getattr(proxy, "_listen_" + stream_name)()
    assert stream.calls == 1
    assert proxy._unprocessed_messages_from_server.empty()
