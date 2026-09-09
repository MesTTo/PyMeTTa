"""Purpose: serve spaces through retained cursors, HTTP threads and engine workers.

Owns resources: Server.close stops the HTTP server and its engine worker;
Gateway.close releases retained cursors
[source: extensions/python/metta/remote/_gateway.py:1464, Gateway.close; commit=WORKTREE].
Guarded by: _Cursors._lock protects cursor retention, _RemoteWorker._lock
protects worker state, and Server._close_lock serializes shutdown
[source: extensions/python/metta/remote/_gateway.py:412,
_RemoteWorker.__init__, Server.__init__; commit=WORKTREE].
"""

from __future__ import annotations

import hashlib
import heapq
import hmac
import logging
import math
import queue
import secrets
import threading
import time
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from itertools import islice
from typing import Any, NamedTuple, Self

import metta._binding.json as _json
import metta._catalog.arrow as _arrow
import metta._catalog.types as _projection
from metta._atoms.designation import space_of
from metta._atoms.factories import Atom, Expression, Symbol, Variable, parse, substitute, unify
from metta._atoms.wire import _atom_from_wire
from metta._binding.runtime import bridge, runtime
from metta._catalog.declarations import declared
from metta._errors.errors import Interrupted, MettaError
from metta._faces.space import Space as MeTTa
from metta._spaces.cursor import Cursor
from metta.remote import _schemas
from metta.remote._defaults import (
    _CURSOR_IDLE,
    _CURSOR_LIMIT,
    _DEFAULT_BATCH,
    _MAX_REQUEST_BYTES,
    _MUTATION_LIMIT,
    _MUTATION_TTL,
    _SERVER_TIMEOUT,
)
from metta.remote._transport import (
    _LIVE_SERVERS,
    _LIVE_SERVERS_LOCK,
    _MUTATIONS,
    _raise_failures,
    _server_timeout,
)

logger = logging.getLogger(__name__)

_GET_OPERATIONS = {"openapi.json": "openapi", "graphql": "graphql_schema"}

_DOCUMENTS = {
    "openapi": "application/json",
    "graphql_schema": "text/plain; charset=utf-8",
}

_Reply = tuple[int, bytes, str, "Mapping[str, str]"]

def _refusal(status: int, message: str) -> _Reply:
    """A refusal, which is JSON whichever representation was asked for.

    A client that cannot have what it asked for needs the sentence rather than
    an empty body of the type it wanted.
    """
    return status, _json.dumps({"error": message}), "application/json", _NO_HEADERS

def _post_reply(worker: _RemoteWorker, operation: str, payload: dict) -> _Reply:
    """What a POST answers, in the representation the request asked for."""
    answer, status = _worker_response(worker, operation, payload)
    streamed = _arrow_response(answer, status)
    if streamed is not None:
        return streamed
    return status, _json.dumps(answer), "application/json", _NO_HEADERS

def _get_reply(
    worker: _RemoteWorker, operation: str, *, secured: bool
) -> _Reply:
    """What a GET answers: a status, a body and the media type it reads as.

    Through the worker like every other engine call, because health counts the
    engine's atoms and a document reads the served spaces' declarations.
    """
    if operation == "health":
        answer, status = _worker_response(worker, "health", {})
        return status, _json.dumps(answer), "application/json", _NO_HEADERS
    if operation not in _DOCUMENTS:
        return _refusal(400, f"unknown operation {operation!r}")
    payload = {"secured": secured} if operation == "openapi" else {}
    answer, status = _worker_response(worker, operation, payload)
    if status != 200:
        return _refusal(status, str(answer.get("error", "")))
    if operation == "graphql_schema":
        return status, answer["schema"].encode("utf-8"), _DOCUMENTS[operation], _NO_HEADERS
    return status, _json.dumps(answer), _DOCUMENTS[operation], _NO_HEADERS

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

    Both response paths name them the same way, so the eager reply and the
    chunks of the lazy one are the same atoms rather than the same atoms under
    two spellings, and one stored atom read twice is one atom.
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
    """The list form, for the bulk request."""
    wires = payload.get(name)
    if not isinstance(wires, list):
        msg = f"this operation needs the `{name}` field, holding a list of wire atoms"
        raise MettaError(
            msg
        )
    return [_atom_from_wire(wire) for wire in wires]

