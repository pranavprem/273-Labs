# 273-Labs

TCP socket monitor written for **CMPE 273-01, Enterprise Distributed Systems**, at San José State University in Spring 2017. The instructor was Professor Sithu Aung. Pranav Prem committed this Lab 1 solution in February 2017. The semester's [course repository](https://github.com/sithu/cmpe273-spring17) also had assignments, exams, and later labs; this repo only ever contained Lab 1.

The assignment: use [psutil](https://github.com/giampaolo/psutil) to see how many TCP sockets a web application has open, keep the connections that have both a local and a remote address, group them by process id, and print CSV sorted so the process with the most connections comes first. The original handout is preserved, typos included, in [Lab1/README.md](Lab1/README.md).

There is no graphical interface. The sample page in `Lab1/index.html` is only there so a local HTTP server has something to serve while you watch its sockets.

## How it works

`Lab1/socket-mon.py` asks psutil for every TCP connection on the machine. A row is kept only when all three of these are present:

- a process id
- a local address
- a remote address

A listening socket fails that test, because its remote address is empty. So an idle `http.server` does not show up until some client is actually connected to it. Connections whose process cannot be read are dropped too; psutil reports those with `pid=None` rather than guessing.

The remaining rows are grouped by pid. Groups are ordered by size, largest first. A tie keeps the order in which each pid was first seen, and the rows inside one pid stay in the order psutil returned them. That is the same ordering the 2017 script used.

Each address is printed as `ip@port`. psutil has represented endpoints as `addr(ip, port)` namedtuples since version 5.3 (July 2017). The original script turned that object into a string and split on commas, which produced columns like `addrip=10.0.0.1@port=80` on any psutil new enough to use the namedtuple. The script now reads the ip and port fields, and still accepts the older plain `(ip, port)` tuple.

Output matches the handout:

```text
"pid","laddr","raddr","status"
"1234","10.0.0.1@48776","93.186.135.91@80","ESTABLISHED"
"1234","10.0.0.1@48777","93.186.135.91@80","ESTABLISHED"
"5678","10.0.0.1@48779","193.286.35.91@8000","CLOSING"
```

Live rows depend on what this machine is doing. The header is always printed.

## Run it today

Python 3.11 or newer is required. The original file was Python 2.7 (`print` statements and `python -m SimpleHTTPServer`), which is no longer a supported runtime. These instructions were checked with Python 3.12 and psutil 7.2.2.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python Lab1/socket-mon.py
```

On macOS, psutil refuses to read the system socket table unless the process is root, and the script exits with a short message. Re-run it with `sudo` (the same workaround the handout suggested). On Linux the call itself succeeds without root, but other users' sockets are omitted because their process file descriptors are not readable.

To watch a real web server, start one against the lab page and leave a request unfinished. `python -m http.server` still defaults to HTTP/1.0, so it closes the socket as soon as a response is sent. A finished `curl` is easy to miss: the accepted socket is gone, and any `TIME_WAIT` entry usually has no pid, so the filter drops it. Stopping after the headers keeps the server blocked in the request and both sockets `ESTABLISHED`.

```bash
# terminal 1, from the repository root
python -m http.server 8000 --bind 127.0.0.1 --directory Lab1

# terminal 2 — leave this running
python - <<'PY'
import socket
import time

connection = socket.create_connection(("127.0.0.1", 8000))
connection.sendall(b"GET / HTTP/1.1\r\nHost: 127.0.0.1\r\n")
time.sleep(120)
PY

# terminal 3
python Lab1/socket-mon.py
```

While that client is still running, the monitor prints two rows for the open connection. The server row has local port 8000. The client row has remote port 8000. Pids and ephemeral ports will differ:

```text
"4321","127.0.0.1@8000","127.0.0.1@51000","ESTABLISHED"
"4322","127.0.0.1@51000","127.0.0.1@8000","ESTABLISHED"
```

`curl -i http://127.0.0.1:8000/` returns the body of `Lab1/index.html`, which is the text `HELLO WORLD`. The handout's sample body was `Hello World`; the committed page was written in capitals and that text is unchanged. That curl confirms the page, and it does not leave a row attributed to the server.

The handout also pointed at Apache Bench (`ab -n 100 -c 10 http://127.0.0.1:8000/`) as a way to open many connections at once. That still works if `ab` is installed. Run the monitor while the benchmark is in progress.

### Tests and lint

```bash
python -m pip install -r requirements-dev.txt
ruff check .
ruff format .
pytest
```

GitHub Actions runs those three commands on Python 3.12 for pushes and pull requests.

## Tech stack

| Piece | Choice |
| --- | --- |
| Runtime | Python 3.11+ (3.12 in CI and `.python-version`) |
| Library | psutil 7.2.2, pinned in `requirements.txt` |
| Lint and format | Ruff 0.17.0 |
| Tests | pytest 9.1.1 |
| CI | GitHub Actions, Ubuntu, the commands above |

psutil is the only runtime dependency. It is a small cross-platform library for process and network information, which is the tool the lab required. Dev tools are listed separately in `requirements-dev.txt` so running the monitor does not install them.

## Project structure

```text
.
├── README.md                 # this guide
├── AGENTS.md                 # instructions for coding agents
├── CLAUDE.md                 # points at AGENTS.md
├── requirements.txt          # runtime pin
├── requirements-dev.txt      # runtime pin plus pytest and ruff
├── pyproject.toml            # ruff and pytest settings
├── .python-version           # 3.12
├── .github/workflows/ci.yml
├── Lab1/
│   ├── README.md             # original Spring 2017 handout
│   ├── socket-mon.py         # the monitor
│   └── index.html            # page served by the sample HTTP server
└── tests/
    └── test_socket_mon.py
```

The script keeps the filename `socket-mon.py` because that name is part of the assignment. The hyphen means it is not a normal importable module; the tests load it by path.
