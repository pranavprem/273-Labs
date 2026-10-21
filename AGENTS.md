# Agent guide

This repository is Pranav Prem's Lab 1 from CMPE 273-01, Enterprise Distributed Systems, San José State University, Spring 2017 (Professor Sithu Aung). It is a single Python script that prints TCP sockets as CSV. Read [README.md](README.md) for the course context and how to run it. The original assignment text is [Lab1/README.md](Lab1/README.md); leave that file as the historical handout.

## Architecture

`Lab1/socket-mon.py` is the whole program.

- `format_address` turns a psutil endpoint into `ip@port`. Empty addresses and UNIX paths become `None`.
- `format_status` returns the lab's status token (`ESTABLISHED`, `CLOSING`, ...). psutil 7.2 uses a string. A later enum should contribute its `value`, not `ConnectionStatus.CONN_ESTABLISHED`.
- `collect_rows` drops connections with no pid or with a missing local or remote address, counts what remains per pid, and orders the groups.
- `render_csv` prints the quoted header and rows. `main` is the only place that calls `psutil.net_connections("tcp")` and writes stdout or stderr.

Do not include `LISTEN` rows. The handout defines a connection as one whose `laddr` and `raddr` both exist. An idle HTTP server is invisible until a client connection is still open.

Sort contract, which tests lock in:

- higher connection count first
- equal counts keep the first-seen pid (stable sort over insertion order; requires Python 3.7+, and this repo requires 3.11+)
- within one pid, keep the order of the input sequence

## Commands

Python 3.12 is the version in `.python-version` and CI. 3.11 or newer is fine locally.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
ruff check .
ruff format .
pytest
python Lab1/socket-mon.py
```

Runtime-only install is `python -m pip install -r requirements.txt`. CI runs the lint, format check, and `pytest` steps in `.github/workflows/ci.yml`.

## Conventions

- Ruff is the formatter and linter. Line length is 88. Settings are in `pyproject.toml`. Do not add a second linter.
- Pin new dependencies with `==` in `requirements.txt` or `requirements-dev.txt`.
- Keep the script at `Lab1/socket-mon.py`. The assignment requires that filename. Tests load it with `importlib` because of the hyphen; do not rename it to make the import prettier.
- Match the existing CSV exactly: four double-quoted fields, no spaces after commas, addresses as `ip@port`. The header is printed even when there are no rows.
- No license file. That choice belongs to the owner.
- Do not commit virtualenvs, `__pycache__`, tool caches, or build output. `.gitignore` already covers them.

## Gotchas

- The 2017 script was Python 2 and formatted addresses with `str(addr).split(",")`. On current psutil, `str(addr(ip='10.0.0.1', port=80))` is `addr(ip='10.0.0.1', port=80)`, so that parser emits the wrong column. Keep using the sequence fields (`addr[0]`, `addr[1]`). There is a regression test named `test_namedtuple_address_is_not_stringified`.
- `pid is None` means "not readable," not "kernel process." Skipping those rows is intentional. On Linux this hides other users' sockets. On macOS, `net_connections` raises `psutil.AccessDenied` unless run as root; `main` catches that and exits 1 with a stderr message.
- A finished request to `python -m http.server` does not leave a visible server row. That server speaks HTTP/1.0 and closes the socket after the response; `TIME_WAIT` then usually has `pid=None`. The README demo sends only the request headers and pauses, which keeps both ends `ESTABLISHED`. There is a test for that shape of connection.
- `Lab1/index.html` is the single line `HELLO WORLD`. The handout said `Hello World`. Leave the file alone.
- There are no credentials in this repo. Do not add any. If a future change needs configuration, use environment variables and keep the values out of git.