_NO_HEADERS: Mapping[str, str] = {}

def _wants_arrow(headers: Mapping[str, str]) -> bool:
    """Whether an Accept header asks for the Arrow IPC streaming format.

    One media type, matched exactly among the header's comma-separated members
    with their q-parameters dropped; a request that offers it alongside JSON
    gets Arrow, which is the reading that makes `Accept: <arrow>, */*` work.
    """
    offered = headers.get("accept", "")
    return any(
        member.split(";")[0].strip() == _arrow.IPC_MEDIA_TYPE
        for member in offered.split(",")
    )

def _requested(operation: str, headers: Mapping[str, str], payload: dict) -> dict:
    """The payload a POST really asks for, once its Accept header is read.

    The Accept header is HTTP's own way of asking for a representation, and it
    sets the same `format` field a direct Gateway caller sets, so the two halves
    of the wire ask for Arrow in one vocabulary. Only the two streaming
    operations answer it; nothing else has rows to put in a batch.
    """
    if operation not in ("ask", "next") or not _wants_arrow(headers):
        return payload
    return {**payload, "format": "arrow"}

def _arrow_response(answer: dict, status: int) -> _Reply | None:
    """An Arrow reply as its status, bytes, media type and headers, or None.

    The cursor token rides in a header because an IPC stream has nowhere to
    carry one, and its absence is the end of the stream, exactly as a null
    `cursor` is in the JSON reply.
    """
    if status != 200 or not isinstance(answer.get("arrow"), bytes):
        return None
    token = answer["cursor"]
    return (
        status,
        answer["arrow"],
        _arrow.IPC_MEDIA_TYPE,
        {} if token is None else {"x-metta-cursor": token},
    )

def _arrow_of(payload: dict) -> bool:
    """Whether this request asked for its answers as an Arrow IPC stream.

    A `format` field rather than a second operation word, so the nine operations
    stay nine and a Gateway called directly can ask for the same bytes the HTTP
    Accept header asks for. Any other value is refused rather than treated as
    JSON: a client that asked for something is owed that or a sentence.
    """
    asked = payload.get("format")
    if asked is None or asked == "json":
        return False
    if asked == "arrow":
        return True
    msg = f"format must be 'json' or 'arrow', got {asked!r}"
    raise MettaError(msg)

def _arrow_chunk(entry: _OpenCursor, answers: list[_Candidate]) -> bytes:
    """One chunk of a cursor as a complete Arrow IPC stream.

    The columns are the cursor's own variables, each produced at the kind the
    schema fixed, then `atom`. `values_of` is `_arrow`'s door for a kind a
    CONSUMER asked for, and a declared column is exactly that: a cell the kind
    cannot hold answers null there and stays exact in `atom`.
    """
    cells = tuple(zip(*(answer.cells for answer in answers), strict=True)) if answers else ()
    columns = [
        _arrow.values_of(cells[index] if index < len(cells) else (), kind)
        for index, kind in enumerate(entry.kinds)
    ]
    columns.append([str(answer.atom) for answer in answers])
    return _arrow.ipc_stream(entry.schema, columns)

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

class _Candidate(NamedTuple):
    """One answer, in both the shapes a reply is built from.

    `atom` is the instantiated pattern the JSON reply carries; `cells` are the
    bindings behind it, in the cursor's own column order, which is what an Arrow
    batch's columns hold; `annotation` is the algebra tag a cursor under an
    ambient carrier answers beside each row, and None otherwise.
    """

    atom: Atom
    cells: tuple[Any, ...]
    annotation: Atom | None

