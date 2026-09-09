"""Purpose: validate wire replies and connect remote operations.

Guarded by: _LIVE_SERVERS_LOCK protects the local server address registry used
by _refuse_this_process [source: extensions/python/metta/remote/_transport.py:304; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
"""

from __future__ import annotations

import logging
import math
import secrets
import socket
import threading
from collections.abc import Callable, Iterable
from copy import deepcopy
from http.client import HTTPException
from typing import Any
from urllib.parse import urlsplit

import metta._binding.json as _json
import metta._catalog.arrow as _arrow
from metta._atoms.factories import Atom
from metta._atoms.wire import _atom_from_wire
from metta._errors.errors import MettaError, TransportFailure
from metta.remote._defaults import _DEFAULT_BATCH
from metta.remote._network import HTTPEndpoint, validated_timeout

logger = logging.getLogger(__name__)

Transport = Callable[[str, dict], dict]

class _HTTPTransport:
    """connect()'s transport validates replies and negotiates mutation replay.

    It knows its server's GET /health, so server_capabilities() can ask. A
    hand-built transport that wants the same offers its own `health`.
    """

    def __init__(
        self,
        operate: Callable[[str, dict], dict],
        health: Callable[[], dict],
    ) -> None:
        self._operate = operate
        self._health = health

    def __call__(self, operation: str, payload: dict) -> dict:
        if operation in _MUTATIONS:
            return _mutate(self._operate, self.health, operation, payload)
        answer = self._operate(operation, payload)
        if isinstance(answer, dict) and isinstance(answer.get("arrow"), (bytes, bytearray)):
            # An Arrow chunk has no JSON envelope to validate; `_arrow_reply`
            # on the cursor checks what a client relies on and the IPC reader
            # refuses anything that is not a stream.
            return answer
        return _response(operation, answer, payload)

    def health(self) -> dict:
        return _response("health", self._health())

_MUTATIONS = frozenset({"add", "add_many", "remove"})

class OutcomeUnknown(TransportFailure):
    """A mutation may have executed; ``retry()`` replays its keyed request.

    ``outcome`` is always ``"unknown"``. A retry returns the original wire
    acknowledgement. Without a negotiated replay contract it refuses to send;
    callers must reconcile the operation with the serving application.
    """

    outcome = "unknown"
    operation: str

    def __init__(self, operation: str, retry: Callable[[], dict] | None = None) -> None:
        """Retain the mutation name and its optional keyed recovery operation."""
        super().__init__(
            f"the remote mutation {operation} has an unknown outcome; "
            "it may have been applied. Use this exception's retry() for keyed "
            "recovery, or reconcile with the server before issuing a new mutation"
        )
        self.operation = operation
        self._retry = retry

    def retry(self) -> dict:
        """Recover the original result without issuing a new logical write."""
        if self._retry is None:
            msg = "this mutation has no negotiated idempotency key; reconcile with the server"
            raise MettaError(msg)
        try:
            return self._retry()
        except OutcomeUnknown:
            raise
        except Exception as exc:
            # A refused recovery cannot settle whether the ORIGINAL ran.
            raise OutcomeUnknown(self.operation, self._retry) from exc

class ProtocolError(TransportFailure):
    """A response violates its schema; cursor retains a rejected reply's token."""

    def __init__(self, message: str, *, cursor: str | None = None) -> None:
        """Keep a valid release token available if initial cursor cleanup fails."""
        super().__init__(message)
        self.cursor = cursor

class _Response(dict):
    """An envelope and its completely validated, decoded atom list."""

    def __init__(self, body: dict) -> None:
        super().__init__(body)
        self.atoms: list[Atom] = []

