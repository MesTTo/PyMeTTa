"""Purpose: spaces across processes, the multi-context reading: each engine
is a context, serve() exposes its spaces over HTTP speaking the same tagged
wire the local boundary speaks, connect() answers a transport, and RemoteSpace over it is the backing metta.attach() registers
registers a remote engine's space here as a foreign space, so
(match &remote (users $id $n) ...) crosses the network exactly as it
crosses into DuckDB. The shape is SingularityNET's DAS gateway (a single
transport method carrying {space, pattern} and answering atoms) and
metta-wam's metta_server, translated onto metta's own SpaceProvider
protocol; the engine keeps unification for itself, so a remote answer is
speed and reach, never trust.
Guarantees:
  - remote JSON decoding preserves explicit s and p tags instead of applying
    process-local engine provenance [tested:
    test_space_handles_are_term_operands_and_round_trip; commit=4e2398075da67bb2cbcc123a9fc1e078ecac6fbf]
  - the ask/next/stop lifecycle answers a chunk at a time and never looks
    ahead, so taking two answers of an enumeration costs two answers'
    engine work whatever the enumeration's size [measured 2026-08-20 over
    real HTTP: 1,250 inferences for two answers whether the space held 10
    atoms or 10,000, against 1,839 and 1,490,407 for the eager door]
    [tested test_two_answers_cross_the_wire_without_the_third_being_computed]
  - a cursor nobody pulls from is released after cursor_idle seconds and
    a gateway refuses to hold more than cursor_limit at once [tested
    test_an_idle_cursor_is_released,
    test_a_gateway_refuses_more_cursors_than_it_holds]
  - close() releases every cursor a client left open [tested
    test_closing_the_server_releases_open_cursors]
  - a candidate whose instantiation is a rational tree crosses as the stored
    atom, the finite form the protocol names for it, instead of being dropped
    from the reply [tested: test_a_rational_tree_candidate_crosses_as_the_stored_atom,
    test_the_kit_certifies_the_attached_space; commit=57f21ba9edf94bcf28cde11f938bce2c241a3709]
  - one stored atom reads back as one atom, however much matching the server
    did in between [tested:
    test_two_reads_of_one_stored_atom_answer_the_same_atom; commit=57f21ba9edf94bcf28cde11f938bce2c241a3709]
  - a close releases what it can and stays retryable: a failed /stop keeps its
    token, close_all closes every cursor before it raises, and a server whose
    worker did not stop leaves its cursors to the next close rather than
    closing one under a live request [tested:
    test_a_failed_stop_leaves_the_remote_cursor_retryable,
    test_closing_every_cursor_survives_one_failure,
    test_a_close_that_cannot_stop_the_worker_keeps_the_cursors;
    commit=57f21ba9edf94bcf28cde11f938bce2c241a3709]
  - GET /health answers an authorization hook's own failure as JSON instead of
    dropping the connection [tested:
    test_a_failing_authorize_hook_answers_json_on_health; commit=57f21ba9edf94bcf28cde11f938bce2c241a3709]
  - the same-process guard covers the addresses a wildcard bind serves and the
    addresses its caller is about to serve [tested:
    test_attaching_a_wildcard_served_space_through_loopback_is_refused,
    test_a_manifest_that_attaches_before_it_serves_is_refused;
    commit=57f21ba9edf94bcf28cde11f938bce2c241a3709]
  - the authorize hook judges /next and /stop against the space the
    cursor's answers come from, not the request's absent space field
    [tested test_authorize_sees_the_cursors_own_space]
  - serve compares Bearer credentials with hmac.compare_digest before
    consulting the authorization callback [tested
    test_bearer_token_uses_constant_time_comparison]
  - an omitted payload space resolves to the gateway's served context for both
    authorization and execution [tested:
    test_an_omitted_remote_space_cannot_cross_the_authorization_boundary;
    commit=af5821f5ffb7ce186e516706f003d02f5c1d3b4a]
  - connect refuses non-HTTP URLs and refuses credentials over plain HTTP
    [tested test_remote_connect_refuses_non_http_urls,
    test_remote_connect_refuses_credentials_over_http]
  - serve reports worker startup failure before accepting requests and close
    waits for both owned threads to finish [tested
    test_remote_serve_reports_worker_startup_failure,
    test_remote_close_waits_for_worker_detach]
  - a worker call that times out is abandoned before it can start, or its
    running engine goal is interrupted and drained before later work starts
    [tested:
    test_a_timed_out_remote_worker_never_runs_or_finishes_the_abandoned_write;
    commit=d64d3cc64e1e7b528e0043a67cb05f6c02da455f]
  - the HTTP boundary rejects ambiguous lengths, oversized bodies, and
    non-object JSON with a response instead of dropping the connection
    [tested test_remote_server_rejects_malformed_request_bodies]
  - RemoteSpace claims every capability the wire carries and declares no
    event delivery, because the wire carries no event and a watcher would
    hear only this process's own writes [measured 2026-08-19: an attached
    space delivered the one atom this process wrote and nothing for the atom
    the server added] [tested
    test_remote_space_claims_subscribe_only_if_the_channel_exists]
Owns:
  - Server owns the HTTP loop and its attached-engine worker until close()
    joins both [tested test_remote_close_waits_for_worker_detach]
  - a Gateway owns every cursor ask/next/stop holds open, one engine each,
    released by close(), by the stream ending, or by the idle deadline
    [tested test_closing_the_server_releases_open_cursors]
Fails when:
  - a program wants to watch a remote space. There is no event channel to
    build that on, so the capability is refused rather than half-kept; the
    refusal names polling and bridge() as the two routes that do work
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import hmac
import logging
import math
import queue
import secrets
import socket
import threading
import time
import warnings
from collections import deque
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from http.client import HTTPException
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from itertools import islice
from typing import Any, Self
from urllib.parse import urlsplit

from . import _json
from ._atom_wire import _atom_from_wire
from ._engine import bridge, runtime
from ._network import HTTPEndpoint, validated_timeout
from ._space import Space as MeTTa
from ._space_objects import Cursor
from .atoms import Atom, Expression, Variable, substitute, unify
from .errors import Interrupted, MettaError
from .foreign import SpaceProvider

logger = logging.getLogger(__name__)
logging.getLogger("metta").addHandler(logging.NullHandler())

__all__ = [
    "Gateway",
    "RemoteCursor",
    "RemoteSpace",
    "Request",
    "Server",
        "connect",
    "serve",
]

#: A transport: one callable taking (operation, payload dict) and answering
#: the decoded JSON dict. connect() builds the HTTP one; tests may pass any
#: callable with the same contract, the DAS gateway's own injection seam.
Transport = Callable[[str, dict], dict]


class _HTTPTransport:
    """connect()'s transport: one call per operation, and it knows its
    server's GET /health, which is how server_capabilities() can ask. A
    hand-built transport that wants the same offers its own `health`.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

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

#: How many answers one reply of the ask/next lifecycle may carry when the
#: request names no batch. One, so a client that never asks for more never
#: pays for one, which is the whole point of the lazy door; pengines picks
#: the same default for the same field, its `chunk`
#: [source 2026-08-20: /usr/lib/swi-prolog/library/ext/pengines/pengines.pl,
#: pengine_ask/3's chunk(1) option].
_DEFAULT_BATCH = 1

#: Seconds an untouched cursor survives before the server releases the
#: engine behind it. A client that dies mid-stream would otherwise leak
#: one engine per abandoned query; pengines bounds the same resource the
#: same way, `idle_limit`, and picks the same 300 seconds
#: [source 2026-08-20: pengines.pl, "Pengine auto-destroys when idle for
#: this time"].
_CURSOR_IDLE = 300.0

