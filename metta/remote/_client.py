"""Purpose: represent remote spaces and retained answer streams.

Guarantees: context exit retains the body failure together with a failed
stop, and propagates either failure unchanged alone [tested:
test_owned_exit_zero_one_or_two_failures; commit=4a3266c7354990618de5d9489f4e094f5a80c5b6].
Owns resources: RemoteCursor.close releases its server token. A failed stop
retains the token so the caller can retry
[source: extensions/python/metta/remote/_client.py:220; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
"""

from __future__ import annotations

import warnings
from collections import deque
from collections.abc import Iterator
from types import TracebackType
from typing import Any, Self

import metta._catalog.arrow as _arrow
import metta.doors as _doors
from metta._atoms.factories import Atom
from metta._errors.errors import MettaError
from metta._spaces.results import _raise_exit_errors
from metta.foreign import SpaceProvider
from metta.remote._defaults import _DEFAULT_BATCH
from metta.remote._transport import (
    ProtocolError,
    Transport,
    _arrow_reply,
    _HTTPTransport,
    _mutate,
    _response,
)


class RemoteCursor(_doors.DoorOwner):
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

    __slots__ = (
        "__weakref__", "_arrow", "_batch", "_buffer", "_closed", "_space",
        "_streams", "_token", "_transport",
    )

    def __init__(
        self,
        transport: Transport,
        space: str,
        pattern: Atom,
        *,
        batch: int = _DEFAULT_BATCH,
        limit: int | None = None,
        arrow: bool = False,
    ) -> None:
        if isinstance(batch, bool) or not isinstance(batch, int) or batch < 1:
            msg = f"batch must be a positive integer, got {batch!r}"
            raise ValueError(msg)
        self._transport = transport
        self._space = space
        self._batch = batch
        self._closed = False
        self._arrow = arrow
        self._token: str | None = None
        self._buffer: deque[Atom] = deque()
        #: The Arrow chunks pulled so far, one complete IPC stream each.
        self._streams: list[bytes] = []
        payload: dict[str, Any] = {
            "space": space,
            "pattern": pattern.to_wire(),
            "batch": batch,
        }
        if limit is not None:
            payload["bound"] = limit
        if arrow:
            payload["format"] = "arrow"
        try:
            self._absorb(transport("ask", payload))
        except ProtocolError as response_error:
            self._token = response_error.cursor
            try:
                self.close()
            except BaseException as close_error:  # noqa: BLE001 -- report both acquisition and cleanup failures
                msg = "remote cursor response and initial cleanup failed"
                raise BaseExceptionGroup(msg, [response_error, close_error]) from None
            raise

    def _absorb(self, answer: dict) -> None:
        operation = "ask" if self._token is None else "next"
        if self._arrow:
            self._token = _arrow_reply(operation, answer, self._streams)
            return
        reply = _response(operation, answer, {"batch": self._batch, "cursor": self._token})
        self._token = reply["cursor"]
        self._buffer.extend(reply.atoms)

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.atom,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.nondet,
        tiers=(_doors.Tier.remote,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_remote_generated_doors_release_their_cursor',),
        remote=_doors.Remote('next', 'NextRequest', 'Answer', 'The next chunk of an open stream. A short chunk ends it.'),
    )
    def __next__(self) -> Atom:
        """Read the next remote answer."""
        if self._arrow:
            msg = (
                "this cursor answers Arrow record batches, so it has no atoms "
                "to iterate; read it with to_arrow(), or open one without "
                "arrow=True to iterate atoms"
            )
            raise MettaError(msg)
        return self._next_atom()

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.value,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.remote,),
        evidence=('extensions/python/tests/ch19_spaces_backed_by_anything/test_remote_arrow.py::test_a_client_cursor_drains_to_one_table',),
    )
    def to_arrow(self) -> Any:
        """The whole remaining stream as one pyarrow Table.

            with space.stream(pattern, arrow=True) as answers:
                table = answers.to_arrow()

        Every chunk crosses as its own complete IPC stream at ONE schema, fixed
        by the server when the cursor opened, so the batches concatenate. The
        columns are the pattern's variables at the types the served space
        declares for them, plus `atom`, the canonical text of each instantiated
        answer, which stays exact where a typed column cannot hold a cell.

        The longhand is the ask/next/stop lifecycle with
        `Accept: application/vnd.apache.arrow.stream` and reading each body with
        `pyarrow.ipc.open_stream`; this is that loop, drained.
        """
        if not self._arrow:
            msg = (
                "this cursor answers JSON atoms; open it with arrow=True to "
                "read Arrow record batches, which is the format the server "
                "fixes a schema for when the cursor opens"
            )
            raise MettaError(msg)
        while self._token is not None:
            self._absorb(
                self._transport(
                    "next",
                    {"cursor": self._token, "batch": self._batch, "format": "arrow"},
                )
            )
        return _arrow.ipc_concat([_arrow.read_ipc(chunk) for chunk in self._streams])

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.value,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.remote,),
        evidence=('extensions/python/tests/ch19_spaces_backed_by_anything/test_remote_arrow.py::test_a_client_cursor_answers_the_capsule_protocol',),
    )
    def __arrow_c_stream__(self, requested_schema: Any = None) -> Any:
        """The drained stream as the Arrow PyCapsule Interface's own object.

        Sugar over `to_arrow()`, so a consumer that dispatches on the protocol
        rather than on a type reaches the same batches
        [source: https://arrow.apache.org/docs/format/CDataInterface/PyCapsuleInterface.html].
        """
        return self.to_arrow().__arrow_c_stream__(requested_schema)

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.stream,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.nondet,
        tiers=(_doors.Tier.remote,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_remote_generated_doors_release_their_cursor',),
        state=_doors.State.any,
    )
    def __iter__(self) -> Iterator[Atom]:
        """Iterate the receiver."""
        return self

    def _next_atom(self) -> Atom:
        """The next atom of a JSON cursor, pulling a chunk when the buffer runs dry."""
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

    @_doors.door(
        kind=_doors.Kind.lifecycle,
        answers=_doors.AnswersAs.none,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.remote,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_remote_generated_doors_release_their_cursor', 'extensions/python/tests/ch19_spaces_backed_by_anything/test_remote.py::test_a_failed_stop_leaves_the_remote_cursor_retryable'),
        state=_doors.State.any,
        remote=_doors.Remote('stop', 'StopRequest', 'Stopped', 'Release a stream early, and say whether there was one to release.'),
    )
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
            _response("stop", self._transport("stop", {"cursor": token}))
            self._token = None
        self._closed = True
        self._buffer.clear()

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.value,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.remote,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_remote_generated_doors_release_their_cursor',),
        state=_doors.State.any,
    )
    def __enter__(self) -> Self:
        """Enter the receiver lifetime."""
        return self

    @_doors.door(
        kind=_doors.Kind.lifecycle,
        answers=_doors.AnswersAs.none,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.remote,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_remote_generated_doors_release_their_cursor',),
        state=_doors.State.any,
    )
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Stop the server's cursor without letting the stop displace the
        diagnosis: a transport that broke mid-stream breaks the /stop too,
        and the failure a caller needs to read is the first one. Both are
        raised together, the same shape serve()'s own startup path uses.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        try:
            self.close()
        except BaseException as stop_failure:  # noqa: BLE001
            msg = "the remote cursor failed and could not be stopped"
            _raise_exit_errors(msg, exc, (stop_failure,))

    def __del__(self) -> None:
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

    def __repr__(self) -> str:
        # Buffered atoms count as open: the server has let go of the
        # stream but the caller has not read the last chunk yet.
        if self._closed:
            state = "closed"
        elif self._token is not None or self._buffer:
            state = "open"
        else:
            state = "exhausted"
        return f"<remote cursor {state} on {self._space}>"

