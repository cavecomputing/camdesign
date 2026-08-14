from __future__ import annotations

import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, Protocol

from flask import Flask

from camdesign.config import Config


class DevelopmentServerUnavailable(RuntimeError):
    pass


class AppFactory(Protocol):
    def __call__(self) -> Flask: ...


def _lock(handle: BinaryIO) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        return

    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock(handle: BinaryIO) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return

    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _claim_lock(handle: BinaryIO) -> None:
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b" ")
        handle.flush()

    try:
        _lock(handle)
    except OSError as error:
        raise DevelopmentServerUnavailable(
            "CamDesign is already running. Close that instance and try again."
        ) from error

    handle.seek(0)
    handle.write(str(os.getpid()).encode("ascii").ljust(32))
    handle.truncate()
    handle.flush()


def _require_available_port(host: str, port: int) -> None:
    probe_host = "" if host == "0.0.0.0" else host
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind((probe_host, port))
    except OSError as error:
        raise DevelopmentServerUnavailable(
            f"Port {port} is already in use. Close the process using it and try again."
        ) from error


@contextmanager
def development_server_guard(
    data_dir: Path,
    *,
    host: str = "127.0.0.1",
    port: int = 5000,
) -> Iterator[None]:
    data_dir.mkdir(parents=True, exist_ok=True)
    lock_path = data_dir / ".devserver.lock"
    with lock_path.open("a+b") as handle:
        _claim_lock(handle)
        try:
            _require_available_port(host, port)
            yield
        finally:
            _unlock(handle)


def _open_browser_when_ready(url: str, timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:  # noqa: S310
                if response.status == 200:
                    webbrowser.open(url)
                    return
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.25)


def run_development_server(app_factory: AppFactory) -> int:
    host = os.environ.get("CAMDESIGN_HOST", "127.0.0.1")
    port = 5000
    browser_url = f"http://127.0.0.1:{port}"

    try:
        with development_server_guard(Config.DATA_DIR, host=host, port=port):
            app = app_factory()
            if os.environ.get("CAMDESIGN_OPEN_BROWSER", "1") != "0":
                threading.Thread(
                    target=_open_browser_when_ready,
                    args=(browser_url,),
                    daemon=True,
                    name="camdesign-browser-opener",
                ).start()
            app.run(host=host, port=port, debug=False, use_reloader=False)
    except DevelopmentServerUnavailable as error:
        print(f"CamDesign did not start: {error}", file=sys.stderr)
        return 1
    return 0
