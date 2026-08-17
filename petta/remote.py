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
Guarantees:
  - serve compares Bearer credentials with hmac.compare_digest before
    consulting the authorization callback [tested
    test_bearer_token_uses_constant_time_comparison]
  - connect refuses non-HTTP URLs and refuses credentials over plain HTTP
    [tested test_remote_connect_refuses_non_http_urls,
    test_remote_connect_refuses_credentials_over_http]
  - serve reports worker startup failure before accepting requests and close
    waits for both owned threads to finish [tested
    test_remote_serve_reports_worker_startup_failure,
    test_remote_close_waits_for_worker_detach]
  - the HTTP boundary rejects ambiguous lengths, oversized bodies, and
    non-object JSON with a response instead of dropping the connection
    [tested test_remote_server_rejects_malformed_request_bodies]
Owns:
  - Server owns the HTTP loop and its attached-engine worker until close()
    joins both [tested test_remote_close_waits_for_worker_detach]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import hmac
import logging
import math
import queue
import threading
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from http.client import HTTPException
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from . import _json
from ._engine import bridge
from ._network import HTTPEndpoint, validated_timeout
from .atoms import Atom, Expr, Var, atom_from_wire
from .errors import PettaError
from .foreign import SpaceProvider
from .space import MeTTa

logger = logging.getLogger(__name__)

__all__ = ["RemoteSpace", "Request", "Server", "attach", "connect", "serve"]

#: A transport: one callable taking (operation, payload dict) and answering
#: the decoded JSON dict. connect() builds the HTTP one; tests may pass any
#: callable with the same contract, the DAS gateway's own injection seam.
Transport = Callable[[str, dict], dict]


class _HTTPTransport:
    """connect()'s transport: one call per operation, and it knows its
    server's GET /health, which is how server_capabilities() can ask. A
    hand-built transport that wants the same offers its own `health`."""

    def __init__(
        self,
        operate: Callable[[str, dict], dict],
        health: Callable[[], dict],
    ) -> None:
        self._operate = operate
        self._health = health

    def __call__(self, operation: str, payload: dict) -> dict:
        return self._operate(operation, payload)

    def health(self) -> dict:
        return self._health()
_SERVER_TIMEOUT = 10.0
_MAX_REQUEST_BYTES = 16 * 1024 * 1024


def _server_timeout(timeout: float) -> float:
    value = float(timeout)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"server timeout must be finite and positive, got {timeout!r}")
    return value


def _raise_failures(message: str, failures: list[BaseException]) -> None:
    if len(failures) == 1:
        raise failures[0]
    raise BaseExceptionGroup(message, failures)


class _HTTPProblem(ValueError):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


def _request_length(headers: Any) -> int:
    if headers.get("transfer-encoding") is not None:
        raise _HTTPProblem(400, "transfer-encoding is not supported; send content-length")
    values = headers.get_all("content-length", [])
    if not values:
        raise _HTTPProblem(411, "content-length is required")
    if len(values) != 1:
        raise _HTTPProblem(400, "exactly one content-length header is required")
    raw = values[0]
    if not raw.isascii() or not raw.isdigit():
        raise _HTTPProblem(400, f"content-length must be decimal digits, got {raw!r}")
    length = int(raw)
    if length > _MAX_REQUEST_BYTES:
        raise _HTTPProblem(
            413,
            f"request body exceeds the {_MAX_REQUEST_BYTES}-byte limit",
        )
    return length


@dataclass(frozen=True)
class Request:
    """What an authorize hook decides about: who is asking, what they ask
    for, and which space they name. A hook given the headers alone could
    not tell a read from a write, so read-only was inexpressible."""

    operation: str
    space: str
    headers: Mapping[str, str]


def _has_credential(headers: Mapping[str, str], token: str | None) -> bool:
    """Check the fixed Bearer credential, before the body is read at all."""
    if token is None:
        return True
    supplied = headers.get("authorization", "")
    return hmac.compare_digest(supplied, f"Bearer {token}")