@dataclass
class _OpenCursor:
    """One answer stream a gateway holds open between requests."""

    #: The engine resource, closed on release; `answers` is what it answers,
    #: already instantiated and, for a linearised match, already filtered.
    cursor: Cursor
    answers: Iterator[_Candidate]
    space: str
    remaining: int | None
    #: The Arrow schema every chunk of THIS stream is written at, built once
    #: when the cursor opens. An IPC stream has one schema for every batch, so
    #: it cannot be derived per chunk from the cells that chunk happened to
    #: hold; it is derived from what the space DECLARES, and a column nothing
    #: declares is canonical MeTTa text, which every atom can be written as.
    #: None until an Arrow reply asks for it, so a JSON-only stream pays
    #: nothing. `kinds` is the same decision as `_arrow`'s own kind words, one
    #: per pattern variable, which is what each chunk's cells are produced at.
    schema: Any = None
    kinds: tuple[str, ...] = ()
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
        except BaseException as exc:  # noqa: BLE001
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

    Keyed mutations retain their acknowledgements for mutation_ttl seconds
    (300 by default), up to mutation_limit entries (4096). Full ledgers refuse
    new keys before execution. Expired keys and keys for another gateway
    instance refuse instead of becoming new writes. The ledger is in memory;
    restarting a gateway requires reconciling outstanding unknown outcomes.

    A Gateway OWNS the cursors ask/next/stop hold open, so close() it when
    the process is done with it. Server.close() does that for the one
    serve() made.

    It serializes NOTHING of its own: serve() runs every call on one
    attached-engine worker, and a Gateway called directly runs on the
    calling thread, so a caller that shares one across threads owns that
    arrangement.

    m may be a context or a space; the gateway serves the space either way.
    """

    def __init__(
        self,
        m,
        spaces: list[str] | None = None,
        *,
        cursor_idle: float = _CURSOR_IDLE,
        cursor_limit: int = _CURSOR_LIMIT,
        mutation_ttl: float = _MUTATION_TTL,
        mutation_limit: int = _MUTATION_LIMIT,
    ) -> None:
        self._mutation_ttl = _server_timeout(mutation_ttl, "mutation retention")
        if type(mutation_limit) is not int or mutation_limit < 1:
            msg = "mutation_limit must be a positive integer"
            raise ValueError(msg)
        self._mutation_limit = mutation_limit
        self._mutation_scope = secrets.token_urlsafe(24)
        self._mutations: dict[str, tuple[float, bytes, dict]] = {}
        self._mutation_expiries: list[tuple[float, str]] = []
        self._metta = space_of(m)
        self._allowed = None if spaces is None else set(spaces)
        self._cursors = _Cursors(cursor_idle, cursor_limit)

    def __call__(self, operation: str, payload: dict) -> dict:
        if operation in _MUTATIONS and "idempotency" in payload:
            return self._mutate(operation, payload)
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
        if operation == "openapi":
            return self.openapi(secured=bool(payload.get("secured")))
        if operation == "graphql_schema":
            return {"schema": self.graphql_schema()}
        if operation == "graphql":
            return self.graphql(payload)
        msg = f"unknown operation {operation!r}"
        raise MettaError(msg)

    def _idempotency_token_is_live(self, token: object, now: float) -> bool:
        """A token this gateway minted, unexpired, with a key of wire-legal length.

        The seven conditions are one question, is this OUR live token, and each
        rejects a distinct way a replay can be wrong: not a dict, no string key,
        a key outside 1..255, another gateway's scope, a non-numeric or
        non-finite expiry, or an expiry outside (now, now + ttl].
        """
        if not isinstance(token, dict) or not isinstance(token.get("key"), str):
            return False
        if not 1 <= len(token["key"]) <= 255 or token.get("scope") != self._mutation_scope:
            return False
        expires = token.get("expires")
        # isinstance narrows for the type checker where `type(x) in (...)` does
        # not; bool is excluded by name because it is an int to isinstance.
        if isinstance(expires, bool) or not isinstance(expires, (int, float)):
            return False
        if not math.isfinite(expires):
            return False
        return now < expires <= now + self._mutation_ttl

    def _mutate(self, operation: str, payload: dict) -> dict:
        token = payload["idempotency"]
        now = time.monotonic()
        if not self._idempotency_token_is_live(token, now):
            msg = "invalid or expired idempotency key, or gateway instance changed"
            raise MettaError(msg)
        # Resolve authorization before replay, including direct Gateway callers.
        space = self._space(payload)
        digest = hashlib.sha256(_json.dumps([
            operation, str(space.name), payload.get("atom"), payload.get("atoms"),
            token["expires"],
        ])).digest()
        while self._mutation_expiries and self._mutation_expiries[0][0] <= now:
            _, expired = heapq.heappop(self._mutation_expiries)
            del self._mutations[expired]
        key = token["key"]
        held = self._mutations.get(key)
        if held is not None:
            if held[1] != digest:
                msg = "idempotency key reused with different parameters"
                raise MettaError(msg)
            return dict(held[2])
        if len(self._mutations) >= self._mutation_limit:
            msg = "mutation replay capacity reached; wait for expiry or increase mutation_limit"
            raise MettaError(msg)
        # Reserve before execution. Reentrancy or a partially applied provider
        # failure must never create an opportunity to execute this key twice.
        answer = {"error": "mutation did not complete", "outcome": "unknown"}
        reservation = (token["expires"], digest, answer)
        self._mutations[key] = reservation
        heapq.heappush(self._mutation_expiries, (token["expires"], key))
        request = {name: value for name, value in payload.items() if name != "idempotency"}
        try:
            answer = self(operation, request)
        except Exception as exc:  # noqa: BLE001 -- provider failures may follow partial effects
            answer = {"error": str(exc), "outcome": "unknown"}
        # Reentrant work may expire and prune this reservation before return.
        # A late completion may only update the entry it still owns.
        if self._mutations.get(key) is reservation:
            self._mutations[key] = (token["expires"], digest, dict(answer))
        return answer

    def health(self) -> dict:
        """The transport-side spelling of GET /health, so a Gateway is a
        drop-in Transport and RemoteSpace.server_capabilities() can ask
        one the same question it asks a connected server.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return self._health()

    def served(self) -> dict[str, MeTTa]:
        """Every space this gateway serves, by the name a request calls it.

        A gateway built with no `spaces` list serves one, the space it was made
        from; a list names them, and each is opened on the same runtime, which
        is what `_space` does for a request.
        """
        names = [self._metta.name] if self._allowed is None else sorted(self._allowed)
        return {
            name: (
                self._metta
                if name == self._metta.name
                else MeTTa(name, _runtime=self._metta.runtime)
            )
            for name in names
        }

    def openapi(self, *, secured: bool = False) -> dict:
        """This gateway as an OpenAPI 3.1.1 document, `GET /openapi.json`.

            print(metta._binding.json.dumps(gateway.openapi()))

        One path per door, `components.schemas.Atom` as the wire's own tagged
        grammar, and `x-metta-heads` listing what each served space DECLARES,
        with every argument's and result's JSON Schema from the one type table.
        A space that declares nothing publishes an empty list of heads.

        `secured` puts the bearer scheme in the document, and `serve()` sets it
        from its own token: a gateway is transport-free and knows nothing about
        credentials, so the half that holds them is the half that says so.

        Cost: one indexed read of each served space's `(: ...)` rows and one
        `get-doc` per declared head, which is O(declarations) rather than
        O(atoms) and is why this is derived per request instead of cached.
        """
        return _schemas.openapi_document(self.served(), secured=secured)

    def graphql_schema(self) -> str:
        """This gateway's served spaces as GraphQL SDL, `GET /graphql`.

            print(gateway.graphql_schema())

        `scalar Atom` carries any atom as the canonical MeTTa text `parse` reads
        back and `scalar Number` carries a MeTTa number, which no built-in
        GraphQL scalar can. `Query.match` reaches every atom whatever a space
        declares; each DECLARED head gains a field of its own answering typed
        rows, whose fields are `x1..xn` because a `(@param ...)` row carries a
        type and a description and never a name.

        The text is built here, so a server publishes its schema whether or not
        graphql-core is installed; only `graphql()` needs the package. A head
        GraphQL cannot name is in the OpenAPI document's `x-metta-unnameable`
        with the door that still reaches it.
        """
        return _schemas.graphql_sdl(self.served())

    def graphql(self, request: dict) -> dict:
        """Execute one GraphQL request, `POST /graphql`.

            gateway.graphql({"query": "{ users { x1 x2 } }"})

        The request is GraphQL over HTTP's own shape -- `query`, `variables`
        and `operationName` -- and the answer is its `data` and `errors`.
        Resolution goes through the same doors the wire operations use, so a
        `match` query answers what `Gateway("match")` answers for the same
        pattern. Refuses with the install guidance when graphql-core is absent.
        """
        spaces = self.served()
        schema = _schemas.build_graphql_schema(_schemas.graphql_sdl(spaces))
        return _schemas.execute_graphql(schema, self._resolvers(spaces), request)

    def _resolvers(self, spaces: dict[str, MeTTa]) -> dict:
        """The root object a GraphQL query resolves against.

        graphql-core's default field resolver reads a field's name off a Mapping
        and calls what it finds with `(info, **arguments)`
        [source: https://github.com/graphql-python/graphql-core,
        `default_field_resolver`], so the root is this dict and every field is
        one closure.
        """
        root: dict[str, Any] = {
            "match": self._resolve_match,
            "add": self._resolve_add,
            "remove": self._resolve_remove,
        }
        for head in _schemas.graphql_heads(spaces):
            root[head.name] = self._head_resolver(head)
        return root

    def _resolve_match(
        self, _info: Any, pattern: str, limit: int | None = None, space: str | None = None
    ) -> list[Atom]:
        """`Query.match`, which is `/match` with the pattern written as source.

        `pattern` is a GraphQL String holding MeTTa source, so it is PARSED
        rather than taken as a value: a Python string is a String atom
        everywhere on this surface, and a pattern is a term.
        """
        payload: dict[str, Any] = {"pattern": parse(pattern).to_wire()}
        if space is not None:
            payload["space"] = space
        if limit is not None:
            payload["bound"] = limit
        return self._matched(payload)

    def _resolve_add(self, _info: Any, atom: str, space: str | None = None) -> bool:
        """`Mutation.add`. The atom is MeTTa source, as `match`'s pattern is."""
        payload: dict[str, Any] = {"atom": parse(atom).to_wire()}
        if space is not None:
            payload["space"] = space
        self._space(payload).add(_atom_of(payload, "atom"))
        return True

    def _resolve_remove(self, _info: Any, atom: str, space: str | None = None) -> bool:
        """`Mutation.remove`, which removes ONE stored atom unifying with this."""
        payload: dict[str, Any] = {"atom": parse(atom).to_wire()}
        if space is not None:
            payload["space"] = space
        return bool(self._remove(payload)["removed"])

    def _head_resolver(self, head: Any) -> Callable:
        """One declared head's field: its rows, each argument typed or an Atom.

        An argument the query supplies fixes that position and leaves the
        pattern's remaining variables to be bound; the row carries the supplied
        value back under its own field, so a row is always as wide as the head.
        """
        kinds = [_projection.graphql_type(kind) for kind in head.arguments]

        def resolve(_info: Any, space: str | None = None, **supplied: Any) -> list[dict]:
            # A supplied argument arrives as an Atom already: the `Atom` scalar's
            # own parse_value is `parse`, so the GraphQL input "(f 1)" is a term
            # by the time a resolver sees it.
            arguments: list[Atom] = [
                supplied.get(f"x{position}") or Variable(f"x{position}")
                for position in range(1, len(head.arguments) + 1)
            ]
            pattern = Expression([Symbol(head.name), *arguments])
            rows = self._space({"space": space or head.space}).match(pattern)
            cells = [
                None if not isinstance(argument, Variable)
                else rows.columns.index(argument.name)
                for argument in arguments
            ]
            return [
                {
                    f"x{index + 1}": _schemas.graphql_value(
                        argument if position is None else row[position], kind
                    )
                    for index, (argument, position, kind) in enumerate(
                        zip(arguments, cells, kinds, strict=True)
                    )
                }
                for row in rows
            ]

        return resolve

    def cursor_space(self, token: object) -> str | None:
        """Which space an open cursor's answers come from, so a transport
        can hand its authorization hook the space /next and /stop are
        really about; None once the cursor is gone.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return self._cursors.space_of(token)

    def close(self) -> None:
        """Release every cursor still open, and the engine behind each."""
        self._cursors.close_all()

    def __enter__(self) -> Self:
        """A gateway owns cursors, so it is `with`-able like everything else here.

        Server, RemoteCursor and Space are all context managers for one reason:
        a handle that owns an engine resource and has to be closed by hand is
        the one whose leak on an exception path is silent. A Gateway holds one
        engine per open cursor and had that shape.
        """
        return self

    def __exit__(self, *_exception: object) -> None:
        """Release the cursors, whether the block ended well or not."""
        self.close()

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
        """The eager method: one reply carrying the whole answer set.

        match()'s reading on the wire, and it costs what match() costs, the
        join computed to the end before anything crosses. /ask is the streaming
        endpoint, and both take their candidates from _candidates, so the two
        answer the same set for every pattern.
        """
        return {"atoms": _wire(self._matched(payload))}

    def _matched(self, payload: dict) -> list[Atom]:
        """The atoms /match answers, before they are put on the wire.

        The GraphQL resolver wants the same answer set as ATOMS, so the two
        share this rather than crossing the wire encoding and back for a call
        that never leaves the process.
        """
        space = self._space(payload)
        pattern = _atom_of(payload, "pattern")
        bound = _bound_of(payload)
        if bound == 0:
            # Zero answers wanted: the engine's query refuses a zero
            # limit, and no work is the exact honoring.
            return []
        if _linear(pattern) is not None:
            # A repeated variable can make an instantiation infinite, so this
            # pattern's candidates come through the linearised cursor whether
            # the caller asked for all of them or a bounded page.
            cursor, answers = self._candidates(space, pattern)
            try:
                taken = answers if bound is None else islice(answers, bound)
                return [candidate.atom for candidate in taken]
            finally:
                cursor.close()
        if bound is not None:
            rows = space.match(pattern, limit=bound)
            return [
                substitute(pattern, dict(zip(rows.columns, row, strict=True)))
                for row in rows
            ]
        return self._collapsed(space, pattern)

    def _collapsed(self, space: MeTTa, pattern: Atom) -> list[Atom]:
        """One engine-side match, collapsed to the instantiations it answers.

        The whole answer set crosses once; stream() pays a crossing per chunk
        instead.
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

    def _candidates(
        self, space: MeTTa, pattern: Atom
    ) -> tuple[Cursor, Iterator[_Candidate]]:
        """The engine cursor a pattern's candidates come from.

        The second answer is the candidates that cursor makes, each carrying
        both the instantiated atom the JSON reply puts on the wire and the ROW
        of cells behind it, which is what an Arrow batch's columns are. One walk
        answers both because they are one match; deriving the row from the atom
        afterwards would re-unify a candidate the cursor had already bound.

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
        answers = (self._candidate(template, cursor.columns, row) for row in cursor)
        if linear is None:
            return cursor, answers
        return cursor, (
            candidate for candidate in answers
            if unify(pattern, _apart(candidate.atom)) is not None
        )

    @staticmethod
    def _candidate(template: Atom, columns: tuple[str, ...], row: Any) -> _Candidate:
        """One pulled row as the candidate both reply formats are built from.

        A cursor under an ambient `metta.under(<algebra>)` scope answers a
        TaggedAnswer rather than a bare row, and this used to zip the columns
        against the wrapper: `Gateway("ask", ...)` raised `TypeError:
        'TaggedAnswer' object is not iterable` for every pattern whenever such a
        scope reached the calling thread [measured 2026-09-07]. The value inside
        it IS the row, and its annotation is what an Arrow answer's
        `annotation` column carries, so unwrapping it here answers both.
        """
        annotation = getattr(row, "annotation", None)
        cells = getattr(row, "value", row) if annotation is not None else row
        return _Candidate(
            substitute(template, dict(zip(columns, cells, strict=True))),
            tuple(cells),
            annotation,
        )

    def _pull(self, entry: _OpenCursor, batch: int) -> tuple[list[_Candidate], bool]:
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

    def _reply(
        self,
        entry: _OpenCursor,
        answers: list[_Candidate],
        token: str | None,
        *,
        arrow: bool,
    ) -> dict:
        """One chunk, in the format the request asked for.

        JSON is the protocol's own; an Arrow reply is a complete IPC stream
        whose bytes ride under `arrow`, and its cursor token rides beside them
        because a stream has nowhere to carry one. Both are the same answers.
        """
        if not arrow:
            return {"atoms": _wire([answer.atom for answer in answers]), "cursor": token}
        return {"arrow": _arrow_chunk(entry, answers), "cursor": token}

    def _ask(self, payload: dict) -> dict:
        """Open a cursor and answer the first chunk for the streaming endpoint.

        stream()'s reading on the wire. The reply's `cursor` is the
        continuation and doubles as the more-flag, because a finished
        stream is one the gateway has already released and answers null
        for, so no boolean has to be computed from a lookahead answer.
        """
        space = self._space(payload)
        pattern = _atom_of(payload, "pattern")
        batch = _batch_of(payload)
        bound = _bound_of(payload)
        arrow = _arrow_of(payload)
        cursor, answers = self._candidates(space, pattern)
        entry = _OpenCursor(cursor, answers, space.name, bound)
        if arrow:
            # The schema is fixed HERE, before the first batch, from what the
            # space declares about the pattern's positions. Every later chunk of
            # this cursor is written at it, which is what an IPC stream requires
            # and what a kind derived per chunk could not promise.
            try:
                entry.schema, entry.kinds = self._arrow_schema(
                    space, pattern, cursor.columns
                )
            except BaseException:
                cursor.close()
                raise
        if bound == 0:
            cursor.close()
            return self._reply(entry, [], None, arrow=arrow)
        try:
            answered, done = self._pull(entry, batch)
            token = None if done else self._cursors.open(entry)
        except BaseException:
            entry.cursor.close()
            raise
        if done:
            entry.cursor.close()
        return self._reply(entry, answered, token, arrow=arrow)

    def _arrow_schema(
        self, space: MeTTa, pattern: Atom, columns: tuple[str, ...]
    ) -> tuple[Any, tuple[str, ...]]:
        """The Arrow schema a pattern's answers are written at.

        One column per pattern variable at the type the space DECLARES for its
        position, then `atom`, the canonical text of the whole instantiated
        pattern, which is the lossless carrier that makes the typed columns
        safe: a cell a declared column cannot hold is null there and exact here.
        An undeclared position is `utf8` canonical text, marked
        `metta.kind=mixed`, as the shared type projection specifies
        [source: extensions/python/metta/_catalog/types.py:213,
        arrow_kind; commit=WORKTREE].
        """
        arrows = _projection.arrows_of(declared(space))
        types = _projection.column_types(pattern, columns, arrows)
        kinds = tuple(_projection.arrow_kind(kind) for kind in types)
        schema = _arrow.ipc_schema(
            (*columns, "atom"),
            (*kinds, _arrow.TEXT),
            (*(str(kind) for kind in types), _projection.UNDEFINED),
        )
        return schema, kinds

    def _next(self, payload: dict) -> dict:
        token = payload.get("cursor")
        entry = self._cursors.take(token)
        batch = _batch_of(payload)
        arrow = _arrow_of(payload)
        if arrow and entry.schema is None:
            self._cursors.release(token)
            msg = (
                "this cursor was opened for JSON answers, so its Arrow schema "
                "was never fixed; ask for the Arrow format on /ask, which is "
                "where a stream's one schema is decided"
            )
            raise MettaError(msg)
        try:
            answered, done = self._pull(entry, batch)
        except BaseException:
            self._cursors.release(token)
            raise
        if done:
            self._cursors.release(token)
        return self._reply(entry, answered, None if done else token, arrow=arrow)

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
            "idempotency": {
                "scope": self._mutation_scope,
                "expires": time.monotonic() + self._mutation_ttl,
            },
            # The reflection the in-process interface has: what this server
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
            # extensions/python/metta/aio/_worker.py:525,
            # _EngineThread.interrupt_if_running;
            # commit=WORKTREE].
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
                except BaseException as exc:  # noqa: BLE001
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

def _worker_response(worker: _RemoteWorker, operation: str, payload: dict) -> tuple[dict, int]:
    """Distinguish completed replies from a worker deadline after possible effects."""
    try:
        kind, value = worker.call(operation, payload, timeout=600.0)
    except TimeoutError as exc:
        if operation not in _MUTATIONS:
            raise
        return {"error": str(exc), "outcome": "unknown"}, 400
    if kind == "ok":
        return value, 200
    answer = {"error": value}
    if operation in _MUTATIONS:
        answer["outcome"] = "unknown"
    return answer, 400

class Server:
    """This engine's spaces, served. close() stops accepting.

    A context manager, because it owns a socket, an accept thread and an
    engine worker, which is more than any other handle in this library and
    exactly the shape Python spells `with`. `metta.space()` and
    `metta.aio.connect()` are already `with`-able; a server that had to be
    closed by hand was the one resource whose leak on an exception path was
    silent.
    """

    def __init__(
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
    mutation_ttl: float = _MUTATION_TTL,
    mutation_limit: int = _MUTATION_LIMIT,
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

    mutation_ttl and mutation_limit bound the keyed mutation replay ledger,
    as documented on Gateway. Authorization must admit health for clients
    that negotiate mutation keys.

    A context is a PROCESS: serving and attaching within one process
    cannot join through the local engine, because one runtime lock guards
    both sides of that call and the serving thread would wait on the very
    evaluation that is waiting on it. Two engines, two processes, is the
    deployment this exists for; in-process, spaces already share the
    engine and need no wire. Gateway is the same protocol with no
    transport under it, for a test or a framework that wants the
    operations without a socket.

    m may be a context or a space, as Gateway takes either.
    """
    gateway = Gateway(
        m, spaces, cursor_idle=cursor_idle, cursor_limit=cursor_limit,
        mutation_ttl=mutation_ttl, mutation_limit=mutation_limit,
    )

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
            self._write(401, _json.dumps({"error": "not authorized"}), "application/json")

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
            # A GET path is one word, except the document paths, whose spelling
            # is what a consumer's tooling looks for: `/openapi.json` is where
            # every OpenAPI client tries first. The gateway door's own name is
            # the operation an authorize hook judges, which is what makes a
            # policy over the documents spell the same words as a policy over
            # the wire operations.
            operation = _GET_OPERATIONS.get(self.path.strip("/"), self.path.strip("/"))
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
                reply = _get_reply(worker, operation, secured=token is not None)
            except _HTTPProblem as exc:
                reply = _refusal(exc.status, str(exc))
            except Exception as exc:  # the wire answers errors as JSON
                logger.warning(
                    "remote engine HTTP handler rejected operation %s",
                    operation,
                    exc_info=True,
                )
                reply = _refusal(400, str(exc))
            self._write(*reply)

        def _write(
            self,
            status: int,
            body: bytes,
            content_type: str,
            extra: Mapping[str, str] = _NO_HEADERS,
        ) -> None:
            """One reply, whatever its media type and whatever it carries beside.

            Every response path went through the same four lines with
            `application/json` written into each of them; the documents a
            server publishes are not all JSON, and an Arrow answer carries its
            cursor token in a header, so both are arguments.
            """
            self.send_response(status)
            self.send_header("content-type", content_type)
            self.send_header("content-length", str(len(body)))
            for name, value in extra.items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)

        def _method_not_allowed(self) -> None:
            # The protocol's own refusal: only POST operates (and GET
            # answers /health). BaseHTTPRequestHandler would say 501,
            # which reads as "not implemented yet" rather than "never".
            self._write(
                405,
                _json.dumps(
                    {"error": f"method {self.command} is not supported; POST an operation"}
                ),
                "application/json",
            )

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
                payload = _requested(operation, headers, self._payload())
                request = Request(operation, self._space_named(operation, payload), headers)
                if authorize is not None and not authorize(request):
                    self._refuse_unauthorized(operation)
                    return
                reply = _post_reply(worker, operation, payload)
            except _HTTPProblem as exc:
                logger.warning(
                    "remote engine HTTP handler rejected operation %s: %s",
                    operation,
                    exc,
                )
                reply = _refusal(exc.status, str(exc))
            except Exception as exc:
                logger.warning(
                    "remote engine HTTP handler rejected operation %s",
                    operation,
                    exc_info=True,
                )
                reply = _refusal(400, str(exc))
            self._write(reply[0], reply[1], reply[2], extra=reply[3])
            logger.debug(
                "served remote engine operation %s with HTTP %d",
                operation,
                reply[0],
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
