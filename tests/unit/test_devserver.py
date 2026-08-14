from __future__ import annotations

import socket
from pathlib import Path

import pytest

from camdesign.devserver import DevelopmentServerUnavailable, development_server_guard


def test_guard_rejects_an_occupied_port(tmp_path: Path):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]

        with (
            pytest.raises(DevelopmentServerUnavailable, match=f"Port {port} is already in use"),
            development_server_guard(tmp_path, port=port),
        ):
            pass


def test_guard_allows_only_one_instance_and_releases_its_lock(tmp_path: Path):
    with (
        development_server_guard(tmp_path, port=0),
        pytest.raises(DevelopmentServerUnavailable, match="already running"),
        development_server_guard(tmp_path, port=0),
    ):
        pass

    with development_server_guard(tmp_path, port=0):
        pass