def _is_authorized(
    request: Request,
    token: str | None,
    authorize: Callable[[Request], bool] | None,
) -> bool:
    """Check the fixed Bearer credential before the general policy hook."""
    return _has_credential(request.headers, token) and (
        authorize is None or authorize(request)
    )


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

    def match(self, pattern: Atom, *, limit: int | None = None) -> Iterator[Atom]:
        """Candidates for a pattern; `limit` crosses as the wire's optional
        `bound` field. Sending it is sound whatever the server does: a
        server that honors it exactly saves the work, one that ignores it
        over-answers, and the local engine re-unifies and truncates either
        way. Whether it is honored is advertised in
        `server_capabilities()`."""
        payload: dict[str, Any] = {"space": self._space, "pattern": pattern.to_wire()}
        if limit is not None:
            payload["bound"] = limit
        answer = self._transport("match", payload)
        for wire in answer["atoms"]:
            yield atom_from_wire(wire)

    def server_capabilities(self) -> dict[str, Any]:
        """The server's own advertisement from GET /health: `capabilities`
        names the seam operations it admits, so a client can ask before
        writing, and `bound` says whether /match honors the bound field
        exactly. A transport built by connect() knows its URL; a
        hand-built transport must carry its own `health` callable, or
        this refuses rather than guessing."""
        health = getattr(self._transport, "health", None)
        if health is None:
            raise PettaError(
                "this transport cannot ask the server for /health; build it "
                "with petta.remote.connect(), or give the callable a "
                "`health` attribute answering the health body"
            )
        body = health()
        # A revision-1 server advertises nothing: the four required
        # operations, bound ignored, is what its silence means.
        return {
            "capabilities": body.get(
                "capabilities", ["match", "enumerate", "add", "remove"]
            ),
            "bound": bool(body.get("bound", False)),
            "protocol": body.get("protocol"),
        }

    def atoms(self) -> Iterator[Atom]:
        answer = self._transport("atoms", {"space": self._space})
        for wire in answer["atoms"]:
            yield atom_from_wire(wire)

    def add(self, atom: Atom) -> None:
        self._transport("add", {"space": self._space, "atom": atom.to_wire()})

    def add_many(self, atoms: list[Atom]) -> None:
        """One request carries the batch, the engine's own bulk-door law on
        the wire: a batch is a transport optimisation and never a semantic
        one, and the engine already routes only plain stores through it."""
        self._transport(
            "add_many",
            {"space": self._space, "atoms": [atom.to_wire() for atom in atoms]},
        )

    def remove(self, atom: Atom) -> bool:
        answer = self._transport("remove", {"space": self._space, "atom": atom.to_wire()})
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
    serving side asks for. Only absolute http and https URLs are accepted.
    Credentials require https."""
    endpoint = HTTPEndpoint(
        url,
        subject="remote engine",
        error_type=PettaError,
        ssl_context=ssl_context,
    )
    timeout = validated_timeout(timeout, subject="remote engine timeout")
    has_credentials = token is not None or any(
        name.lower() == "authorization" for name in headers or ()
    )
    if endpoint.scheme != "https" and has_credentials:
        raise PettaError("remote engine credentials require an https URL")
    sent = {"content-type": "application/json"}
    if token is not None:
        sent["authorization"] = f"Bearer {token}"
    if headers:
        sent.update(headers)

    def transport(operation: str, payload: dict) -> dict:
        logger.debug("sending remote engine operation %s", operation)
        try:
            status, reason, raw = endpoint.request(
                "POST",
                operation,
                body=_json.dumps(payload),
                headers=sent,
                timeout=timeout,
            )
        except (HTTPException, OSError) as exc:
            logger.warning(
                "remote engine operation %s failed during transport",
                operation,
                exc_info=True,
            )
            raise PettaError(f"the remote engine request {operation} failed: {exc}") from exc
        logger.debug(
            "remote engine operation %s answered with HTTP %d",
            operation,
            status,
        )
        try:
            answer = _json.loads(raw)
        except (UnicodeDecodeError, ValueError) as exc:
            detail = raw.decode("utf-8", "replace")[:200]
            raise PettaError(
                f"the remote engine answered {status} {reason} with invalid JSON: {detail}"
            ) from exc
        if status >= 400:
            body = raw.decode("utf-8", "replace")
            detail = answer.get("error", body) if isinstance(answer, dict) else body
            raise PettaError(f"the remote engine refused {operation}: {detail}")
        if not isinstance(answer, dict):
            raise PettaError(
                f"the remote engine returned {type(answer).__name__}, expected an object"
            )
        if "error" in answer:
            raise PettaError(f"the remote engine refused {operation}: {answer['error']}")
        return answer

    def health() -> dict:
        """GET /health, the server describing itself: revision, atom
        count, capabilities, and whether /match honors bound."""
        try:
            status, reason, raw = endpoint.request(
                "GET", "health", headers=sent, timeout=timeout
            )
        except (HTTPException, OSError) as exc:
            raise PettaError(f"the remote engine health request failed: {exc}") from exc
        try:
            answer = _json.loads(raw)
        except (UnicodeDecodeError, ValueError) as exc:
            raise PettaError(
                f"the remote engine answered health with invalid JSON "
                f"({status} {reason})"
            ) from exc
        if status >= 400 or not isinstance(answer, dict):
            raise PettaError(f"the remote engine refused health: {status} {reason}")
        return answer

    return _HTTPTransport(transport, health)


def attach(m, name: str, url_or_transport: Any, remote_space: str = "&self") -> RemoteSpace:
    """Register a remote engine's space here under a local name.

    petta.remote.attach(m, "&hq", "http://127.0.0.1:8700")
    m.run('!(match &hq (users $id $n) $n)')
    """
    transport = url_or_transport if callable(url_or_transport) else connect(url_or_transport)
    provider = RemoteSpace(transport, remote_space)
    m.register_space(provider, name)
    return provider


class _RemoteWorker:
    """One attached Prolog engine serving serialized remote requests."""

    def __init__(self, handle: Callable[[str, dict], dict]) -> None:
        self._handle = handle
        self._lock = threading.Lock()
        self._started: queue.Queue[BaseException | None] = queue.Queue(maxsize=1)
        self._state = "unstarted"
        self._failures: list[BaseException] = []
        self._work: queue.Queue[tuple[str, dict, queue.SimpleQueue] | None] = queue.Queue()
        self.thread = threading.Thread(
            target=self._run,
            name="petta-remote-engine",
            daemon=True,
        )

    def start(self, timeout: float = _SERVER_TIMEOUT) -> None:
        timeout = _server_timeout(timeout)
        with self._lock:
            if self._state != "unstarted":
                raise RuntimeError(f"remote engine worker is {self._state}")
            self._state = "starting"
        try:
            self.thread.start()
        except BaseException as exc:
            self._record_failure(exc)
            raise
        try:
            failure = self._started.get(timeout=timeout)
        except queue.Empty as exc:
            self._work.put(None)
            self.thread.join(timeout)
            failure = TimeoutError(
                f"remote engine worker did not attach within {timeout:g} seconds"
            )
            self._record_failure(failure)
            raise failure from exc
        if failure is not None:
            self.thread.join(timeout)
            raise PettaError(
                f"remote engine worker could not attach: {type(failure).__name__}: {failure}"
            ) from failure
        with self._lock:
            if self._state == "starting":
                self._state = "live"

    def call(self, operation: str, payload: dict, timeout: float) -> tuple[str, Any]:
        with self._lock:
            if self._state != "live" or not self.thread.is_alive():
                raise PettaError(f"remote engine worker is {self._state}")
            reply: queue.SimpleQueue = queue.SimpleQueue()
            self._work.put((operation, payload, reply))
        try:
            return reply.get(timeout=timeout)
        except queue.Empty as exc:
            raise TimeoutError(
                f"remote engine operation {operation!r} did not finish within {timeout:g} seconds"
            ) from exc

    def stop(self, timeout: float = _SERVER_TIMEOUT, *, report_failure: bool = True) -> None:
        timeout = _server_timeout(timeout)
        with self._lock:
            if self._state == "unstarted":
                self._state = "closed"
                return
            if self._state == "closed":
                failures = tuple(self._failures)
                thread = self.thread
            else:
                if self._state in ("starting", "live"):
                    self._state = "closing"
                    self._work.put(None)
                thread = self.thread
                failures = ()
        if thread is threading.current_thread():
            raise PettaError("a remote engine worker cannot stop itself")
        if thread.is_alive():
            thread.join(timeout)
        if thread.is_alive():
            raise TimeoutError(f"remote engine worker did not stop within {timeout:g} seconds")
        with self._lock:
            failures = tuple(self._failures)
            self._state = "closed"
        if report_failure and failures:
            if len(failures) == 1:
                failure = failures[0]
                raise PettaError(
                    f"remote engine worker failed: {type(failure).__name__}: {failure}"
                ) from failure
            raise BaseExceptionGroup("remote engine worker failed", list(failures))

    def _record_failure(self, failure: BaseException) -> None:
        with self._lock:
            self._failures.append(failure)
            self._state = "failed"
        logger.error(
            "remote engine worker failed: %s: %s",
            type(failure).__name__,
            failure,
        )

    def _fail_running(self, failure: BaseException) -> None:
        self._record_failure(failure)
        pending: list[queue.SimpleQueue] = []
        with self._lock:
            while True:
                try:
                    item = self._work.get_nowait()
                except queue.Empty:
                    break
                if item is not None:
                    pending.append(item[2])
        for reply in pending:
            reply.put(("error", f"{type(failure).__name__}: {failure}"))
        if pending:
            logger.error("rejected %d queued remote request(s)", len(pending))

    def _run(self) -> None:
        try:
            janus = bridge()
            janus.attach_engine()
        except BaseException as exc:  # noqa: BLE001
            self._record_failure(exc)
            self._started.put(exc)
            return
        self._started.put(None)
        logger.debug("remote engine server worker attached a Prolog engine")
        try:
            while True:
                item = self._work.get()
                if item is None:
                    return
                operation, payload, reply = item
                try:
                    reply.put(("ok", self._handle(operation, payload)))
                except Exception as exc:
                    logger.warning(
                        "remote engine operation %s failed",
                        operation,
                        exc_info=True,
                    )
                    reply.put(("error", str(exc)))
                except BaseException as exc:  # noqa: BLE001
                    reply.put(("error", str(exc)))
                    self._fail_running(exc)
                    return
        except BaseException as exc:  # noqa: BLE001
            self._fail_running(exc)
        finally:
            try:
                janus.detach_engine()
            except BaseException as exc:  # noqa: BLE001
                self._record_failure(exc)
            else:
                logger.debug("remote engine server worker detached its Prolog engine")


class Server:
    """This engine's spaces, served. close() stops accepting."""

    def __init__(
        self,
        httpd: ThreadingHTTPServer,
        thread: threading.Thread,
        worker: _RemoteWorker,
        scheme: str = "http",
    ) -> None:
        self._httpd = httpd
        self._thread = thread
        self._worker = worker
        self._close_lock = threading.Lock()
        self._closed = False
        raw_host, self.port = httpd.server_address[:2]
        self.host = raw_host.decode("ascii") if isinstance(raw_host, bytes) else raw_host
        self.url = f"{scheme}://{self.host}:{self.port}"

    def close(self, timeout: float = _SERVER_TIMEOUT) -> None:
        """Stop accepting, detach the engine worker, and join both threads."""
        timeout = _server_timeout(timeout)
        with self._close_lock:
            if self._closed:
                return
            if self._thread is threading.current_thread():
                raise PettaError("the remote HTTP server cannot close itself")
            failures = [*self._stop_http(timeout), *self._stop_worker(timeout)]
            self._closed = not self._thread.is_alive() and not self._worker.thread.is_alive()
            if failures:
                _raise_failures("remote server close failed", failures)
            logger.debug("stopped remote engine server on %s:%d", self.host, self.port)

    def _stop_http(self, timeout: float) -> list[BaseException]:
        failures: list[BaseException] = []
        for close in (self._httpd.shutdown, self._httpd.server_close):
            try:
                close()
            except BaseException as exc:  # noqa: BLE001
                failures.append(exc)
        if self._thread.is_alive():
            self._thread.join(timeout)
        if self._thread.is_alive():
            failures.append(
                TimeoutError(f"remote HTTP server did not stop within {timeout:g} seconds")
            )
        return failures

    def _stop_worker(self, timeout: float) -> list[BaseException]:
        try:
            self._worker.stop(timeout)
        except BaseException as exc:  # noqa: BLE001
            return [exc]
        return []


