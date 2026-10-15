#!/usr/bin/env python3
"""List TCP sockets grouped by process.

Lab 1 for CMPE 273-01 (Enterprise Distributed Systems) at San Jose State
University, Spring 2017, under Professor Sithu Aung.

The script prints one CSV row for each TCP connection that has a process id
and both a local and a remote address. Rows are grouped by pid. Processes
with more connections come first. Run it with ``python Lab1/socket-mon.py``.
"""

from __future__ import annotations

import sys
from collections.abc import Iterable

import psutil

HEADER = '"pid","laddr","raddr","status"'
Row = tuple[int, str, str, str]


def format_address(addr):
    """Return ``ip@port`` for a connected address, or None when there is none.

    psutil 5.3 and later represent an IPv4 or IPv6 endpoint as an
    ``addr(ip, port)`` namedtuple. Earlier releases used a plain
    ``(ip, port)`` tuple. A listening socket has an empty remote address,
    ``()``, and a UNIX socket path is a string. Stringifying the namedtuple
    does not produce the ``ip@port`` column the lab asks for.
    """
    if not addr or isinstance(addr, str):
        return None
    try:
        ip, port = addr[0], addr[1]
    except (IndexError, TypeError):
        return None
    return f"{ip}@{port}"


def format_status(status):
    """Return the status token printed in the lab sample, such as ESTABLISHED.

    psutil 7.2 returns a ``str``. psutil 8 documents a ``ConnectionStatus``
    enum whose value is that same token.
    """
    value = getattr(status, "value", status)
    return str(value)


def collect_rows(connections: Iterable) -> list[Row]:
    """Keep connected TCP sockets, group them by pid, and sort by count.

    Connections with no pid, or with a missing local or remote address, are
    dropped. That excludes LISTEN sockets. Ordering matches the original
    lab script: higher connection counts first, ties keep the order in which
    each pid was first seen, and rows for one pid keep psutil's order.
    """
    required: list[Row] = []
    counts: dict[int, int] = {}
    for connection in connections:
        local = format_address(connection.laddr)
        remote = format_address(connection.raddr)
        pid = connection.pid
        if pid is None or local is None or remote is None:
            continue
        required.append((pid, local, remote, format_status(connection.status)))
        counts[pid] = counts.get(pid, 0) + 1

    # ``sorted`` is stable, and ``counts`` remembers first-seen pid order.
    ordered = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    rows: list[Row] = []
    for pid, _count in ordered:
        rows.extend(row for row in required if row[0] == pid)
    return rows


def render_csv(rows: Iterable[Row]) -> str:
    """Render rows in the lab's quoted CSV layout, header included."""
    lines = [HEADER]
    for pid, local, remote, status in rows:
        lines.append(f'"{pid}","{local}","{remote}","{status}"')
    return "\n".join(lines)


def main() -> int:
    try:
        connections = psutil.net_connections("tcp")
    except psutil.AccessDenied:
        print(
            "socket-mon.py: permission denied reading TCP sockets. "
            "On macOS, re-run with sudo.",
            file=sys.stderr,
        )
        return 1
    print(render_csv(collect_rows(connections)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
