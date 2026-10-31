import pathlib
import sys
import threading
import time
from logging import getLogger
from textwrap import dedent
from typing import Any
from urllib.parse import urlsplit

from .connection import MicroPythonConnection

OUTPUT_ENQ = b"\x05"
OUTPUT_ACK = b"\x06"
NORMAL_PROMPT = b">>> "
FIRST_RAW_PROMPT = b"raw REPL; CTRL-B to exit\r\n>"


logger = getLogger(__name__)


def validate_rfc2217_url(url: str) -> None:
    """Validate the endpoint; PySerial validates its optional query parameters."""
    try:
        parts = urlsplit(url)
        if parts.scheme != "rfc2217" or not url.lower().startswith("rfc2217://"):
            raise ValueError("Use an RFC 2217 URL such as rfc2217://hostname:4000")
        if not parts.hostname or any(ch.isspace() for ch in parts.hostname):
            raise ValueError("An RFC 2217 server hostname is required")
        if parts.port is None or not 1 <= parts.port <= 65535:
            raise ValueError("The RFC 2217 TCP port must be between 1 and 65535")
        if parts.username is not None or parts.password is not None:
            raise ValueError("RFC 2217 URLs do not support a username or password")
        if parts.path or parts.fragment:
            raise ValueError("RFC 2217 URLs must not contain a path or fragment")
    except ValueError as error:
        raise ValueError("Invalid RFC 2217 address: " + str(error)) from error