def _instantiate(atom: Atom, bindings: dict) -> Atom:
    """The pattern with one answer row's bindings substituted, which is
    exactly the atom match's pattern-as-template form would answer."""
    if isinstance(atom, Var):
        bound = bindings.get(atom.name)
        return bound if bound is not None else atom
    if isinstance(atom, Expr):
        return Expr([_instantiate(child, bindings) for child in atom.children])
    return atom


def serve(
    m,
    host: str = "127.0.0.1",
    port: int = 0,
    spaces: list[str] | None = None,
    *,
    token: str | None = None,
    authorize: Callable[[Request], bool] | None = None,
    ssl_context: Any = None,
) -> Server:
    """Expose this engine's spaces over HTTP; port 0 picks a free one.

    Every operation answers for the space the request names, restricted
    to `spaces` when given. Security is the caller's to define, library
    fashion: token requires Bearer authentication, authorize is the
    general hook (a Request in, carrying the operation, the space and
    the headers, and a verdict out, so read-only, per-space and
    per-tenant policies all fit), and ssl_context, Python's own
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
    allowed = None if spaces is None else set(spaces)

    def space_of(payload: dict) -> MeTTa:
        name = payload.get("space", "&self")
        if allowed is not None and name not in allowed:
            raise PettaError(f"space {name!r} is not served")
        return m if name == m.space_name else m.space(name)

    def handle(operation: str, payload: dict) -> dict:
        if operation == "match":
            space = space_of(payload)
            pattern = atom_from_wire(payload["pattern"])
            bound = payload.get("bound")
            if bound is not None:
                # Honored EXACTLY, the trusted-Exact contract this server
                # may claim because its match is real unification: the
                # engine's own bounded query stops at the count, and the
                # rows instantiate the pattern the way match's template
                # would.
                if isinstance(bound, bool) or not isinstance(bound, int) or bound < 0:
                    raise PettaError(
                        f"bound must be a non-negative integer, got {bound!r}"
                    )
                if bound == 0:
                    # Zero answers wanted: the engine's query refuses a
                    # zero limit, and no work is the exact honoring.
                    return {"atoms": []}
                rows = space.query(pattern, limit=bound)
                names = rows.columns
                atoms = [
                    _instantiate(pattern, dict(zip(names, row, strict=True)))
                    for row in rows
                ]
                return {"atoms": [a.to_wire() for a in atoms]}
            groups = space.run(
                "!(collapse (match (context-space) pat pat))",
                using={"pat": pattern},
            )
            if len(groups) != 1 or len(groups[0]) != 1:
                raise PettaError(f"remote match returned an invalid collapse result: {groups!r}")
            group = groups[0][0]
            if not isinstance(group, Expr):
                raise PettaError(f"remote match returned a non-expression collapse: {group!r}")
            atoms = list(group)
            return {"atoms": [a.to_wire() for a in atoms]}
        if operation == "atoms":
            return {"atoms": [a.to_wire() for a in space_of(payload).atoms()]}
        if operation == "add":
            space_of(payload).add(atom_from_wire(payload["atom"]))
            return {"added": True}
        if operation == "add_many":
            atoms = [atom_from_wire(wire) for wire in payload["atoms"]]
            space_of(payload).add(*atoms)
            return {"added": len(atoms)}
        if operation == "remove":
            pattern = atom_from_wire(payload["atom"])
            space = space_of(payload)
            if isinstance(pattern, Var):
                # The protocol's law is removal by unification, and a bare
                # variable unifies with every stored atom. The engine's own
                # removal wants a storage-shaped pattern, so "everything"
                # is spelled as one removal per stored atom, equations and
                # their compiled clauses included.
                removed = False
                for atom in space.atoms():
                    removed = space.remove(atom) or removed
                return {"removed": removed}
            if not isinstance(pattern, Expr):
                # A stored atom is always an expression; a symbol or a
                # grounded value can unify with none of them.
                return {"removed": False}
            return {"removed": space.remove(pattern)}
        if operation == "health":
            return {
                "ok": True,
                "atoms": m.count(),
                "protocol": 2,
                # The reflection the in-process seam has: what this server
                # admits, so a client can ask before writing.
                "capabilities": ["match", "enumerate", "add", "remove"],
                # /match honors the optional bound field exactly.
                "bound": True,
            }
        raise PettaError(f"unknown operation {operation!r}")

    # Every engine call runs on one persistent attached-engine worker.
    worker = _RemoteWorker(handle)

    class Handler(BaseHTTPRequestHandler):
        def setup(self) -> None:
            super().setup()
            self.connection.settimeout(_SERVER_TIMEOUT)

        def _payload(self) -> dict:
            length = _request_length(self.headers)
            try:
                raw = self.rfile.read(length)
            except TimeoutError as exc:
                raise _HTTPProblem(408, "request body timed out") from exc
            if len(raw) != length:
                raise _HTTPProblem(
                    400,
                    f"request body ended after {len(raw)} of {length} bytes",
                )
            try:
                payload = _json.loads(raw)
            except (UnicodeDecodeError, ValueError) as exc:
                raise _HTTPProblem(400, f"request body is not valid JSON: {exc}") from exc
            if not isinstance(payload, dict):
                raise _HTTPProblem(
                    400,
                    f"request body must be a JSON object, got {type(payload).__name__}",
                )
            return payload

        def _refuse_unauthorized(self, operation: str) -> None:
            logger.warning("refused unauthorized remote engine operation %s", operation)
            body = _json.dumps({"error": "not authorized"})
            self.send_response(401)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _collected_headers(self) -> dict[str, str]:
            headers: dict[str, str] = {}
            for name, value in self.headers.items():
                key = name.lower()
                headers[key] = f"{headers[key]}, {value}" if key in headers else value
            return headers

        def do_GET(self) -> None:
            operation = self.path.strip("/")
            headers = self._collected_headers()
            # The same gates as every POST, credential then policy hook:
            # health names what the server admits, which is not an
            # anonymous answer when a token or a policy is configured.
            if not _has_credential(headers, token):
                self._refuse_unauthorized(operation)
                return
            request = Request(operation, m.space_name, headers)
            if authorize is not None and not authorize(request):
                self._refuse_unauthorized(operation)
                return
            if operation == "health":
                try:
                    kind, value = worker.call("health", {}, timeout=600.0)
                    answer = value if kind == "ok" else {"error": value}
                    status = 200 if kind == "ok" else 400
                except Exception as exc:  # noqa: BLE001  the wire answers errors as JSON
                    answer, status = {"error": str(exc)}, 400
            else:
                answer, status = {"error": f"unknown operation {operation!r}"}, 400
            body = _json.dumps(answer)
            self.send_response(status)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _method_not_allowed(self) -> None:
            # The protocol's own refusal: only POST operates (and GET
            # answers /health). BaseHTTPRequestHandler would say 501,
            # which reads as "not implemented yet" rather than "never".
            body = _json.dumps(
                {"error": f"method {self.command} is not supported; POST an operation"}
            )
            self.send_response(405)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        do_PUT = _method_not_allowed
        do_DELETE = _method_not_allowed
        do_PATCH = _method_not_allowed

        def do_POST(self) -> None:
            operation = self.path.strip("/")
            headers = self._collected_headers()
            # The fixed credential decides before the body is read, so a
            # request without it drives no parser. The policy hook decides
            # after, because the space it judges is in the body.
            if not _has_credential(headers, token):
                self._refuse_unauthorized(operation)
                return
            try:
                payload = self._payload()
                request = Request(operation, str(payload.get("space", m.space_name)), headers)
                if authorize is not None and not authorize(request):
                    self._refuse_unauthorized(operation)
                    return
                kind, value = worker.call(operation, payload, timeout=600.0)
                answer = value if kind == "ok" else {"error": value}
                status = 200 if kind == "ok" else 400
            except _HTTPProblem as exc:
                logger.warning(
                    "remote engine HTTP handler rejected operation %s: %s",
                    operation,
                    exc,
                )
                answer, status = {"error": str(exc)}, exc.status
            except Exception as exc:
                logger.warning(
                    "remote engine HTTP handler rejected operation %s",
                    operation,
                    exc_info=True,
                )
                answer, status = {"error": str(exc)}, 400
            body = _json.dumps(answer)
            self.send_response(status)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            logger.debug(
                "served remote engine operation %s with HTTP %d",
                operation,
                status,
            )

        def log_message(self, format: str, *args: Any) -> None:
            logger.debug("remote HTTP: " + format, *args)

    httpd = ThreadingHTTPServer((host, port), Handler)
    # Handler threads are request-scoped. Server.close bounds the owned HTTP
    # loop and engine worker instead of inheriting a process-exit wait here.
    httpd.daemon_threads = True
    thread = threading.Thread(
        target=httpd.serve_forever,
        name="petta-remote-http",
        daemon=True,
    )
    try:
        if ssl_context is not None:
            httpd.socket = ssl_context.wrap_socket(httpd.socket, server_side=True)
        worker.start()
        thread.start()
        server = Server(
            httpd,
            thread,
            worker,
            scheme="https" if ssl_context else "http",
        )
    except BaseException as start_error:
        cleanup_failures: list[BaseException] = []
        if thread.is_alive():
            try:
                httpd.shutdown()
            except BaseException as exc:  # noqa: BLE001
                cleanup_failures.append(exc)
            thread.join(_SERVER_TIMEOUT)
        try:
            worker.stop(report_failure=False)
        except BaseException as exc:  # noqa: BLE001
            cleanup_failures.append(exc)
        try:
            httpd.server_close()
        except BaseException as exc:  # noqa: BLE001
            cleanup_failures.append(exc)
        if cleanup_failures:
            raise BaseExceptionGroup(
                "remote server startup and cleanup failed",
                [start_error, *cleanup_failures],
            ) from None
        raise
    logger.debug("started remote engine server on %s", server.url)
    return server
