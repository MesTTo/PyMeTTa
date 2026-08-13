"""Purpose: spaces across processes, the multi-context reading: each engine
is a context, serve() exposes its spaces over HTTP speaking the same tagged
wire the local boundary speaks, connect() answers a transport, and attach()
registers a remote engine's space here as a foreign space, so
(match &remote (users $id $n) ...) crosses the network exactly as it
crosses into DuckDB. The shape is SingularityNET's DAS gateway (a single
transport method carrying {space, pattern} and answering atoms) and
metta-wam's metta_server, translated onto petta's own SpaceProvider
protocol; the engine keeps unification for itself, so a remote answer is
speed and reach, never trust.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Iterator, Mapping
from urllib.request import Request, urlopen

from .atoms import Atom, from_wire
from .errors import PettaError
from .foreign import SpaceProvider

__all__ = ["serve", "connect", "attach", "RemoteSpace", "Server"]

#: A transport: one callable taking (operation, payload dict) and answering
#: the decoded JSON dict. connect() builds the HTTP one; tests may pass any
#: callable with the same contract, the DAS gateway's own injection seam.
Transport = Callable[[str, dict], dict]


class RemoteSpace(SpaceProvider):
    """A space served by another engine, reached through a transport.

    match sends the pattern's wire form and decodes the instantiated
    atoms the remote engine's own match answered; add and remove write
    through; atoms enumerates. The local engine unifies every candidate
    against the local pattern, so a lying or stale remote can only cost
    time, not soundness.
    """

    def __init__(self, transport: Transport, space: str = "&self") -> None:
        self._transport = transport
        self._space = space

    def match(self, pattern: Atom) -> Iterator[Atom]:
        answer = self._transport(
            "match", {"space": self._space, "pattern": pattern.to_wire()}
        )
        for wire in answer["atoms"]:
            yield from_wire(wire)

    def atoms(self) -> Iterator[Atom]:
        answer = self._transport("atoms", {"space": self._space})
        for wire in answer["atoms"]:
            yield from_wire(wire)

    def add(self, atom: Atom) -> None:
        self._transport("add", {"space": self._space, "atom": atom.to_wire()})

    def remove(self, atom: Atom) -> bool:
        answer = self._transport(
            "remove", {"space": self._space, "atom": atom.to_wire()}
        )
        return bool(answer.get("removed"))


def connect(
    url: str,
    timeout: float = 30.0,
    *,
    token: str | None = None,
    headers: dict[str, str] | None = None,
    ssl_context: Any = None,
) -> Transport:
    """The HTTP transport for a serve()d engine: one POST per operation,
    JSON both ways, errors surfaced with the remote's own message.

    token sends Bearer authentication, headers adds anything else a
    deployment needs (an API key, a tenant id), and ssl_context is
    Python's own ssl.SSLContext for https urls, certificate pinning
    included, so the transport composes with whatever security the
    serving side asks for."""
    base = url.rstrip("/")
    sent = {"content-type": "application/json"}
    if token is not None:
        sent["authorization"] = f"Bearer {token}"
    if headers:
        sent.update(headers)

    def transport(operation: str, payload: dict) -> dict:
        from urllib.error import HTTPError

        request = Request(
            f"{base}/{operation}",
            data=json.dumps(payload).encode("utf-8"),
            headers=dict(sent),
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout, context=ssl_context) as response:
                answer = json.loads(response.read().decode("utf-8"))
        except HTTPError as refusal:
            # The remote's refusal travels as a JSON error body; read it,
            # so the caller gets the remote engine's own words.
            body = refusal.read().decode("utf-8", "replace")
            try:
                answer = json.loads(body)
            except ValueError:
                raise PettaError(
                    f"the remote engine refused {operation}: {body[:200]}"
                ) from refusal
        if "error" in answer:
            raise PettaError(f"the remote engine refused {operation}: {answer['error']}")
        return answer

    return transport


def attach(m, name: str, url_or_transport: Any, remote_space: str = "&self") -> RemoteSpace:
    """Register a remote engine's space here under a local name.

        petta.remote.attach(m, "&hq", "http://127.0.0.1:8700")
        m.run('!(match &hq (users $id $n) $n)')
    """
    transport = (
        url_or_transport
        if callable(url_or_transport)
        else connect(url_or_transport)
    )
    provider = RemoteSpace(transport, remote_space)
    m.register_space(name, provider)
    return provider


class Server:
    """This engine's spaces, served. close() stops accepting."""

    def __init__(
        self, httpd: ThreadingHTTPServer, thread: threading.Thread, work=None,
        scheme: str = "http",
    ) -> None:
        self._httpd = httpd
        self._thread = thread
        self._work = work
        self.host, self.port = httpd.server_address[:2]
        self.url = f"{scheme}://{self.host}:{self.port}"

    def close(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        self._thread.join(timeout=10)
        if self._work is not None:
            self._work.put(None)


def serve(
    m,
    host: str = "127.0.0.1",
    port: int = 0,
    spaces: list[str] | None = None,
    *,
    token: str | None = None,
    authorize: Callable[[Mapping[str, str]], bool] | None = None,
    ssl_context: Any = None,
) -> Server:
    """Expose this engine's spaces over HTTP; port 0 picks a free one.

    Every operation answers for the space the request names, restricted
    to `spaces` when given. Security is the caller's to define, library
    fashion: token requires Bearer authentication, authorize is the
    general hook (the request headers in, a verdict out, so any scheme
    an operator runs fits), and ssl_context, Python's own
    ssl.SSLContext with a certificate loaded, serves TLS directly;
    anything heavier still composes behind a fronting proxy. match runs
    the engine's own match with the pattern as its template, so the
    instantiated atoms cross, and the caller's engine re-unifies them.

    A context is a PROCESS: serving and attaching within one process
    cannot join through the local engine, because one runtime lock guards
    both sides of that call and the serving thread would wait on the very
    evaluation that is waiting on it. Two engines, two processes, is the
    deployment this exists for; in-process, spaces already share the
    engine and need no wire."""
    from .space import MeTTa

    allowed = None if spaces is None else set(spaces)

    def space_of(payload: dict) -> MeTTa:
        name = payload.get("space", "&self")
        if allowed is not None and name not in allowed:
            raise PettaError(f"space {name!r} is not served")
        return MeTTa(name)

    def handle(operation: str, payload: dict) -> dict:
        if operation == "match":
            space = space_of(payload)
            pattern = from_wire(payload["pattern"])
            (answers,) = space.run(
                "!(collapse (match (context-space) pat pat))",
                using={"pat": pattern},
            )
            group = answers[0]
            atoms = list(group) if hasattr(group, "children") else []
            return {"atoms": [a.to_wire() for a in atoms]}
        if operation == "atoms":
            return {"atoms": [a.to_wire() for a in space_of(payload).atoms()]}
        if operation == "add":
            space_of(payload).add(from_wire(payload["atom"]))
            return {"added": True}
        if operation == "remove":
            removed = space_of(payload).remove(from_wire(payload["atom"]))
            return {"removed": removed}
        raise PettaError(f"unknown operation {operation!r}")

    # Every engine call runs on ONE persistent worker thread: janus keeps
    # a Prolog engine attached to a long-lived thread cheaply, where
    # attaching per handler thread is costly and, for the functional
    # calling convention, was observed to kill the process outright.
    import queue

    work: "queue.Queue[tuple[str, dict, queue.SimpleQueue] | None]" = queue.Queue()

    def worker() -> None:
        # A persistent engine makes this thread first-class for the
        # engine: the fast calling convention works here, and the
        # per-call temporary attach cost disappears, the janus-documented
        # pattern for a thread that calls Prolog repeatedly.
        import petta as pkg

        pkg.janus.attach_engine()
        while True:
            item = work.get()
            if item is None:
                pkg.janus.detach_engine()
                return
            operation, payload, reply = item
            try:
                reply.put(("ok", handle(operation, payload)))
            except Exception as exc:
                reply.put(("error", str(exc)))

    engine_thread = threading.Thread(target=worker, daemon=True)
    engine_thread.start()

    def authorized(headers: Mapping[str, str]) -> bool:
        if token is not None:
            if headers.get("authorization") != f"Bearer {token}":
                return False
        if authorize is not None and not authorize(headers):
            return False
        return True

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802  (http.server's spelling)
            length = int(self.headers.get("content-length", 0))
            operation = self.path.strip("/")
            if not authorized(self.headers):
                body = json.dumps({"error": "not authorized"}).encode("utf-8")
                self.send_response(401)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
                reply: queue.SimpleQueue = queue.SimpleQueue()
                work.put((operation, payload, reply))
                kind, value = reply.get(timeout=600)
                answer = value if kind == "ok" else {"error": value}
                status = 200 if kind == "ok" else 400
            except Exception as exc:
                answer, status = {"error": str(exc)}, 400
            body = json.dumps(answer).encode("utf-8")
            self.send_response(status)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: Any) -> None:
            pass  # the suite is the log; a server for humans fronts this

    httpd = ThreadingHTTPServer((host, port), Handler)
    if ssl_context is not None:
        httpd.socket = ssl_context.wrap_socket(httpd.socket, server_side=True)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return Server(httpd, thread, work, scheme="https" if ssl_context else "http")