def _response(operation: str, body: Any, payload: dict | None = None) -> _Response:
    token = body.get("cursor") if isinstance(body, dict) else None
    token = token if operation in ("ask", "next") and isinstance(token, str) and token else None

    def refuse(detail: str) -> None:
        msg = f"invalid remote {operation} response: {detail}"
        raise ProtocolError(msg, cursor=token)

    if not isinstance(body, dict):
        refuse("expected an object")
    if "error" in body:
        if not isinstance(body["error"], str):
            refuse("error must be a string")
        if body.get("outcome") == "unknown":
            if operation not in _MUTATIONS:
                refuse("unknown outcome is only valid for mutations")
            raise OutcomeUnknown(operation) from MettaError(body["error"])
        msg = f"the remote engine refused {operation}: {body['error']}"
        raise MettaError(msg)
    answer = _Response(body)
    if operation in ("match", "atoms", "ask", "next"):
        if not isinstance(body.get("atoms"), list):
            refuse("chunk without an atom list")
        try:
            answer.atoms = [_atom_from_wire(wire) for wire in body["atoms"]]
        except (ValueError, TypeError) as exc:
            msg = f"invalid remote {operation} response: {exc}"
            raise ProtocolError(msg, cursor=token) from exc
    if operation in ("ask", "next"):
        if "cursor" not in body:
            refuse("cursor field is required")
        cursor = body["cursor"]
        if cursor is not None and (not isinstance(cursor, str) or not cursor):
            refuse("cursor must be a nonempty string or null")
        if cursor is not None and not answer.atoms:
            refuse("live cursor with no atoms")
        if payload is not None:
            batch = payload.get("batch", _DEFAULT_BATCH)
            if len(answer.atoms) > batch:
                refuse("atom list exceeds the requested batch")
            if cursor is not None and len(answer.atoms) < batch:
                refuse("a short chunk must end the stream")
            if operation == "next" and cursor not in (None, payload.get("cursor")):
                refuse("next changed the cursor token")
    if operation in ("remove", "stop"):
        field = "removed" if operation == "remove" else "stopped"
        if type(body.get(field)) is not bool:
            refuse(f"{field} must be a boolean")
    if operation == "add" and body.get("added") is not True:
        refuse("added must be true")
    if operation == "add_many":
        if type(body.get("added")) is not int or body["added"] < 0:
            refuse("added must be a nonnegative integer")
        if payload is not None and body["added"] != len(payload.get("atoms", ())):
            refuse("added count differs from the requested batch")
    if operation == "health":
        if body.get("ok") is not True:
            refuse("ok must be true")
        if type(body.get("atoms")) is not int or body["atoms"] < 0:
            refuse("atoms must be a nonnegative integer")
        if "bound" in body and type(body["bound"]) is not bool:
            refuse("bound must be a boolean")
        if "protocol" in body and (type(body["protocol"]) is not int or body["protocol"] < 1):
            refuse("protocol must be a positive integer")
        if "capabilities" in body and (
            not isinstance(body["capabilities"], list)
            or any(not isinstance(item, str) or not item for item in body["capabilities"])
        ):
            refuse("capabilities must be a list of nonempty strings")
        if "idempotency" in body:
            contract = body["idempotency"]
            if (
                not isinstance(contract, dict)
                or not isinstance(contract.get("scope"), str)
                or not contract["scope"]
                or type(contract.get("expires")) not in (int, float)
                or not math.isfinite(contract["expires"])
            ):
                refuse("malformed idempotency metadata")
    return answer

def _arrow_reply(operation: str, answer: Any, streams: list[bytes]) -> str | None:
    """Validate one Arrow chunk and keep its bytes; answer the continuation.

    An Arrow answer has no envelope to validate the way a JSON one does, so
    what is checked is what a client relies on: bytes under `arrow`, and a
    cursor token that is a nonempty string or absent. The bytes themselves are
    checked by the reader, which refuses anything that is not an IPC stream.
    """
    def refuse(detail: str) -> None:
        msg = f"invalid remote {operation} response: {detail}"
        raise ProtocolError(msg)

    if not isinstance(answer, dict):
        refuse("expected an object")
    if isinstance(answer.get("error"), str):
        msg = f"the remote engine refused {operation}: {answer['error']}"
        raise MettaError(msg)
    if not isinstance(answer.get("arrow"), (bytes, bytearray)):
        refuse("an Arrow chunk without its bytes")
    token = answer.get("cursor")
    if token is not None and (not isinstance(token, str) or not token):
        refuse("cursor must be a nonempty string or null")
    streams.append(bytes(answer["arrow"]))
    return token

