"""Tests for the Lab 1 TCP socket monitor."""

from __future__ import annotations

import enum
import importlib.util
import os
import socket
import subprocess
import sys
import time
from collections import namedtuple
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "Lab1" / "socket-mon.py"

Connection = namedtuple("Connection", "pid laddr raddr status")
Address = namedtuple("addr", "ip port")

LAB_SAMPLE = "\n".join(
    [
        '"pid","laddr","raddr","status"',
        '"1234","10.0.0.1@48776","93.186.135.91@80","ESTABLISHED"',
        '"1234","10.0.0.1@48777","93.186.135.91@80","ESTABLISHED"',
        '"5678","10.0.0.1@48779","193.286.35.91@8000","CLOSING"',
    ]
)


@pytest.fixture(scope="module")
def socket_mon():
    spec = importlib.util.spec_from_file_location("socket_mon", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_lab_sample_groups_by_pid_and_sorts_by_count(socket_mon):
    # The busier pid is listed second on input and must still be printed first.
    connections = [
        Connection(
            5678,
            Address("10.0.0.1", 48779),
            Address("193.286.35.91", 8000),
            "CLOSING",
        ),
        Connection(
            1234,
            Address("10.0.0.1", 48776),
            Address("93.186.135.91", 80),
            "ESTABLISHED",
        ),
        Connection(
            1234,
            Address("10.0.0.1", 48777),
            Address("93.186.135.91", 80),
            "ESTABLISHED",
        ),
    ]
    assert socket_mon.render_csv(socket_mon.collect_rows(connections)) == LAB_SAMPLE


def test_namedtuple_address_is_not_stringified(socket_mon):
    """psutil's addr repr is not the lab column, which the 2017 parser assumed."""
    addr = Address("10.0.0.1", 48776)
    assert str(addr) == "addr(ip='10.0.0.1', port=48776)"
    assert socket_mon.format_address(addr) == "10.0.0.1@48776"


def test_plain_tuple_and_ipv6_addresses(socket_mon):
    assert socket_mon.format_address(("10.0.0.1", 80)) == "10.0.0.1@80"
    assert socket_mon.format_address(("::1", 8000)) == "::1@8000"
    assert socket_mon.format_address(()) is None
    assert socket_mon.format_address("") is None
    assert socket_mon.format_address("/tmp/socket") is None


def test_listen_sockets_and_unknown_pids_are_omitted(socket_mon):
    connections = [
        Connection(42, Address("127.0.0.1", 8000), (), "LISTEN"),
        Connection(None, Address("10.0.0.1", 1), Address("10.0.0.2", 2), "ESTABLISHED"),
        Connection(
            7, Address("127.0.0.1", 5000), Address("127.0.0.1", 9), "ESTABLISHED"
        ),
    ]
    assert socket_mon.collect_rows(connections) == [
        (7, "127.0.0.1@5000", "127.0.0.1@9", "ESTABLISHED")
    ]


def test_equal_counts_keep_first_seen_pid_order(socket_mon):
    connections = [
        Connection(2, ("10.0.0.1", 2), ("10.0.0.2", 80), "ESTABLISHED"),
        Connection(1, ("10.0.0.1", 1), ("10.0.0.3", 80), "ESTABLISHED"),
        Connection(2, ("10.0.0.1", 3), ("10.0.0.4", 443), "TIME_WAIT"),
        Connection(1, ("10.0.0.1", 4), ("10.0.0.5", 443), "CLOSE_WAIT"),
    ]
    rows = socket_mon.collect_rows(connections)
    assert [row[0] for row in rows] == [2, 2, 1, 1]
    assert [row[1] for row in rows if row[0] == 2] == ["10.0.0.1@2", "10.0.0.1@3"]


def test_status_enum_uses_its_value(socket_mon):
    class ConnectionStatus(enum.Enum):
        CONN_ESTABLISHED = "ESTABLISHED"

    connections = [
        Connection(
            9,
            Address("10.0.0.1", 1),
            Address("10.0.0.2", 80),
            ConnectionStatus.CONN_ESTABLISHED,
        )
    ]
    rows = socket_mon.collect_rows(connections)
    assert rows[0][3] == "ESTABLISHED"
    assert "ConnectionStatus" not in socket_mon.render_csv(rows)


def test_empty_input_still_prints_the_header(socket_mon):
    assert socket_mon.render_csv(socket_mon.collect_rows([])) == (
        '"pid","laddr","raddr","status"'
    )


def test_access_denied_is_reported_on_stderr(socket_mon, monkeypatch, capsys):
    def denied(_kind):
        raise socket_mon.psutil.AccessDenied(pid=0, name="net_connections")

    monkeypatch.setattr(socket_mon.psutil, "net_connections", denied)
    assert socket_mon.main() == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "permission denied" in captured.err.lower()


def test_script_reports_a_live_tcp_connection():
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    port = listener.getsockname()[1]
    client = socket.create_connection(("127.0.0.1", port))
    accepted, _peer = listener.accept()
    try:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT)],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    finally:
        client.close()
        accepted.close()
        listener.close()

    assert completed.returncode == 0, completed.stderr
    lines = completed.stdout.splitlines()
    assert lines[0] == '"pid","laddr","raddr","status"'
    for line in lines[1:]:
        pid, local, remote, status = _parse_csv_line(line)
        assert pid.isdigit()
        assert "@" in local and "@" in remote
        assert status.isupper()

    own_pid = f'"{os.getpid()}"'
    endpoint = f"@{port}"
    matching = [
        line
        for line in lines
        if line.startswith(own_pid + ",")
        and endpoint in line
        and '"ESTABLISHED"' in line
    ]
    assert matching, completed.stdout


def test_unfinished_http_request_lists_the_server():
    """The README demo: http.server stays visible until the request finishes."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]

    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "http.server",
            str(port),
            "--bind",
            "127.0.0.1",
            "--directory",
            str(ROOT / "Lab1"),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    client = None
    try:
        deadline = time.monotonic() + 5
        while True:
            try:
                client = socket.create_connection(("127.0.0.1", port), timeout=0.2)
                break
            except OSError:
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.05)
        client.sendall(b"GET / HTTP/1.1\r\nHost: 127.0.0.1\r\n")
        time.sleep(0.2)
        completed = subprocess.run(
            [sys.executable, str(SCRIPT)],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    finally:
        if client is not None:
            client.close()
        server.kill()
        server.wait(timeout=5)

    assert completed.returncode == 0, completed.stderr
    server_pid = f'"{server.pid}"'
    endpoint = f"@{port}"
    matching = [
        line
        for line in completed.stdout.splitlines()
        if line.startswith(server_pid + ",")
        and endpoint in line
        and '"ESTABLISHED"' in line
    ]
    assert matching, completed.stdout


def _parse_csv_line(line: str) -> tuple[str, str, str, str]:
    assert line.startswith('"') and line.endswith('"')
    parts = line[1:-1].split('","')
    assert len(parts) == 4
    return parts[0], parts[1], parts[2], parts[3]