class RemoteSpace(SpaceProvider, _doors.DoorOwner):
    """A space served by another engine, reached through a transport.

    match sends the pattern's wire form and decodes the instantiated
    atoms the remote engine's own match answered; add and remove write
    through; atoms enumerates. The local engine unifies every candidate
    against the local pattern, so a lying or stale remote can only cost
    time, not soundness.

    `batch` chooses how match() retrieves answers, and the choice is the one
    match() and stream() make in-process. Left None, match() is the eager
    /match: one crossing carrying the whole answer set, which is what a
    space whose answers fit in an HTTP body wants. Set to a count, match()
    rides the ask/next/stop lifecycle in chunks of that size, so a caller
    that stops early stops the server's work with it and an answer set
    larger than one body still crosses.

    It does NOT subscribe, and that is the one capability a provider has to
    promise rather than implement. See delivers.
    """

    def __init__(
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

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.none,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.remote,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_remote_door_contracts_preserve_capability_refusals',),
        state=_doors.State.any,
    )
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

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.value,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.remote,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_remote_door_contracts_preserve_capability_refusals',),
        state=_doors.State.any,
    )
    def refusal(self, capability: str, /, **_request: Any) -> str | None:
        """Read RemoteSpace.refusal."""
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

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.stream,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.nondet,
        tiers=(_doors.Tier.remote,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_remote_storage_doors_use_the_declared_operation_protocol',),
        remote=_doors.Remote('match', 'MatchRequest', 'Atoms', 'Every candidate for a pattern in one reply; the eager door, which computes the whole answer set before anything crosses.'),
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
        answer = _response("match", self._transport("match", payload), payload)
        yield from answer.atoms

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.stream,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.nondet,
        tiers=(_doors.Tier.remote,),
        evidence=('extensions/python/tests/ch19_spaces_backed_by_anything/test_remote.py::test_the_lifecycle_answers_exactly_what_the_eager_door_answers',),
        remote=_doors.Remote('ask', 'AskRequest', 'Answer', "Open an answer stream and take its first chunk. The reply's cursor is the continuation and doubles as the more-flag."),
    )
    def stream(
        self,
        pattern: Atom,
        *,
        batch: int = _DEFAULT_BATCH,
        limit: int | None = None,
        arrow: bool = False,
    ) -> RemoteCursor:
        """The lazy method: answers pulled a chunk at a time, so taking two
        of a large enumeration costs the server two answers' work instead
        of the whole join's.

        match() remains eager, matching the in-process split between match()
        and stream(). Reach for this to take answers
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

        `arrow=True` asks for Arrow record batches instead of tagged atoms: the
        server fixes ONE schema for the whole stream when the cursor opens, from
        what it declares about the pattern's positions, and each chunk crosses
        as a complete IPC stream at that schema. Such a cursor answers
        `to_arrow()` and the PyCapsule protocol rather than atoms, because
        converting a batch back to atoms would go through canonical text and
        lose what the tagged wire carries exactly.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return RemoteCursor(
            self._transport, self._space, pattern, batch=batch, limit=limit, arrow=arrow
        )

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.mapping,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.remote,),
        evidence=('extensions/python/tests/ch19_spaces_backed_by_anything/test_remote.py::test_server_capabilities_refuses_a_health_less_transport', 'extensions/python/tests/ch19_spaces_backed_by_anything/test_remote.py::test_a_gateway_is_a_drop_in_transport', 'extensions/python/tests/ch19_spaces_backed_by_anything/test_remote.py::test_health_advertises_the_projection'),
    )
    def server_capabilities(self) -> dict[str, Any]:
        """The server's own advertisement from GET /health: `capabilities`
        names the protocol operations it admits, so a client can ask before
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
        body = _response("health", health())
        # A revision-1 server advertises nothing: the four required
        # operations, bound ignored, is what its silence means.
        return {
            "capabilities": body.get(
                "capabilities", ["match", "enumerate", "add", "remove"]
            ),
            "bound": body.get("bound", False),
            "protocol": body.get("protocol"),
        }

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.stream,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.nondet,
        tiers=(_doors.Tier.remote,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_remote_storage_doors_use_the_declared_operation_protocol',),
        remote=_doors.Remote('atoms', 'SpaceRequest', 'Atoms', 'Every atom the named space holds, duplicates included.'),
    )
    def atoms(self) -> Iterator[Atom]:
        """Read RemoteSpace.atoms."""
        answer = _response("atoms", self._transport("atoms", {"space": self._space}))
        yield from answer.atoms

    @_doors.door(
        kind=_doors.Kind.write,
        answers=_doors.AnswersAs.none,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.remote,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_remote_storage_doors_use_the_declared_operation_protocol',),
        remote=_doors.Remote('add', 'AddRequest', 'Added', 'Store one atom in the named space.'),
    )
    def add(self, atom: Atom) -> None:
        """Store one atom on the serving side.

        A lost response raises OutcomeUnknown. Its retry() replays the
        original acknowledgement when the server advertised idempotency;
        otherwise retry refuses to send and the caller must reconcile with
        the server. Calling add again starts a NEW logical mutation.
        """
        self._mutate("add", {"space": self._space, "atom": atom.to_wire()})

    @_doors.door(
        kind=_doors.Kind.write,
        answers=_doors.AnswersAs.none,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.remote,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_remote_storage_doors_use_the_declared_operation_protocol',),
        remote=_doors.Remote('add_many', 'AddManyRequest', 'AddedCount', 'Store a batch in one request. A batch is a transport optimisation and never a semantic one.'),
    )
    def add_many(self, atoms: list[Atom]) -> None:
        """One request carries the batch, the engine's own bulk-write law on
        the wire: a batch is a transport optimisation and never a semantic
        one, and the engine already routes only plain stores through it.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        self._mutate(
            "add_many",
            {"space": self._space, "atoms": [atom.to_wire() for atom in atoms]},
        )

    @_doors.door(
        kind=_doors.Kind.write,
        answers=_doors.AnswersAs.boolean,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.remote,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_remote_storage_doors_use_the_declared_operation_protocol',),
        remote=_doors.Remote('remove', 'RemoveRequest', 'Removed', 'Remove ONE stored atom unifying with this one. Two copies need two removals.'),
    )
    def remove(self, atom: Atom) -> bool:
        """Read RemoteSpace.remove."""
        answer = self._mutate("remove", {"space": self._space, "atom": atom.to_wire()})
        return answer["removed"]


    def _mutate(self, operation: str, payload: dict) -> dict:
        if isinstance(self._transport, _HTTPTransport):
            return self._transport(operation, payload)
        return _mutate(
            self._transport, getattr(self._transport, "health", None), operation, payload
        )