def _mutate(
    transport: Transport,
    health: Callable[[], dict] | None,
    operation: str,
    payload: dict,
) -> dict:
    # Stripe API 2026-07-29.dahlia: reuse a key only with the original inputs.
    # https://docs.stripe.com/api/idempotent_requests
    request = deepcopy(payload)
    contract = None if health is None else _response("health", health()).get("idempotency")
    if "idempotency" in request:
        token = request["idempotency"]
        if (contract is None or not isinstance(token, dict)
                or token.get("scope") != contract["scope"]):
            msg = "the supplied idempotency key does not name this gateway instance"
            raise MettaError(msg)
    elif contract is not None:
        request["idempotency"] = {
            "scope": contract["scope"],
            "expires": contract["expires"],
            "key": secrets.token_urlsafe(24),
        }

    def attempt() -> dict:
        try:
            answer = _response(operation, transport(operation, deepcopy(request)), request)
        except OutcomeUnknown as exc:
            if contract is None:
                raise
            raise OutcomeUnknown(operation, attempt) from exc
        except (HTTPException, OSError, ProtocolError) as exc:
            raise OutcomeUnknown(operation, attempt if contract is not None else None) from exc
        return answer

    return attempt()

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

_LIVE_SERVERS: dict[tuple[str, int], tuple[str, ...]] = {}

_LIVE_SERVERS_LOCK = threading.Lock()

_LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})

_WILDCARD_FAMILIES: dict[str, frozenset[int]] = {
    "0.0.0.0": frozenset({socket.AF_INET}),  # nosec B104 -- recognising a wildcard bind, not making one  # noqa: S104  # nosec B104 -- recognising a wildcard bind, not making one
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
    is not refused here; the guard is on the space() URL form, whose spaces
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
    Credentials require https. Each mutation negotiates a replay key through
    GET /health before its POST; authorization policies must permit that read.
    An unadvertised extension leaves mutations unkeyed, and OutcomeUnknown
    refuses to resend those requests after a lost response.
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
        asked = sent if payload.get("format") != "arrow" else {
            **sent, "accept": _arrow.IPC_MEDIA_TYPE
        }
        try:
            status, reason, raw, received = endpoint.request(
                "POST",
                operation,
                body=_json.dumps(payload),
                headers=asked,
                timeout=timeout,
            )
        except (HTTPException, OSError) as exc:
            logger.warning(
                "remote engine operation %s failed during transport",
                operation,
                exc_info=True,
            )
            if operation in _MUTATIONS:
                raise OutcomeUnknown(operation) from exc
            msg = f"the remote engine request {operation} failed: {exc}"
            raise MettaError(msg) from exc
        logger.debug(
            "remote engine operation %s answered with HTTP %d",
            operation,
            status,
        )
        if received.get("content-type", "").split(";")[0].strip() == _arrow.IPC_MEDIA_TYPE:
            # An Arrow answer is BYTES, and its cursor token rides in a header
            # because an IPC stream has nowhere to put one. Both halves of the
            # wire keep one transport signature by carrying it as this dict.
            return {"arrow": raw, "cursor": received.get("x-metta-cursor") or None}
        try:
            answer = _json.loads(raw)
        except (UnicodeDecodeError, ValueError) as exc:
            if operation in _MUTATIONS:
                raise OutcomeUnknown(operation) from exc
            detail = raw.decode("utf-8", "replace")[:200]
            msg = f"the remote engine answered {status} {reason} with invalid JSON: {detail}"
            raise ProtocolError(msg) from exc
        if operation in _MUTATIONS and (
            status >= 500 or (isinstance(answer, dict) and answer.get("outcome") == "unknown")
        ):
            detail = answer.get("error", reason) if isinstance(answer, dict) else reason
            raise OutcomeUnknown(operation) from MettaError(str(detail))
        if status >= 400:
            body = raw.decode("utf-8", "replace")
            detail = answer.get("error", body) if isinstance(answer, dict) else body
            msg = f"the remote engine refused {operation}: {detail}"
            raise MettaError(msg)
        return answer

    def health() -> dict:
        """GET /health, the server describing itself: revision, atom
        count, capabilities, and whether /match honors bound.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        try:
            status, reason, raw, _received = endpoint.request(
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
            raise ProtocolError(msg) from exc
        if status >= 400:
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
