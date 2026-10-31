import queue
import socket
import threading
from typing import Any, cast
from unittest.mock import Mock

import pytest
import serial
from serial.rfc2217 import PortManager

from minny.connection import MicroPythonConnection, ReadingTimeoutError
from minny.serial_connection import SerialConnection, validate_rfc2217_url


class Rfc2217Peer:
    """Exercise PySerial's real RFC 2217 negotiation without serial hardware."""

    def __init__(self, negotiate=True):
        self.listener = socket.socket()
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen()
        self.listener.settimeout(0.1)
        self.url = "rfc2217://127.0.0.1:%s" % self.listener.getsockname()[1]
        self.device = serial.serial_for_url("loop://", timeout=0.1)
        self.negotiate = negotiate
        self.stopped = threading.Event()
        self.write_lock = threading.Lock()
        self.received = queue.Queue()
        self.client: socket.socket | None = None
        self.manager: Any = None
        self.errors = []
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    def write(self, data):
        with self.write_lock:
            assert self.client is not None
            self.client.sendall(data)

    def send(self, data):
        self.write(b"".join(self.manager.escape(data)))

    def disconnect(self):
        if self.client is not None:
            try:
                self.client.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.client.close()

    def serve(self):
        while not self.stopped.is_set():
            try:
                client, _ = self.listener.accept()
            except TimeoutError:
                continue
            except OSError:
                return
            self.client = client
            client.settimeout(0.1)
            try:
                # types-pyserial incorrectly types the protocol adapter's two
                # duck-typed arguments as concrete serial classes.
                self.manager = (
                    PortManager(cast(Any, self.device), cast(Any, self)) if self.negotiate else None
                )
                while not self.stopped.is_set():
                    try:
                        incoming = client.recv(1024)
                    except TimeoutError:
                        continue
                    if not incoming:
                        break
                    if self.manager is not None:
                        data = b"".join(self.manager.filter(incoming))
                        if data:
                            self.received.put(data)
                            self.send(data)
            except OSError:
                # Closing a socket in disconnect/close unblocks recv or sendall.
                pass
            except Exception as error:
                self.errors.append(error)
            finally:
                client.close()

    def close(self):
        self.stopped.set()
        self.disconnect()
        self.listener.close()
        self.thread.join(timeout=3)
        self.device.close()
        assert not self.thread.is_alive()
        assert not self.errors


@pytest.fixture
def peer():
    peer = Rfc2217Peer()
    try:
        yield peer
    finally:
        peer.close()


@pytest.mark.parametrize(
    "url",
    [
        "rfc2217://127.0.0.1:4000",
        "rfc2217://localhost:4000",
        "rfc2217://serial.example:65535?ign_set_control&timeout=1",
        "rfc2217://[::1]:4000",
    ],
)
def test_validate_rfc2217_url(url):
    validate_rfc2217_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "socket://localhost:4000",
        "rfc2217:localhost:4000",
        "rfc2217://:4000",
        "rfc2217://local host:4000",
        "rfc2217://localhost",
        "rfc2217://localhost:0",
        "rfc2217://localhost:-1",
        "rfc2217://localhost:65536",
        "rfc2217://localhost:not-a-port",
        "rfc2217://user:password@localhost:4000",
        "rfc2217://localhost:4000/path",
        "rfc2217://localhost:4000#fragment",
        "rfc2217://[::1:4000",
    ],
)
def test_invalid_rfc2217_url(url):
    with pytest.raises(ValueError, match="Invalid RFC 2217 address"):
        validate_rfc2217_url(url)


def test_rfc2217_binary_and_multiple_writes(peer):
    connection = SerialConnection(peer.url, dtr=False, rts=False)
    try:
        assert peer.manager._client_is_rfc2217
        assert peer.device.baudrate == 115200
        assert peer.device.dtr is False
        assert peer.device.rts is False
        connection.set_text_mode(False)
        for data in [bytes(range(256)), b"\x03\x01\x04\x02", b"last\x00\xff"]:
            assert connection.write(data) == len(data)
            assert connection.read(len(data), timeout=3) == data
        assert connection.outgoing_is_empty()
    finally:
        reader = connection._reading_thread
        connection.close()
    assert reader is not None
    assert not reader.is_alive()
    connection.close()