#: How many cursors one gateway holds open at once. An open cursor owns an
#: engine and its stacks, so the ceiling is refused rather than grown.
_CURSOR_LIMIT = 256


def _server_timeout(timeout: float, subject: str = "server timeout") -> float:
    value = float(timeout)
    if not math.isfinite(value) or value <= 0:
        msg = f"{subject} must be finite and positive, got {timeout!r}"
        raise ValueError(msg)
    return value


def _raise_failures(message: str, failures: list[BaseException]) -> None:
    if len(failures) == 1:
        raise failures[0]
    raise BaseExceptionGroup(message, failures)


class _HTTPProblem(ValueError):  # noqa: N818  -- the exception name is a domain outcome in the public protocol, not an implementation error suffix
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
    not tell a read from a write, so read-only was inexpressible.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

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


class RemoteCursor:
    """A remote answer stream: `/ask` opened it, `/next` pulls the next
    chunk, `/stop` releases it.

    Space.stream()'s Cursor with a wire under it, and the same discipline:
    iterate it, close() it, or leave its with-block. Exhaustion releases
    the server's cursor and stays ordinary iterator exhaustion; an
    explicit close is the separate state that refuses further pulls.

        with space.stream(pattern) as answers:
            for atom in answers:
                if wanted(atom):
                    break          # the server computes nothing further

    `batch` is how many answers one crossing carries. One is the fully
    lazy reading and the protocol's default; raising it trades an answer
    that may go unwanted for a saved round trip, the same choice a
    database driver's fetch size makes.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    __slots__ = ("__weakref__", "_batch", "_buffer", "_closed", "_space", "_token", "_transport")

    def __init__(  # noqa: D107  -- the enclosing class documents construction and the object invariants
        self,
        transport: Transport,
        space: str,
        pattern: Atom,
        *,
        batch: int = _DEFAULT_BATCH,
        limit: int | None = None,
    ) -> None:
        if isinstance(batch, bool) or not isinstance(batch, int) or batch < 1:
            msg = f"batch must be a positive integer, got {batch!r}"
            raise ValueError(msg)
        self._transport = transport
        self._space = space
        self._batch = batch
        self._closed = False
        self._token: str | None = None
        self._buffer: deque[Atom] = deque()
        payload: dict[str, Any] = {
            "space": space,
            "pattern": pattern.to_wire(),
            "batch": batch,
        }
        if limit is not None:
            payload["bound"] = limit
        self._absorb(transport("ask", payload))

    def _absorb(self, answer: dict) -> None:
        """Take a reply's chunk and its continuation.

        A chunk that carries nothing while still naming a cursor is
        refused rather than looped on: the protocol says a short chunk
        ends the stream, so an empty one with a live cursor is a server
        that would spin a client forever.
        """
        atoms = answer.get("atoms")
        if not isinstance(atoms, list):
            msg = f"the remote engine answered a chunk without an atom list: {answer!r}"
            raise MettaError(
                msg
            )
        token = answer.get("cursor")
        if token is not None and not isinstance(token, str):
            msg = f"the remote engine answered a non-string cursor: {token!r}"
            raise MettaError(msg)
        if token is not None and not atoms:
            msg = (
                "the remote engine answered a live cursor with no atoms; a "
                "chunk that carries nothing ends the stream and must answer "
                "a null cursor"
            )
            raise MettaError(
                msg
            )
        self._token = token
        self._buffer.extend(_atom_from_wire(wire) for wire in atoms)

    def __iter__(self) -> Iterator[Atom]:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return self

    def __next__(self) -> Atom:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        if self._closed:
            msg = "this cursor is closed"
            raise MettaError(msg)
        while not self._buffer:
            if self._token is None:
                raise StopIteration
            self._absorb(
                self._transport("next", {"cursor": self._token, "batch": self._batch})
            )
        return self._buffer.popleft()

    def close(self) -> None:
        """Release the server's cursor; idempotent, and distinct from
        exhaustion, which released it already.

        The token survives a failed /stop and the cursor stays open, because
        a close that discarded it first could never release the server's
        cursor afterwards: every later close returned at the flag while the
        server held the engine to its idle deadline [tested
        test_a_failed_stop_leaves_the_remote_cursor_retryable].
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if self._closed:
            return
        token = self._token
        if token is not None:
            self._transport("stop", {"cursor": token})
            self._token = None
        self._closed = True
        self._buffer.clear()

    def __enter__(self) -> Self:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        """Stop the server's cursor without letting the stop displace the
        diagnosis: a transport that broke mid-stream breaks the /stop too,
        and the failure a caller needs to read is the first one. Both are
        raised together, the same shape serve()'s own startup path uses.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if exc is None:
            self.close()
            return
        try:
            self.close()
        except BaseException as stop_failure:  # noqa: BLE001
            msg = "the remote cursor failed and could not be stopped"
            raise BaseExceptionGroup(
                msg,
                [exc, stop_failure],
            ) from None

    def __del__(self) -> None:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        if not getattr(self, "_closed", True) and getattr(self, "_token", None) is not None:
            # No stop is sent from here: a destructor is the wrong place
            # for a network round trip, and the server's own idle deadline
            # is what releases a cursor whose client walked away.
            warnings.warn(
                "an open metta RemoteCursor was discarded; use a with-block "
                "or close(), or the server holds it until its idle deadline",
                ResourceWarning,
                source=self,
                stacklevel=2,
            )

    def __repr__(self) -> str:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        # Buffered atoms count as open: the server has let go of the
        # stream but the caller has not read the last chunk yet.
        if self._closed:
            state = "closed"
        elif self._token is not None or self._buffer:
            state = "open"
        else:
            state = "exhausted"
        return f"<remote cursor {state} on {self._space}>"


class RemoteSpace(SpaceProvider):
    """A space served by another engine, reached through a transport.

    match sends the pattern's wire form and decodes the instantiated
    atoms the remote engine's own match answered; add and remove write
    through; atoms enumerates. The local engine unifies every candidate
    against the local pattern, so a lying or stale remote can only cost
    time, not soundness.

    `batch` chooses which door match() uses, and the choice is the one
    match() and stream() make in-process. Left None, match() is the eager
    /match: one crossing carrying the whole answer set, which is what a
    space whose answers fit in an HTTP body wants. Set to a count, match()
    rides the ask/next/stop lifecycle in chunks of that size, so a caller
    that stops early stops the server's work with it and an answer set
    larger than one body still crosses.

    It does NOT subscribe, and that is the one capability a provider has to
    promise rather than implement. See delivers.
    """

    def __init__(  # noqa: D107  -- the enclosing class documents construction and the object invariants
        self,
        transport: Transport,
        space: str = "&self",
        *,
        batch: int | None = None,
    ) -> None:
        if batch is not None and (
            isinstance(batch, bool) or not isinstance(batch, int) or batch < 1
        ):
            msg = f"batch must be a positive integer or None, got {batch!r}"
            raise ValueError(msg)
        self._transport = transport
        self._space = space
        self._batch = batch

    def delivers(self) -> tuple[str, str] | None:
        """Nothing: the wire carries no event.

        The wire has four operations, match, enumerate, add and remove, and
        none of them carries an event, while a remote space's contents change
        on the server, which is the whole reason it is remote. So a watcher
        here would hear only the writes this process made and silently miss
        every other one [measured 2026-08-19: an attached space delivered the
        one atom this process wrote and nothing for the atom the server
        added]. Declaring nothing is what refuses the subscription; the
        sentence below is what a caller reads.
        """
        return None

    def refusal(self, capability: str, /, **_request: Any) -> str | None:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        if capability != "subscribe":
            return None
        return (
            "a remote space has no event channel: its contents change on the "
            "server and the wire carries no event, so a watcher here would "
            "hear only this process's own writes and miss every other one. "
            "Poll match(), or run the subscription on the engine that owns "
            "the space and bridge() the changes here, which needs only add "
            "and remove on this side"
        )

    def match(self, pattern: Atom, *, limit: int | None = None) -> Iterator[Atom]:
        """Candidates for a pattern; `limit` crosses as the wire's optional
        `bound` field. Sending it is sound whatever the server does: a
        server that honors it exactly saves the work, one that ignores it
        over-answers, and the local engine re-unifies and truncates either
        way. Whether it is honored is advertised in
        `server_capabilities()`.

        One crossing carries the whole answer set unless this space was
        built with a `batch`, in which case the ask/next/stop lifecycle
        carries it a chunk at a time and an engine that stops pulling
        stops the server.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if self._batch is not None:
            with self.stream(pattern, batch=self._batch, limit=limit) as answers:
                yield from answers
            return
        payload: dict[str, Any] = {"space": self._space, "pattern": pattern.to_wire()}
        if limit is not None:
            payload["bound"] = limit
        answer = self._transport("match", payload)
        for wire in answer["atoms"]:
            yield _atom_from_wire(wire)

    def stream(
        self,
        pattern: Atom,
        *,
        batch: int = _DEFAULT_BATCH,
        limit: int | None = None,
    ) -> RemoteCursor:
        """The lazy door: answers pulled a chunk at a time, so taking two
        of a large enumeration costs the server two answers' work instead
        of the whole join's.

        match() is the eager door and stays it, the split match() and
        stream() already make in-process. Reach for this to take answers
        until you have seen enough, or when the answer set is larger than
        one HTTP body.

        `limit` is the wire's `bound` and carries the same advice it
        carries on match(): a server that can honor it exactly stops at
        the count, one that cannot ignores it and over-answers. It is not
        truncated again here, because a server may answer candidates
        rather than answers, and cutting an over-approximated stream at
        the count is the under-approximation the protocol forbids. The
        first ask crosses when the cursor is built, as the in-process
        cursor opens its engine when it is built.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return RemoteCursor(
            self._transport, self._space, pattern, batch=batch, limit=limit
        )

    def server_capabilities(self) -> dict[str, Any]:
        """The server's own advertisement from GET /health: `capabilities`
        names the seam operations it admits, so a client can ask before
        writing, and `bound` says whether /match honors the bound field
        exactly. A transport built by connect() knows its URL; a
        hand-built transport must carry its own `health` callable, or
        this refuses rather than guessing.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        health = getattr(self._transport, "health", None)
        if health is None:
            msg = (
                "this transport cannot ask the server for /health; build it "
                "with metta.remote.connect(), or give the callable a "
                "`health` attribute answering the health body"
            )
            raise MettaError(
                msg
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

    def atoms(self) -> Iterator[Atom]:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        answer = self._transport("atoms", {"space": self._space})
        for wire in answer["atoms"]:
            yield _atom_from_wire(wire)

    def add(self, atom: Atom) -> None:
        """Store one atom on the serving side.

        A transport TIMEOUT means UNKNOWN, not failed: the server may
        still be processing the request when the client stops waiting, so
        a mutation behind a timeout can have committed. Exactly-once
        delivery needs idempotency keys and server-side deduplication,
        which the remote protocol does not carry yet; until it does,
        re-checking with a read is the caller's disambiguation.
        """
        self._transport("add", {"space": self._space, "atom": atom.to_wire()})

    def add_many(self, atoms: list[Atom]) -> None:
        """One request carries the batch, the engine's own bulk-door law on
        the wire: a batch is a transport optimisation and never a semantic
        one, and the engine already routes only plain stores through it.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        self._transport(
            "add_many",
            {"space": self._space, "atoms": [atom.to_wire() for atom in atoms]},
        )

    def remove(self, atom: Atom) -> bool:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        answer = self._transport("remove", {"space": self._space, "atom": atom.to_wire()})
        return bool(answer.get("removed"))


#: Every live server in THIS process, keyed by the address it accepts on.
#: the space() URL door reads it to refuse a configuration that cannot work; Server
#: registers on construction and releases on close.
_LIVE_SERVERS: dict[tuple[str, int], tuple[str, ...]] = {}
_LIVE_SERVERS_LOCK = threading.Lock()
#: The spellings of one loopback address, so a server bound to 127.0.0.1 is
#: recognised through `localhost` too.
_LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})

#: Bind addresses that mean "every address this host has", and the families
#: each answers on. A server bound to one of them serves every spelling of
#: every interface, so its registry entry cannot list them and the guard asks
#: the operating system instead. "::" is dual-stack wherever this runs, so it
#: carries IPv4 too.
_WILDCARD_FAMILIES: dict[str, frozenset[int]] = {
    "0.0.0.0": frozenset({socket.AF_INET}),  # noqa: S104  # nosec B104 -- recognising a wildcard bind, not making one
    "": frozenset({socket.AF_INET}),
    "::": frozenset({socket.AF_INET, socket.AF_INET6}),
}


def _local_families(hostname: str) -> frozenset[int]:
    """The address families in which `hostname` names an address of THIS host.

    Binding is the exact test, and the portable one: Python enumerates no
    interfaces, while the operating system already knows which addresses are
    its own and refuses to bind any other. A host with net.ipv4.ip_nonlocal_bind
    set answers yes for an address it does not hold, which costs one refusal
    message on a configuration that would have worked, against a deadlock that
    names nothing.
    """
    try:
        candidates = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except OSError:
        return frozenset()  # a name this host cannot resolve is not this host
    families: set[int] = set()
    for family, _type, _protocol, _canonical, sockaddr in candidates:
        if family in families:
            continue
        with socket.socket(family, socket.SOCK_STREAM) as probe:
            try:
                probe.bind((sockaddr[0], 0, *sockaddr[2:]))
            except OSError:
                continue
        families.add(family)
    return frozenset(families)


def _refuse_this_process(
    url: object, name: str, pending: Iterable[tuple[str, int]] = ()
) -> None:
    """Refuse attaching a space served by THIS process over HTTP.

    Janus holds the GIL across a Prolog call, so while one thread is inside an
    evaluation no other thread can run Prolog, whatever engine it attached.
    An attached space is only ever matched from inside an evaluation, so this
    configuration cannot complete: measured, the request times out after the
    transport's whole timeout and the serving side then fails on a broken
    pipe, and neither message names the cause.

    `pending` names addresses the caller is ABOUT to serve and has not bound
    yet. The live registry cannot know about a server that starts one line
    later, so an assembler performing an attach form before its own serve
    form walked straight past this guard and deadlocked when the server
    arrived: the same two forms were refused in one order and accepted in the
    other [tested test_a_manifest_that_attaches_before_it_serves_is_refused].
    The configuration is what is wrong, not the ordering.

    A plain HTTP call to the same server from outside an evaluation works and
    is not refused here; the guard is on the space() URL door, whose spaces
    are only ever matched from inside one.
    """
    if not isinstance(url, str):
        return
    parsed = urlsplit(url)
    if parsed.hostname is None or parsed.port is None:
        return  # nothing to match an address against; connect() judges the URL
    hosts = _LOOPBACK if parsed.hostname in _LOOPBACK else {parsed.hostname}
    endpoint_port = parsed.port
    with _LIVE_SERVERS_LOCK:
        servers = dict(_LIVE_SERVERS)
    for host, port in pending:
        # A server that has not started serves no space yet, so the remedy
        # below names the default rather than one of its own.
        servers.setdefault((str(host), int(port)), ())
    served = next(
        (
            spaces
            for host in hosts
            if (spaces := servers.get((host, endpoint_port))) is not None
        ),
        None,
    )
    wildcards = [
        (spaces, families)
        for host, families in _WILDCARD_FAMILIES.items()
        if (spaces := servers.get((host, endpoint_port))) is not None
    ]
    if served is None and wildcards:
        # A wildcard bind answers on every address this host has, so the
        # registry entry names none of them and 127.0.0.1 or localhost walked
        # straight past this guard into the deadlock [tested
        # test_attaching_a_wildcard_served_space_through_loopback_is_refused].
        local = _local_families(parsed.hostname)
        served = next(
            (spaces for spaces, families in wildcards if families & local), None
        )
    if served is None:
        return
    remote_space = served[0] if served else "&self"
    msg = (
        f"{url} is served by this same process, and attaching it over HTTP "
        f"cannot work: janus holds the GIL across a Prolog call, so the "
        f"serving thread cannot run while the evaluation that is waiting on "
        f"it holds the interpreter. Left to run it times out and then breaks "
        f"the connection.\n\n"
        f"In one process, use the transport that runs on the calling thread:\n\n"
        f"    gateway = metta.remote.Gateway(server_space)\n"
        f"    metta.attach({name!r}, metta.remote.RemoteSpace(gateway, {remote_space!r}))\n\n"
        f"A URL is for reaching an engine in ANOTHER process."
    )
    raise MettaError(msg)


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
    Credentials require https.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    endpoint = HTTPEndpoint(
        url,
        subject="remote engine",
        error_type=MettaError,
        ssl_context=ssl_context,
    )
    timeout = validated_timeout(timeout, subject="remote engine timeout")
    has_credentials = token is not None or any(
        name.lower() == "authorization" for name in headers or ()
    )
    if endpoint.scheme != "https" and has_credentials:
        msg = "remote engine credentials require an https URL"
        raise MettaError(msg)
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
            msg = f"the remote engine request {operation} failed: {exc}"
            raise MettaError(msg) from exc
        logger.debug(
            "remote engine operation %s answered with HTTP %d",
            operation,
            status,
        )
        try:
            answer = _json.loads(raw)
        except (UnicodeDecodeError, ValueError) as exc:
            detail = raw.decode("utf-8", "replace")[:200]
            msg = f"the remote engine answered {status} {reason} with invalid JSON: {detail}"
            raise MettaError(
                msg
            ) from exc
        if status >= 400:
            body = raw.decode("utf-8", "replace")
            detail = answer.get("error", body) if isinstance(answer, dict) else body
            msg = f"the remote engine refused {operation}: {detail}"
            raise MettaError(msg)
        if not isinstance(answer, dict):
            msg = f"the remote engine returned {type(answer).__name__}, expected an object"
            raise MettaError(
                msg
            )
        if "error" in answer:
            msg = f"the remote engine refused {operation}: {answer['error']}"
            raise MettaError(msg)
        return answer

    def health() -> dict:
        """GET /health, the server describing itself: revision, atom
        count, capabilities, and whether /match honors bound.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        try:
            status, reason, raw = endpoint.request(
                "GET", "health", headers=sent, timeout=timeout
            )
        except (HTTPException, OSError) as exc:
            msg = f"the remote engine health request failed: {exc}"
            raise MettaError(msg) from exc
        try:
            answer = _json.loads(raw)
        except (UnicodeDecodeError, ValueError) as exc:
            msg = (
                f"the remote engine answered health with invalid JSON "
                f"({status} {reason})"
            )
            raise MettaError(
                msg
            ) from exc
        if status >= 400 or not isinstance(answer, dict):
            # The body's own sentence when there is one, the same detail POST
            # surfaces: a policy hook that refused, or failed, says why here.
            detail = answer.get("error") if isinstance(answer, dict) else None
            msg = (
                f"the remote engine refused health: {status} {reason}"
                if detail is None
                else f"the remote engine refused health: {detail}"
            )
            raise MettaError(msg)
        return answer

    return _HTTPTransport(transport, health)


#: The engine's own wording when a binding has no finite wire form, which is
#: how the eager door learns a candidate is a rational tree
#: [source: extensions/python/metta/shim.pl, metta_py_wire_refuse/0].
_RATIONAL_TREE = "rational-tree binding has no finite wire form"


def _linear(pattern: Atom) -> Atom | None:
    """The pattern with every repeated variable occurrence made distinct.

    None when no variable repeats at all.

    A repeated variable is the only way a match can bind a variable to a term
    that contains it: the stored atoms come out of the database with their own
    fresh variables, so nothing else can close the loop. The linearised
    pattern cannot, because every occurrence is its own variable and each
    binds to a subterm of the stored atom, which is why the relaxed match
    answers a finite atom for a candidate whose real instantiation is a
    rational tree. The relaxed match over-answers, and the caller filters it
    back with the engine's own unification.
    """
    counts: dict[str, int] = {}

    def distinct(term: Atom) -> Atom:
        if not isinstance(term, Variable) or term.name == "_":
            return term
        seen = counts.get(term.name, 0)
        counts[term.name] = seen + 1
        # The suffix keeps the reading of the name it came from; a pattern
        # carrying both `$x` twice and a literal `$x-relaxed-1` would collide,
        # and no caller writes that.
        return term if seen == 0 else Variable(f"{term.name}-relaxed-{seen}")

    relaxed = pattern.map(distinct)
    return relaxed if any(count > 1 for count in counts.values()) else None


def _read_out(atom: Atom) -> Atom:
    """A stored atom with its variables named by the walk that reads it.

    The names come out the same every time the atom is read.

    A stored variable's engine name is a stack offset that moves with every
    match the server runs, so two reads of ONE atom crossed as two atoms that
    printed differently and a client comparing printed forms saw a space
    changing under it, against the `repeated` source this server declares
    [measured 2026-08-30: (gc-fact (f $_78) $_78) read back as $_2184, then
    $_3998, then $_5764, after one match each; tested
    test_two_reads_of_one_stored_atom_answer_the_same_atom]. The engine that
    re-unifies a candidate renames its variables apart regardless, so the
    name carries nothing but this identity [measured 2026-08-30: a
    candidate's $a does not collide with a pattern's own $a].
    """
    names: dict[str, str] = {}

    def named(term: Atom) -> Atom:
        if not isinstance(term, Variable) or term.name == "_":
            return term
        return Variable(names.setdefault(term.name, f"_{len(names)}"))

    return atom.map(named)


def _wire(atoms: list[Atom]) -> list:
    """The wire forms of the atoms a reply answers, each named by _read_out.

    Every door names them the same way, so the eager reply and the chunks of
    the lazy one are the same atoms rather than the same atoms under two
    spellings, and one stored atom read twice is one atom.
    """
    return [_read_out(atom).to_wire() for atom in atoms]


def _apart(atom: Atom) -> Atom:
    """The atom with its variables renamed away from a client's pattern.

    This is the renaming the engine's own re-unification does before it
    matches. `_` stays anonymous, because naming it would force two of its
    occurrences to be equal.
    """
    return atom.map(
        lambda term: Variable(f"remote-candidate-{term.name}")
        if isinstance(term, Variable) and term.name != "_"
        else term
    )


def _batch_of(payload: dict) -> int:
    """The chunk one reply may carry: how many answers this crossing buys."""
    value = payload.get("batch", _DEFAULT_BATCH)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        msg = f"batch must be a positive integer, got {value!r}"
        raise MettaError(msg)
    return value


def _atom_of(payload: dict, name: str) -> Atom:
    """A wire atom a request must carry, named when it is missing.

    A bare payload[name] answered a KeyError whose whole message was the
    field's name in quotes, which tells a client implementer nothing about
    what its request left out.
    """
    wire = payload.get(name)
    if wire is None:
        msg = f"this operation needs the `{name}` field, holding a wire atom"
        raise MettaError(msg)
    return _atom_from_wire(wire)


def _atoms_of(payload: dict, name: str) -> list[Atom]:
    """The list form, for the bulk door."""
    wires = payload.get(name)
    if not isinstance(wires, list):
        msg = f"this operation needs the `{name}` field, holding a list of wire atoms"
        raise MettaError(
            msg
        )
    return [_atom_from_wire(wire) for wire in wires]


def _bound_of(payload: dict) -> int | None:
    """The caller's answer limit, honored EXACTLY or not at all.

    A batch is a CHUNK and a bound is a CUT, which is why only one of them
    needs a matcher's permission: chunking hands back part of an answer set
    with the rest still reachable, so it is sound whatever a server's match
    does, while truncating an over-approximated candidate list can drop true
    answers past the cut. This server may honor it because its match is real
    unification; health advertises that as `bound`.
    """
    value = payload.get("bound")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        msg = f"bound must be a non-negative integer, got {value!r}"
        raise MettaError(msg)
    return value


@dataclass
class _OpenCursor:
    """One answer stream a gateway holds open between requests."""

    #: The engine resource, closed on release; `answers` is what it answers,
    #: already instantiated and, for a linearised match, already filtered.
    cursor: Cursor
    answers: Iterator[Atom]
    space: str
    remaining: int | None
    deadline: float = 0.0


class _Cursors:
    """A gateway's open cursors, keyed by an unguessable token.

    The token IS the capability, because it is the whole of what /next and
    /stop name, so it is minted from `secrets` rather than counted up. Two
    bounds keep a stateful resource on an open port finite, and pengines
    bounds the same resource the same two ways: a cursor nobody pulls from
    is released after `idle` seconds, and a client that would open more than
    `limit` at once is refused rather than served.

    Every mutation runs on the gateway's own thread. space_of() is the one
    read from elsewhere, serve()'s HTTP threads asking which space a cursor
    belongs to so the authorize hook judges /next and /stop against the
    space the answers come from, so the table is lock-guarded.
    """

    def __init__(self, idle: float, limit: int) -> None:
        self._idle = _server_timeout(idle, "cursor idle deadline")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            msg = f"cursor limit must be a positive integer, got {limit!r}"
            raise ValueError(msg)
        self._limit = limit
        self._lock = threading.Lock()
        self._open: dict[str, _OpenCursor] = {}

    def _sweep(self) -> None:
        """Release every cursor whose deadline has passed, engines and all."""
        now = time.monotonic()
        with self._lock:
            expired = [token for token, e in self._open.items() if e.deadline <= now]
            gone = [self._open.pop(token) for token in expired]
        if gone:
            logger.debug(
                "releasing %d remote cursor(s) idle past %g seconds",
                len(gone),
                self._idle,
            )
        _close_every(gone)

    def open(self, entry: _OpenCursor) -> str:
        self._sweep()
        token = secrets.token_urlsafe(24)
        with self._lock:
            if len(self._open) >= self._limit:
                msg = (
                    f"this gateway already holds {self._limit} answer cursors "
                    f"open; stop one before asking for another, or serve with "
                    f"a larger cursor_limit"
                )
                raise MettaError(
                    msg
                )
            entry.deadline = time.monotonic() + self._idle
            self._open[token] = entry
        return token

    def take(self, token: object) -> _OpenCursor:
        """The cursor a request names, its idle deadline pushed out.

        A token the table does not hold is an ERROR rather than an empty
        answer: answering nothing would say the enumeration ended, and
        under-answering is the one thing this protocol forbids.
        """
        self._sweep()
        if not isinstance(token, str):
            msg = f"cursor must be a string, got {token!r}"
            raise MettaError(msg)
        with self._lock:
            entry = self._open.get(token)
            if entry is not None:
                entry.deadline = time.monotonic() + self._idle
        if entry is None:
            msg = (
                f"no such cursor: it was stopped, it ran out of answers, or it "
                f"went untouched for {self._idle:g} seconds and the gateway "
                f"released it. Ask again for a new one"
            )
            raise MettaError(
                msg
            )
        return entry

    def release(self, token: object) -> bool:
        self._sweep()
        if not isinstance(token, str):
            msg = f"cursor must be a string, got {token!r}"
            raise MettaError(msg)
        with self._lock:
            entry = self._open.pop(token, None)
        if entry is None:
            return False
        entry.cursor.close()
        return True

    def space_of(self, token: object) -> str | None:
        if not isinstance(token, str):
            return None
        with self._lock:
            entry = self._open.get(token)
        return None if entry is None else entry.space

    def close_all(self) -> None:
        with self._lock:
            entries = list(self._open.values())
            self._open.clear()
        _close_every(entries)


def _close_every(entries: list[_OpenCursor]) -> None:
    """Close every cursor, then raise whatever the closes raised.

    The table has already let go of all of them, so stopping at the first
    failure abandons the engines behind the rest with nothing left holding
    their tokens [tested test_closing_every_cursor_survives_one_failure].
    """
    failures: list[BaseException] = []
    for entry in entries:
        try:
            entry.cursor.close()
        except BaseException as exc:  # noqa: BLE001  -- every cursor closes before any failure leaves
            failures.append(exc)
    if failures:
        _raise_failures("releasing remote answer cursors failed", failures)


class Gateway:
    """This engine's spaces as the protocol's server side, transport-free.

    Call it with (operation, payload) and it answers the reply dict, which
    is the shape `Transport` has on the client side, so both halves of the
    wire carry one signature. serve() wraps a Gateway in the bundled HTTP
    server; mount one on the framework a deployment already runs, or call
    it directly, which is how a test watches the engine's own counters
    while the protocol runs, an HTTP server answering on a thread of its
    own.

    A Gateway OWNS the cursors ask/next/stop hold open, so close() it when
    the process is done with it. Server.close() does that for the one
    serve() made.

    It serializes NOTHING of its own: serve() runs every call on one
    attached-engine worker, and a Gateway called directly runs on the
    calling thread, so a caller that shares one across threads owns that
    arrangement.
    """

    def __init__(  # noqa: D107  -- the enclosing class documents construction and the object invariants
        self,
        m,
        spaces: list[str] | None = None,
        *,
        cursor_idle: float = _CURSOR_IDLE,
        cursor_limit: int = _CURSOR_LIMIT,
    ) -> None:
        self._metta = m
        self._allowed = None if spaces is None else set(spaces)
        self._cursors = _Cursors(cursor_idle, cursor_limit)

    def __call__(self, operation: str, payload: dict) -> dict:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        if operation == "match":
            return self._match(payload)
        if operation == "ask":
            return self._ask(payload)
        if operation == "next":
            return self._next(payload)
        if operation == "stop":
            return self._stop(payload)
        if operation == "atoms":
            return {"atoms": _wire(self._space(payload).atoms())}
        if operation == "add":
            self._space(payload).add(_atom_of(payload, "atom"))
            return {"added": True}
        if operation == "add_many":
            atoms = _atoms_of(payload, "atoms")
            self._space(payload).add(*atoms)
            return {"added": len(atoms)}
        if operation == "remove":
            return self._remove(payload)
        if operation == "health":
            return self._health()
        msg = f"unknown operation {operation!r}"
        raise MettaError(msg)

    def health(self) -> dict:
        """The transport-side spelling of GET /health, so a Gateway is a
        drop-in Transport and RemoteSpace.server_capabilities() can ask
        one the same question it asks a connected server.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return self._health()

    def cursor_space(self, token: object) -> str | None:
        """Which space an open cursor's answers come from, so a transport
        can hand its authorization hook the space /next and /stop are
        really about; None once the cursor is gone.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return self._cursors.space_of(token)

    def close(self) -> None:
        """Release every cursor still open, and the engine behind each."""
        self._cursors.close_all()

    # ------------------------------------------------------------ operations

    def _space(self, payload: dict) -> MeTTa:
        name = payload.get("space", self._metta.name)
        if self._allowed is not None and name not in self._allowed:
            msg = f"space {name!r} is not served"
            raise MettaError(msg)
        return (
            self._metta
            if name == self._metta.name
            else MeTTa(name, _runtime=self._metta.runtime)
        )

    def _match(self, payload: dict) -> dict:
        """The eager door: one reply carrying the whole answer set.

        match()'s reading on the wire, and it costs what match() costs, the
        join computed to the end before anything crosses. /ask is the other
        door, and both take their candidates from _candidates, so the two
        answer the same set for every pattern.
        """
        space = self._space(payload)
        pattern = _atom_of(payload, "pattern")
        bound = _bound_of(payload)
        if bound == 0:
            # Zero answers wanted: the engine's query refuses a zero
            # limit, and no work is the exact honoring.
            return {"atoms": []}
        if _linear(pattern) is not None:
            # A repeated variable can make an instantiation infinite, so this
            # pattern's candidates come through the linearised cursor whether
            # the caller asked for all of them or a bounded page.
            cursor, answers = self._candidates(space, pattern)
            try:
                atoms = list(answers if bound is None else islice(answers, bound))
            finally:
                cursor.close()
            return {"atoms": _wire(atoms)}
        if bound is not None:
            rows = space.match(pattern, limit=bound)
            atoms = [
                substitute(pattern, dict(zip(rows.columns, row, strict=True)))
                for row in rows
            ]
            return {"atoms": _wire(atoms)}
        return {"atoms": _wire(self._collapsed(space, pattern))}

    def _collapsed(self, space: MeTTa, pattern: Atom) -> list[Atom]:
        """One engine-side match, collapsed to the instantiations it answers.

        The whole answer set in ONE crossing, which is what makes the eager
        door eager; the lazy door pays a crossing per chunk instead.
        """
        with space.bind(pat=pattern):
            groups = space.run("!(collapse (match (context-space) pat pat))")
        if len(groups) != 1 or len(groups[0]) != 1:
            msg = f"remote match returned an invalid collapse result: {groups!r}"
            raise MettaError(msg)
        group = groups[0][0]
        if not isinstance(group, Expression):
            msg = f"remote match returned a non-expression collapse: {group!r}"
            raise MettaError(msg)
        return list(group)

    def _candidates(self, space: MeTTa, pattern: Atom) -> tuple[Cursor, Iterator[Atom]]:
        """The engine cursor a pattern's candidates come from.

        The second answer is the atoms that cursor makes.

        Candidates cross as the pattern instantiated by each match. Matching
        binds raw, so a repeated pattern variable can bind to a term that
        contains it: that candidate IS an answer this server owes and no
        finite tagged form spells its instantiation. Such a pattern is
        therefore matched LINEARISED, which answers the stored atom rather
        than an instantiation of it, the other form the protocol allows, and
        the engine's own re-unification filters the relaxed answer back to the
        candidates this pattern really joins, so the reply stays exact
        [source: website/live/remote-protocol.md, the rational-tree paragraph;
        tested test_a_rational_tree_candidate_crosses_as_the_stored_atom].
        """
        linear = _linear(pattern)
        template = pattern if linear is None else linear
        cursor = space.stream(template)
        answers = (
            substitute(template, dict(zip(cursor.columns, row, strict=True)))
            for row in cursor
        )
        if linear is None:
            return cursor, answers
        return cursor, (
            atom for atom in answers if unify(pattern, _apart(atom)) is not None
        )

    def _pull(self, entry: _OpenCursor, batch: int) -> tuple[list[Atom], bool]:
        """Take at most `batch` answers, and not one more.

        A SHORT batch is the whole of the exhaustion signal, so nothing here
        looks ahead: the answer after the last one a client asked for is
        never computed, which is what makes taking two answers of a large
        enumeration cost two answers' work
        [tested test_two_answers_cross_the_wire_without_the_third_being_computed].
        """
        want = batch if entry.remaining is None else min(batch, entry.remaining)
        atoms = list(islice(entry.answers, want))
        if entry.remaining is not None:
            entry.remaining -= len(atoms)
        return atoms, len(atoms) < want or entry.remaining == 0

    def _reply(self, atoms: list[Atom], token: str | None) -> dict:
        return {"atoms": _wire(atoms), "cursor": token}

    def _ask(self, payload: dict) -> dict:
        """The lazy door: open a cursor and answer its first chunk.

        stream()'s reading on the wire. The reply's `cursor` is the
        continuation and doubles as the more-flag, because a finished
        stream is one the gateway has already released and answers null
        for, so no boolean has to be computed from a lookahead answer.
        """
        space = self._space(payload)
        pattern = _atom_of(payload, "pattern")
        batch = _batch_of(payload)
        bound = _bound_of(payload)
        if bound == 0:
            return self._reply([], None)
        entry = _OpenCursor(*self._candidates(space, pattern), space.name, bound)
        try:
            atoms, done = self._pull(entry, batch)
            token = None if done else self._cursors.open(entry)
        except BaseException:
            entry.cursor.close()
            raise
        if done:
            entry.cursor.close()
        return self._reply(atoms, token)

    def _next(self, payload: dict) -> dict:
        token = payload.get("cursor")
        entry = self._cursors.take(token)
        batch = _batch_of(payload)
        try:
            atoms, done = self._pull(entry, batch)
        except BaseException:
            self._cursors.release(token)
            raise
        if done:
            self._cursors.release(token)
        return self._reply(atoms, None if done else token)

    def _stop(self, payload: dict) -> dict:
        """Release a cursor early. Answering whether there was one to
        release is the honest reply to a call a client makes from a
        finally-block, where the stream may already have ended.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return {"stopped": self._cursors.release(payload.get("cursor"))}

    def _remove(self, payload: dict) -> dict:
        pattern = _atom_of(payload, "atom")
        if not isinstance(pattern, (Expression, Variable)):
            # A stored atom is always an expression; a symbol or a
            # grounded value can unify with none of them.
            return {"removed": False}
        # A bare variable is the remove-everything reading, and the
        # engine owns it now, each atom leaving through its own path.
        return {"removed": self._space(payload).remove(pattern)}

    def _health(self) -> dict:
        return {
            "ok": True,
            "atoms": len(self._metta),
            "protocol": 3,
            # The reflection the in-process seam has: what this server
            # admits, so a client can ask before writing.
            # add-many is the registry's own hyphenated spelling
            # (foreign.CAPABILITIES); the WIRE verb stays /add_many.
            "capabilities": ["match", "enumerate", "add", "add-many", "remove", "stream"],
            # /match and /ask honor the optional bound field exactly.
            "bound": True,
        }


@dataclass
class _RemoteRequest:
    """One worker request and the caller-owned channel for its outcome."""

    operation: str
    payload: dict
    reply: queue.SimpleQueue
    abandoned: threading.Event
    interrupted: bool = False


class _RemoteWorker:
    """One attached Prolog engine serving serialized remote requests."""

    def __init__(self, handle: Callable[[str, dict], dict]) -> None:
        self._handle = handle
        self._lock = threading.Lock()
        self._transition = threading.Lock()
        self._started: queue.Queue[BaseException | None] = queue.Queue(maxsize=1)
        self._state = "unstarted"
        self._failures: list[BaseException] = []
        self._current: _RemoteRequest | None = None
        self._swi_thread: Any = None
        self._work: queue.Queue[_RemoteRequest | None] = queue.Queue()
        self.thread = threading.Thread(
            target=self._run,
            name="metta-remote-engine",
            daemon=True,
        )

    def start(self, timeout: float = _SERVER_TIMEOUT) -> None:
        timeout = _server_timeout(timeout)
        with self._lock:
            if self._state != "unstarted":
                msg = f"remote engine worker is {self._state}"
                raise RuntimeError(msg)
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
            msg = f"remote engine worker could not attach: {type(failure).__name__}: {failure}"
            raise MettaError(
                msg
            ) from failure
        with self._lock:
            if self._state == "starting":
                self._state = "live"

    def call(self, operation: str, payload: dict, timeout: float) -> tuple[str, Any]:
        with self._lock:
            if self._state != "live" or not self.thread.is_alive():
                msg = f"remote engine worker is {self._state}"
                raise MettaError(msg)
            reply: queue.SimpleQueue = queue.SimpleQueue()
            request = _RemoteRequest(
                operation,
                payload,
                reply,
                threading.Event(),
            )
            self._work.put(request)
        try:
            return reply.get(timeout=timeout)
        except queue.Empty as exc:
            request.abandoned.set()
            try:
                self._interrupt_if_running(request)
            except BaseException as cancellation_error:  # noqa: BLE001 -- a failed cancellation leaves an operation whose outcome is unknown
                timed_out = TimeoutError(
                    f"remote engine operation {operation!r} did not finish "
                    f"within {timeout:g} seconds"
                )
                timed_out.__cause__ = exc
                cancellation_message = (
                    "the remote engine operation timed out and could not be cancelled"
                )
                raise BaseExceptionGroup(
                    cancellation_message,
                    [timed_out, cancellation_error],
                ) from None
            msg = f"remote engine operation {operation!r} did not finish within {timeout:g} seconds"
            raise TimeoutError(
                msg
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
            msg = "a remote engine worker cannot stop itself"
            raise MettaError(msg)
        if thread.is_alive():
            thread.join(timeout)
        if thread.is_alive():
            msg = f"remote engine worker did not stop within {timeout:g} seconds"
            raise TimeoutError(msg)
        with self._lock:
            failures = tuple(self._failures)
            self._state = "closed"
        if report_failure and failures:
            if len(failures) == 1:
                failure = failures[0]
                msg = f"remote engine worker failed: {type(failure).__name__}: {failure}"
                raise MettaError(
                    msg
                ) from failure
            msg = "remote engine worker failed"
            raise BaseExceptionGroup(msg, list(failures))

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
                    item.abandoned.set()
                    pending.append(item.reply)
        for reply in pending:
            reply.put(("error", f"{type(failure).__name__}: {failure}"))
        if pending:
            logger.error("rejected %d queued remote request(s)", len(pending))

    def _run(self) -> None:
        try:
            janus = bridge()
            janus.attach_engine()
            with self._lock:
                self._swi_thread = janus.engine()
        except BaseException as exc:  # noqa: BLE001
            self._record_failure(exc)
            self._started.put(exc)
            return
        self._started.put(None)
        logger.debug("remote engine server worker attached a Prolog engine")
        try:
            self._work_loop()
        except BaseException as exc:  # noqa: BLE001
            self._fail_running(exc)
        finally:
            try:
                janus.detach_engine()
            except BaseException as exc:  # noqa: BLE001
                self._record_failure(exc)
            else:
                logger.debug("remote engine server worker detached its Prolog engine")
            finally:
                with self._lock:
                    self._swi_thread = None

    def _drain(self) -> None:
        """Consume only a stale cancellation signal before later work."""
        janus = bridge()
        try:
            janus.query_once("true")
        except janus.PrologError as exc:
            try:
                runtime()._raise(exc)
            except Interrupted:
                logger.debug("discarded a stale remote-worker interrupt: %s", exc)

    def _interrupt_if_running(self, request: _RemoteRequest) -> bool:
        """Interrupt only ``request`` when it has started running."""
        with self._lock:
            swi_thread = self._swi_thread
        with self._transition:
            if self._current is not request:
                return False
            if swi_thread is None:
                msg = "the remote worker has a request but no published Prolog engine"
                raise RuntimeError(msg)
            # This is AsyncMeTTa's cancellation protocol: signal the exact
            # attached engine, then drain a signal that raced completion
            # before starting another request [source:
            # extensions/python/metta/aio.py,
            # _EngineThread.interrupt_if_running;
            # commit=076eade6b1fe254379b2ae0f11ff56f36b4af1e4].
            request.interrupted = True
            bridge().query_once(
                "thread_signal(T, throw(error(metta_control_signal(interrupted, none), "
                "context(metta, interrupted))))",
                {"T": swi_thread},
            )
            logger.debug("sent an interrupt to the remote engine worker")
            return True

    def _work_loop(self) -> None:
        """Serve one request at a time until asked to stop."""
        while True:
            item = self._work.get()
            if item is None:
                return
            request = item
            with self._transition:
                if request.abandoned.is_set():
                    continue
                self._current = request
            fatal: BaseException | None = None
            outcome: tuple[str, Any]
            try:
                outcome = ("ok", self._handle(request.operation, request.payload))
            except Exception as exc:
                logger.warning(
                    "remote engine operation %s failed",
                    request.operation,
                    exc_info=True,
                )
                outcome = ("error", str(exc))
            except BaseException as exc:  # noqa: BLE001
                outcome = ("error", str(exc))
                fatal = exc
            with self._transition:
                self._current = None
                try:
                    if request.interrupted:
                        self._drain()
                except BaseException as exc:  # noqa: BLE001 -- an unexpected transition failure poisons the worker
                    fatal = (
                        exc
                        if fatal is None
                        else BaseExceptionGroup(
                            "the remote request and its transition drain both failed",
                            [fatal, exc],
                        )
                    )
                    outcome = ("error", str(fatal))
                if not request.abandoned.is_set():
                    request.reply.put(outcome)
            if fatal is not None:
                self._fail_running(fatal)
                return


class Server:
    """This engine's spaces, served. close() stops accepting.

    A context manager, because it owns a socket, an accept thread and an
    engine worker, which is more than any other handle in this library and
    exactly the shape Python spells `with`. `metta.space()` and
    `metta.aio.connect()` are already `with`-able; a server that had to be
    closed by hand was the one resource whose leak on an exception path was
    silent.
    """

    def __init__(  # noqa: D107  -- the enclosing class documents construction and the object invariants
        self,
        httpd: ThreadingHTTPServer,
        thread: threading.Thread,
        worker: _RemoteWorker,
        gateway: Gateway,
        scheme: str = "http",
    ) -> None:
        self._httpd = httpd
        self._thread = thread
        self._worker = worker
        self._gateway = gateway
        self._close_lock = threading.Lock()
        self._closed = False
        raw_host, self.port = httpd.server_address[:2]
        self.host = raw_host.decode("ascii") if isinstance(raw_host, bytes) else raw_host
        self.url = f"{scheme}://{self.host}:{self.port}"
        # attach() reads this to refuse the one configuration that cannot
        # work, so the entry has to exist for as long as the socket does.
        # str(): server_address carries bytes on some families, and the
        # registry key is a str address.
        self._address = (str(self.host), self.port)
        with _LIVE_SERVERS_LOCK:
            _LIVE_SERVERS[self._address] = tuple(sorted(gateway._allowed or ()))

    def __enter__(self) -> Self:
        """The server itself, so `with serve(m) as server:` names it."""
        return self

    def __exit__(self, *_exception: object) -> None:
        """Close on the way out, on the exception path too."""
        self.close()

    def close(self, timeout: float = _SERVER_TIMEOUT) -> None:
        """Stop accepting, detach the engine worker, join both threads, and
        release every answer cursor a client left open.

        The cursors go LAST, once nothing can pull from them: each holds an
        engine, and a client that walked away from a stream would otherwise
        leave one behind until the idle deadline that no longer has a server
        to fire on.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        timeout = _server_timeout(timeout)
        with self._close_lock:
            if self._closed:
                return
            if self._thread is threading.current_thread():
                msg = "the remote HTTP server cannot close itself"
                raise MettaError(msg)
            failures = self._stop_http(timeout)
            stopped_serving = not failures
            failures.extend(self._stop_worker(timeout))
            if self._worker.thread.is_alive():
                # Each cursor holds an engine the worker may be inside right
                # now, so releasing them here would close one out from under a
                # running request. They keep their idle deadline instead, and
                # a later close() releases them once the worker is gone
                # [tested test_a_close_that_cannot_stop_the_worker_keeps_the_cursors].
                failures.append(
                    MettaError(
                        "the remote engine worker did not stop, so the answer "
                        "cursors it may still be reading were left open rather "
                        "than closed under it; close() again once the worker "
                        "has stopped"
                    )
                )
            else:
                try:
                    self._gateway.close()
                except BaseException as exc:  # noqa: BLE001
                    failures.append(exc)
            self._closed = not self._thread.is_alive() and not self._worker.thread.is_alive()
            if stopped_serving or self._closed:
                # The socket is gone, so nothing reaches this server through
                # it any more. Until it is, the entry stays: the deadlock
                # guard reads it to refuse an attach that would hang, and a
                # close that failed leaves a server that may still answer.
                with _LIVE_SERVERS_LOCK:
                    _LIVE_SERVERS.pop(self._address, None)
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


def serve(
    m,
    host: str = "127.0.0.1",
    port: int = 0,
    spaces: list[str] | None = None,
    *,
    token: str | None = None,
    authorize: Callable[[Request], bool] | None = None,
    ssl_context: Any = None,
    cursor_idle: float = _CURSOR_IDLE,
    cursor_limit: int = _CURSOR_LIMIT,
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

    `cursor_idle` and `cursor_limit` bound the ask/next/stop lifecycle's
    server-side state: how long a cursor nobody pulls from survives, and
    how many live at once before a further ask is refused. The defaults
    are pengines' own, 300 seconds and a ceiling.

    A context is a PROCESS: serving and attaching within one process
    cannot join through the local engine, because one runtime lock guards
    both sides of that call and the serving thread would wait on the very
    evaluation that is waiting on it. Two engines, two processes, is the
    deployment this exists for; in-process, spaces already share the
    engine and need no wire. Gateway is the same protocol with no
    transport under it, for a test or a framework that wants the
    operations without a socket.
    """
    gateway = Gateway(m, spaces, cursor_idle=cursor_idle, cursor_limit=cursor_limit)

    # Every engine call runs on one persistent attached-engine worker.
    worker = _RemoteWorker(gateway)

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

        def _space_named(self, operation: str, payload: dict) -> str:
            """Which space this request is about, for the authorize hook.

            /next and /stop carry a cursor rather than a space, and reading
            the default out of the absent field would hand a read-only or
            per-tenant policy the WRONG space to judge: the answers come
            from wherever the /ask that opened the cursor pointed. So the
            gateway is asked which space the cursor belongs to, and a
            cursor it no longer holds falls back to the default, where the
            operation refuses itself anyway.
            """
            if operation in ("next", "stop"):
                held = gateway.cursor_space(payload.get("cursor"))
                if held is not None:
                    return held
            return str(payload.get("space", m.name))

        def do_GET(self) -> None:
            operation = self.path.strip("/")
            headers = self._collected_headers()
            # The same gates as every POST, credential then policy hook:
            # health names what the server admits, which is not an
            # anonymous answer when a token or a policy is configured.
            if not _has_credential(headers, token):
                self._refuse_unauthorized(operation)
                return
            # The policy hook runs INSIDE the boundary: an authorize that
            # raises used to leave do_GET through socketserver, which drops
            # the connection and answers the client nothing
            # [tested test_a_failing_authorize_hook_answers_json_on_health].
            try:
                request = Request(operation, m.name, headers)
                if authorize is not None and not authorize(request):
                    self._refuse_unauthorized(operation)
                    return
                if operation == "health":
                    kind, value = worker.call("health", {}, timeout=600.0)
                    answer = value if kind == "ok" else {"error": value}
                    status = 200 if kind == "ok" else 400
                else:
                    answer, status = {"error": f"unknown operation {operation!r}"}, 400
            except _HTTPProblem as exc:
                answer, status = {"error": str(exc)}, exc.status
            except Exception as exc:  # the wire answers errors as JSON
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

        do_PUT = _method_not_allowed  # noqa: N815  -- BaseHTTPRequestHandler dispatch requires the exact do_METHOD attribute spelling
        do_DELETE = _method_not_allowed  # noqa: N815  -- BaseHTTPRequestHandler dispatch requires the exact do_METHOD attribute spelling
        do_PATCH = _method_not_allowed  # noqa: N815  -- BaseHTTPRequestHandler dispatch requires the exact do_METHOD attribute spelling

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
                request = Request(operation, self._space_named(operation, payload), headers)
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

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 -- BaseHTTPRequestHandler fixes the keyword-capable override parameter name
            logger.debug("remote HTTP: " + format, *args)

    httpd = ThreadingHTTPServer((host, port), Handler)
    # Handler threads are request-scoped. Server.close bounds the owned HTTP
    # loop and engine worker instead of inheriting a process-exit wait here.
    httpd.daemon_threads = True
    thread = threading.Thread(
        target=httpd.serve_forever,
        name="metta-remote-http",
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
            gateway,
            scheme="https" if ssl_context else "http",
        )
    except BaseException as start_error:
        cleanup_failures: list[BaseException] = []
        try:
            gateway.close()
        except BaseException as exc:  # noqa: BLE001
            cleanup_failures.append(exc)
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
            msg = "remote server startup and cleanup failed"
            raise BaseExceptionGroup(
                msg,
                [start_error, *cleanup_failures],
            ) from None
        raise
    logger.debug("started remote engine server on %s", server.url)
    return server
