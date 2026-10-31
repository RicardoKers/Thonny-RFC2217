"""Opt-in real-device test of Thonny's ESP32 backend, not just a TCP probe.

Run with the workspace venv. Requires the external simulator already running.
Creates only a uniquely named test directory and removes that directory's files.
Never overwrites the device's root boot.py or main.py.
"""

import argparse
import json
import os
import queue
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from thonny.common import (
    MESSAGE_MARKER,
    ImmediateCommand,
    InlineCommand,
    InlineResponse,
    ToplevelCommand,
    ToplevelResponse,
    parse_message,
    serialize_message,
)

ROOT = Path(__file__).resolve().parents[1]


class Backend:
    def __init__(self, url):
        self.messages = queue.Queue()
        self.transcript = []
        self.stderr = []
        self.counter = 0
        user_dir = ROOT / "test-results" / "backend-user"
        user_dir.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ, THONNY_USER_DIR=str(user_dir), PYTHONIOENCODING="utf-8")
        args = dict(
            port=url,
            clean=False,
            dtr=False,
            rts=False,
            submit_mode="raw_paste",
            write_block_size=255,
            write_block_delay=0.01,
            interrupt_on_connect=True,
            project_manager="-",
            local_rtc=True,
        )
        from thonny.plugins.esp import esp32_back

        launcher = Path(esp32_back.__file__)
        self.process = subprocess.Popen(
            [sys.executable, "-u", str(launcher), repr(args)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env=env,
            cwd=ROOT,
        )
        threading.Thread(target=self._read, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()

    def _read(self):
        try:
            while line := self.process.stdout.readline():
                if not line.startswith(MESSAGE_MARKER):
                    self.transcript.append({"raw": line.rstrip()})
                    continue
                count = int(line[1 : line.index(" ")])
                for _ in range(count - 1):
                    line += self.process.stdout.readline()
                msg = parse_message(line.rstrip("\n"))
                self.transcript.append(dict(msg.__dict__))
                self.messages.put(msg)
        except Exception as error:
            self.stderr.append(repr(error))
        finally:
            self.messages.put(None)

    def _read_stderr(self):
        for line in self.process.stderr:
            self.stderr.append(line.rstrip())

    def send(self, command):
        self.process.stdin.write(serialize_message(command) + "\n")
        self.process.stdin.flush()

    def wait(self, predicate, timeout=45):
        deadline = time.monotonic() + timeout
        seen = []
        while time.monotonic() < deadline:
            try:
                msg = self.messages.get(timeout=min(0.2, deadline - time.monotonic()))
            except queue.Empty:
                continue
            if msg is None:
                raise RuntimeError(
                    f"Backend exited ({self.process.poll()}): {self.stderr[-8:]}; {seen[-5:]}"
                )
            seen.append(msg)
            if predicate(msg, seen):
                return msg, seen
        raise TimeoutError(
            f"Backend response timed out; stderr={self.stderr[-5:]}; messages={seen[-5:]}"
        )

    def command(self, name, inline=False, **kwargs):
        self.counter += 1
        command_id = f"integration-{self.counter}"
        cls = InlineCommand if inline else ToplevelCommand
        self.send(cls(name, id=command_id, **kwargs))
        response, messages = self.wait(
            lambda msg, _: isinstance(msg, (InlineResponse, ToplevelResponse))
            and msg.get("command_id") == command_id
        )
        output = "".join(
            msg.get("data", "")
            for msg in messages
            if msg.get("event_type") == "ProgramOutput"
        )
        if response.get("error") or response.get("errors"):
            raise AssertionError(repr(response))
        if (
            "Traceback (most recent call last)" in output
            or "PROBLEM IN THONNY" in output
        ):
            raise AssertionError(output)
        return response, output

    def close(self):
        if self.process.poll() is None:
            try:
                self.command("prepare_disconnect", inline=True)
            finally:
                self.process.terminate()
                self.process.wait(timeout=10)
        for stream in [self.process.stdin, self.process.stdout, self.process.stderr]:
            stream.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="rfc2217://127.0.0.1:4000")
    options = parser.parse_args()
    results = []
    backends = []
    backend = None
    test_dir = "/thonny_rfc2217_test_" + uuid.uuid4().hex[:10]
    created = False

    def check(name, action):
        start = time.monotonic()
        try:
            detail = action()
            item = dict(test=name, status="PASS", detail=detail)
        except Exception as error:
            item = dict(test=name, status="FAIL", detail=str(error))
        item["seconds"] = round(time.monotonic() - start, 2)
        results.append(item)
        print(json.dumps(item, ensure_ascii=True), flush=True)
        return item["status"] == "PASS"

    def start():
        nonlocal backend
        backend = Backend(options.url)
        backends.append(backend)
        response, _ = backend.wait(
            lambda msg, _: isinstance(msg, ToplevelResponse), timeout=60
        )
        assert "ESP32" in response.get("welcome_text", ""), repr(response)
        return dict(welcome=response.get("welcome_text"), cwd=response.get("cwd"))

    def execute(source, expected):
        _, output = backend.command("execute_source", source=source)
        assert expected in output, repr(output)
        return output

    try:
        if not check("T03-T04 backend ESP32 and raw REPL initialization", start):
            return 1
        check(
            "T05 shell print unicode",
            lambda: execute("print('RFC2217 olá ✓')", "RFC2217 olá ✓"),
        )

        def run_led():
            backend.counter += 1
            command_id = f"integration-{backend.counter}"
            source = (
                "from machine import Pin\nfrom time import sleep_ms\n"
                "led = Pin(4, Pin.OUT)\nwhile True:\n"
                "    led.value(1)\n    print('LED LIGADO', led.value())\n    sleep_ms(500)\n"
                "    led.value(0)\n    print('LED DESLIGADO', led.value())\n    sleep_ms(500)\n"
            )
            backend.send(ToplevelCommand("Run", id=command_id, source=source, args=[]))
            try:
                _, messages = backend.wait(
                    lambda _, seen: all(
                        text in "".join(m.get("data", "") for m in seen)
                        for text in ["LED LIGADO 1", "LED DESLIGADO 0"]
                    )
                )
            finally:
                backend.send(ImmediateCommand("interrupt"))
            _, final = backend.wait(lambda msg, _: msg.get("command_id") == command_id)
            output = "".join(m.get("data", "") for m in messages + final)
            assert "KeyboardInterrupt" in output, repr(output)
            return output

        check("T06-T07 Run command (F5 backend), GPIO4 readback and interrupt", run_led)
        check(
            "prompt after interruption",
            lambda: execute("print('PROMPT_OK')", "PROMPT_OK"),
        )

        def soft_reset():
            execute("retention_test_variable = 123; print('SET_OK')", "SET_OK")
            _, output = backend.command(
                "Run",
                source="print('SOFT_RESET_OK', 'retention_test_variable' in globals())",
                args=[],
            )
            assert "SOFT_RESET_OK False" in output, repr(output)
            return output

        check("T09 soft reset via Run", soft_reset)

        def listing():
            response, _ = backend.command(
                "get_dirs_children_info",
                inline=True,
                paths=["/"],
                include_hidden=True,
                node_id="integration",
            )
            assert isinstance(response.get("data", {}).get("/"), dict), repr(response)
            return sorted(response["data"]["/"])

        check("T10 remote file listing through Thonny", listing)

        def make_dir():
            nonlocal created
            backend.command("mkdir", inline=True, path=test_dir)
            created = True
            return test_dir

        check("create test directory", make_dir)
        payload = bytes(range(256)) * 3 + b"\x00\xff\x03\x04\r\n"

        def transfer():
            path = test_dir + "/binary.bin"
            backend.command(
                "write_file",
                inline=True,
                path=path,
                content_bytes=payload,
                make_shebang_scripts_executable=False,
            )
            response, _ = backend.command("read_file", inline=True, path=path)
            assert response["content_bytes"] == payload
            return dict(bytes=len(payload), exact_match=True)

        if created:
            check("T11 binary upload and download through Thonny", transfer)

            def rename():
                original = test_dir + "/binary.bin"
                renamed = test_dir + "/renamed.bin"
                execute(
                    f"import os; os.rename({original!r}, {renamed!r}); print('RENAME_OK')",
                    "RENAME_OK",
                )
                response, _ = backend.command(
                    "read_file", inline=True, path=test_dir + "/renamed.bin"
                )
                assert response["content_bytes"] == payload
                return "renamed.bin verified"

            check("rename remote test file", rename)

            def main_boot():
                for filename in ["main.py", "boot.py"]:
                    path = test_dir + "/" + filename
                    content = f"print('TEST_{filename}_OK')\n".encode()
                    backend.command(
                        "write_file",
                        inline=True,
                        path=path,
                        content_bytes=content,
                        make_shebang_scripts_executable=False,
                    )
                    response, _ = backend.command("read_file", inline=True, path=path)
                    assert response["content_bytes"] == content
                _, output = backend.command(
                    "run",
                    source=f"exec(open({test_dir + '/main.py'!r}).read())",
                    args=[],
                )
                assert "TEST_main.py_OK" in output, repr(output)
                return output

            check(
                "T12 main.py execution and boot.py roundtrip in test directory",
                main_boot,
            )

            def cleanup():
                nonlocal created
                backend.command("delete", inline=True, paths=[test_dir])
                created = False
                return "unique test directory removed through Thonny"

            check("delete remote test files and directory", cleanup)

        check("backend disconnect", lambda: backend.close())
        if check("T14 reconnect new Thonny backend", start):
            check(
                "REPL after reconnect",
                lambda: execute("print('RECONNECTED_OK')", "RECONNECTED_OK"),
            )
    finally:
        if created and backend is not None and backend.process.poll() is None:
            check(
                "cleanup after failed test",
                lambda: backend.command("delete", inline=True, paths=[test_dir]),
            )
        for item in backends:
            try:
                item.close()
            except Exception as error:
                print("Close error:", error)
        out_dir = ROOT / "test-results"
        out_dir.mkdir(exist_ok=True)
        transcript = [dict(messages=b.transcript, stderr=b.stderr) for b in backends]
        report = dict(url=options.url, results=results, backends=transcript)
        (out_dir / "integration.json").write_text(
            json.dumps(report, ensure_ascii=True, indent=2, default=repr),
            encoding="utf-8",
        )
    return int(any(item["status"] != "PASS" for item in results))


if __name__ == "__main__":
    raise SystemExit(main())