def test_idle_read_timeout_is_not_disconnection(peer):
    connection = SerialConnection(peer.url)
    try:
        assert connection.soft_read(1, timeout=0.5) == b""
        connection.check_for_error()
        connection.write(b"after idle\n")
        assert connection.read_until(b"\n", timeout=3) == b"after idle\n"
    finally:
        connection.close()


@pytest.mark.parametrize("text_mode", [False, True])
@pytest.mark.parametrize("prefix", [b"", b"prefix "])
def test_split_utf8_survives_idle_timeout(peer, text_mode, prefix):
    connection = SerialConnection(peer.url)
    connection.set_text_mode(text_mode)
    try:
        peer.send(prefix + b"\xc3")
        if prefix:
            assert connection.read(len(prefix), timeout=3) == prefix
        if not text_mode:
            # Binary mode publishes every byte without waiting for UTF-8.
            assert connection.read(1, timeout=3) == b"\xc3"
        # This exceeds the transport's finite read timeout. In text mode the
        # incomplete code point must stay in the reader's pending bytes.
        assert connection.soft_read(1, timeout=0.5) == b""
        connection.check_for_error()
        peer.send(b"\xa1")
        expected = b"\xc3\xa1" if text_mode else b"\xa1"
        assert connection.read(len(expected), timeout=3) == expected
    finally:
        connection.close()


@pytest.mark.parametrize("data", [b"\xff", b"\xc3x"])
def test_invalid_complete_utf8_is_preserved(peer, data):
    connection = SerialConnection(peer.url)
    try:
        peer.send(data)
        assert connection.read(len(data), timeout=3) == data
    finally:
        connection.close()


def test_remote_close_wakes_pending_read_and_allows_reconnect(peer):
    connection = SerialConnection(peer.url)
    finished = threading.Event()
    errors = []

    def read():
        try:
            connection.read_until(b"never", timeout=30)
        except ConnectionError as error:
            errors.append(error)
        finally:
            finished.set()

    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    peer.disconnect()
    try:
        assert finished.wait(3), "A pending read must observe remote disconnection"
        assert len(errors) == 1
        assert peer.url in str(errors[0])
    finally:
        connection.close()
        reader.join(timeout=3)

    connection = SerialConnection(peer.url)
    try:
        connection.write(b"reconnected\n")
        assert connection.read_until(b"\n", timeout=3) == b"reconnected\n"
    finally:
        connection.close()


def test_rfc2217_negotiation_timeout():
    peer = Rfc2217Peer(negotiate=False)
    try:
        with pytest.raises(ConnectionRefusedError, match="support RFC2217"):
            SerialConnection(peer.url + "?timeout=0.2")
    finally:
        peer.close()


def test_unavailable_server():
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    url = "rfc2217://127.0.0.1:%s" % listener.getsockname()[1]
    listener.close()
    with pytest.raises(ConnectionRefusedError, match=url):
        SerialConnection(url)


def test_unavailable_host(monkeypatch):
    def fail(*args, **kwargs):
        raise socket.gaierror("hostname unavailable")

    monkeypatch.setattr(socket, "create_connection", fail)
    with pytest.raises(ConnectionRefusedError, match="hostname unavailable"):
        SerialConnection("rfc2217://unavailable.invalid:4000")