class SerialConnection(MicroPythonConnection):
    def __init__(self, port, baudrate=115200, dtr=None, rts=None, skip_reader=False):
        import serial
        from serial.serialutil import SerialException

        super().__init__()
        self._port = port
        self._is_rfc2217 = port.lower().startswith("rfc2217://")
        self._serial: Any = None
        self._write_lock = threading.Lock()

        try:
            # Pyrefly can't see the attributes of Serial subtypes
            if self._is_rfc2217:
                validate_rfc2217_url(port)
                # RFC 2217 has no cancel_read and does not support write_timeout.
                # Its socket has a finite timeout; use a finite read timeout too,
                # so the reader can stop while the remote serial port is idle.
                self._serial = serial.serial_for_url(
                    port, baudrate=baudrate, timeout=0.2, do_not_open=True
                )
            else:
                self._serial = serial.Serial(
                    port=None, baudrate=baudrate, timeout=None, write_timeout=2, exclusive=True
                )
            logger.info(
                "Before opening serial port, DTR=%r, RTS=%r", self._serial.dtr, self._serial.rts
            )
            # Tweaking dtr and rts was proposed by
            # https://github.com/thonny/thonny/pull/1187
            # but in some cases it messes up communication.
            # At the same time, in some cases it is required
            # https://github.com/thonny/thonny/issues/1462
            # More information:
            #   https://github.com/npat-efault/picocom/blob/master/lowerrts.md
            #   https://github.com/micropython/micropython/pull/11076
            if dtr is not None:
                logger.debug("Setting DTR to %s", dtr)
                self._serial.dtr = dtr
            if rts is not None:
                logger.debug("Setting RTS to %s", rts)
                self._serial.rts = rts

            self._serial.port = port
            logger.debug("Opening serial port %s", port)
            self._serial.open()
        except (SerialException, ValueError) as error:
            if self._serial is not None:
                self._serial.close()
            err_str = str(error)
            if "FileNotFoundError" in err_str:
                err_str = "port not found"
            message = "Unable to connect to " + port + ": " + err_str

            # TODO: check if these error codes also apply to Linux and Mac
            if getattr(error, "errno", None) == 13 and sys.platform == "linux":
                try:
                    group = pathlib.Path(self._serial.port).group()
                except Exception:
                    logger.warning("Could not query group for '%s'", self._serial.port)
                    group = "dialoutfb"

                # TODO: check if user already has this group
                message += "\n\n" + dedent(
                    f"""\
                Try adding yourself to the '{group}' group:
                > sudo usermod -a -G {group} <username>
                (NB! You may need to reboot your system after this!)"""
                )

            elif "PermissionError" in message or "Could not exclusively lock" in message:
                message += "\n\n" + dedent(
                    """\
                If you have serial connection to the device from another program, then disconnect it there first."""
                )

            elif getattr(error, "errno", None) == 16:
                message += "\n\n" + "Try restarting the device."

            raise ConnectionRefusedError(message) from error

        self._reading_thread: threading.Thread | None
        if skip_reader:
            self._reading_thread = None
        else:
            self._reading_thread = threading.Thread(target=self._listen_serial, daemon=True)
            self._reading_thread.start()

    def write(self, data: bytes) -> int:
        from serial.serialutil import SerialException

        self.check_for_error()
        with self._write_lock:
            try:
                size = self._serial.write(data)
            except SerialException as error:
                if not self._is_rfc2217:
                    raise
                self._error = f"Connection to {self._port} failed: {error}"
                raise ConnectionError(self._error) from error
        # print(data.decode(), end="")
        assert size == len(data)
        return len(data)

    def stop_reader(self) -> None:
        super().stop_reader()
        cancel_read = getattr(self._serial, "cancel_read", None)
        if cancel_read is not None:
            cancel_read()

    def _listen_serial(self):
        "NB! works in background thread"
        try:
            data = b""
            while not self._reader_stopped:
                new_data = self._serial.read(1)  # To avoid busy loop
                if self._reader_stopped:
                    break
                if not new_data and self._is_rfc2217:
                    # An idle finite read is not EOF. PySerial raises an error
                    # on the next read if its network reader has terminated.
                    continue
                data += new_data
                if not data:
                    self._error = "EOF"
                    # print("LISTEN EOFFFFFFFFFF")
                    break
                data += self._serial.read_all()
                # logger.debug("GOT %r", data)

                if data.endswith(OUTPUT_ENQ) and self.text_mode:
                    # Flow control.
                    logger.debug("Read ENQ, responding with ACK")
                    self.write(OUTPUT_ACK)
                    self._serial.flush()
                    data = data[:-1]
                    continue

                # don't publish incomplete utf-8 data
                try:
                    if self.text_mode:
                        data.decode("utf-8")  # testing if data decodes
                    to_be_published = data
                    data = b""
                except UnicodeDecodeError as e:
                    if e.start == 0 and e.reason != "unexpected end of data":
                        # Invalid start byte, ie. we have missed first byte(s) of the codepoint.
                        # No use of waiting, output everything
                        to_be_published = data
                        data = b""
                    else:
                        # A valid leading byte can arrive on its own, especially
                        # over TCP. Retain it across idle read timeouts as well.
                        to_be_published = data[: e.start]
                        data = data[e.start :]

                if to_be_published:
                    self._make_output_available(to_be_published)

        except Exception as e:
            if not self._reader_stopped:
                self._error = f"Connection to {self._port} failed: {e}"

    def incoming_is_empty(self):
        return self._serial.in_waiting == 0 and super().incoming_is_empty()

    def outgoing_is_empty(self):
        if self._is_rfc2217:
            # PySerial's synchronous write uses sendall; Minny has no pending
            # write buffer after it returns. RFC 2217 provides no remote drain
            # acknowledgement, so this does not promise device-side consumption.
            self.check_for_error()
            return not self._write_lock.locked()
        return self._serial.out_waiting == 0

    def close(self):
        if self._serial is not None:
            try:
                self.stop_reader()
                self._error = self._error or f"Connection to {self._port} closed"
                # In particular on Windows, cancellation must complete before
                # closing the handles used by an overlapped local serial read.
                if not self._is_rfc2217 and self._reading_thread:
                    self._reading_thread.join(timeout=2)
            finally:
                try:
                    self._serial.close()
                except Exception:
                    logger.exception("Couldn't close serial")
                finally:
                    if self._is_rfc2217 and self._reading_thread:
                        self._reading_thread.join(timeout=2)
                    self._serial = None


class DifficultSerialConnection(SerialConnection):
    """For hardening the communication protocol"""

    def _make_output_available(self, data, block=True):
        # output prompts in parts
        if FIRST_RAW_PROMPT in data or NORMAL_PROMPT in data:
            if FIRST_RAW_PROMPT in data:
                start = data.find(FIRST_RAW_PROMPT)
                end = start + len(FIRST_RAW_PROMPT)
            else:
                start = data.find(NORMAL_PROMPT)
                end = start + len(NORMAL_PROMPT)

            super()._make_output_available(data[: start + 1], block=block)
            time.sleep(0.1)
            super()._make_output_available(data[start + 1 : end - 1], block=block)
            time.sleep(0.1)
            super()._make_output_available(data[end - 1 :], block=block)
        else:
            super()._make_output_available(data, block=block)