def test_local_serial_settings_and_open_order_are_preserved(monkeypatch):
    local_serial = Mock()
    local_serial.out_waiting = 7
    serial_factory = Mock(return_value=local_serial)
    monkeypatch.setattr(serial, "Serial", serial_factory)
    monkeypatch.setattr(serial, "serial_for_url", Mock(side_effect=AssertionError("URL used")))

    def check_open():
        assert local_serial.port == "COM9"
        assert local_serial.dtr is False
        assert local_serial.rts is True

    local_serial.open.side_effect = check_open
    connection = SerialConnection("COM9", baudrate=9600, dtr=False, rts=True, skip_reader=True)
    serial_factory.assert_called_once_with(
        port=None, baudrate=9600, timeout=None, write_timeout=2, exclusive=True
    )
    assert connection.outgoing_is_empty() is False
    local_serial.out_waiting = 0
    assert connection.outgoing_is_empty() is True
    connection.close()
    local_serial.cancel_read.assert_called_once()
    local_serial.close.assert_called_once()


def test_rfc2217_write_failure_identifies_endpoint(monkeypatch):
    remote_serial = Mock()
    remote_serial.write.side_effect = serial.SerialException("socket closed")
    monkeypatch.setattr(serial, "serial_for_url", Mock(return_value=remote_serial))
    connection = SerialConnection("rfc2217://localhost:4000", skip_reader=True)
    try:
        with pytest.raises(ConnectionError, match="localhost:4000.*socket closed"):
            connection.write(b"data")
    finally:
        connection.close()


def test_local_serial_read_finishes_before_handles_close(monkeypatch):
    events = []
    started = threading.Event()
    release = threading.Event()
    local_serial = Mock()

    def read(size):
        started.set()
        assert release.wait(3)
        events.append("read returned")
        return b""

    local_serial.read.side_effect = read
    local_serial.cancel_read.side_effect = lambda: events.append("cancel")
    local_serial.close.side_effect = lambda: events.append("close")
    monkeypatch.setattr(serial, "Serial", Mock(return_value=local_serial))
    connection = SerialConnection("COM9")
    assert started.wait(3)
    reader = connection._reading_thread
    assert reader is not None
    original_join = reader.join

    def join(timeout=None):
        events.append("join")
        release.set()
        original_join(timeout)

    monkeypatch.setattr(reader, "join", join)
    connection.close()
    assert events == ["cancel", "join", "read returned", "close"]
    assert not reader.is_alive()


def test_rfc2217_reports_in_progress_write(monkeypatch):
    started = threading.Event()
    release = threading.Event()
    remote_serial = Mock()

    def write(data):
        started.set()
        assert release.wait(3)
        return len(data)

    remote_serial.write.side_effect = write
    monkeypatch.setattr(serial, "serial_for_url", Mock(return_value=remote_serial))
    connection = SerialConnection("rfc2217://localhost:4000", skip_reader=True)
    writer = threading.Thread(target=connection.write, args=(b"data",), daemon=True)
    writer.start()
    try:
        assert started.wait(3)
        assert connection.outgoing_is_empty() is False
        release.set()
        writer.join(timeout=3)
        assert not writer.is_alive()
        assert connection.outgoing_is_empty() is True
    finally:
        release.set()
        writer.join(timeout=3)
        connection.close()


@pytest.mark.parametrize("read_until", [False, True])
def test_connection_observes_error_while_waiting(read_until):
    connection = MicroPythonConnection()
    finished = threading.Event()
    errors = []

    def read():
        try:
            if read_until:
                connection.read_until(b"never", timeout=30)
            else:
                connection.read(1, timeout=30)
        except ConnectionError as error:
            errors.append(error)
        finally:
            finished.set()

    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    connection._error = "disconnected"
    assert finished.wait(3)
    reader.join(timeout=3)
    assert str(errors[0]) == "disconnected"


def test_partial_reads_preserve_bytes_after_timeout():
    connection = MicroPythonConnection()
    connection._make_output_available(b"part")
    with pytest.raises(ReadingTimeoutError) as error:
        connection.read(5, timeout=0.02)
    assert error.value.read_bytes == b"part"
    connection._make_output_available(b"2")
    assert connection.read(5, timeout=1) == b"part2"
